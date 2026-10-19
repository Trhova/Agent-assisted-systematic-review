"""Bounded public GETs with durable success/failure journals. No access bypass."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests

from scripts.model_backend import atomic_json, digest


class AcquisitionError(RuntimeError):
    pass


def public_url(url):
    parts = urlsplit(url)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        raise AcquisitionError(
            "Only public HTTP(S) URLs without credentials are accepted"
        )
    labels = set(parts.hostname.lower().split("."))
    if labels & {
        "sci-hub",
        "scihub",
        "libgen",
        "annas-archive",
        "annasarchive",
        "z-library",
        "zlibrary",
    }:
        raise AcquisitionError(
            "Known unauthorized mirror excluded from public-source acquisition"
        )
    addresses = socket.getaddrinfo(
        parts.hostname, parts.port or (443 if parts.scheme == "https" else 80)
    )
    if not addresses or any(
        not ipaddress.ip_address(a[4][0]).is_global for a in addresses
    ):
        raise AcquisitionError("Non-public destination rejected")
    return url


def failure_retry_epoch(meta, now=None):
    now = time.time() if now is None else now
    if "budget" in meta.get("error", ""):
        return 0
    if meta.get("http_status") == 429 or "cooldown" in meta.get("error", "").lower():
        return meta.get("server_retry_after_epoch", now + 300)
    if 500 <= meta.get("http_status", 0) < 600:
        failures = max(1, meta.get("failure_count", 1))
        return now + min(3600, 60 * 2 ** min(failures - 1, 6))
    return now + 86400


class PublicFetcher:
    """Per-record network budget; cached responses do not consume requests.

    Timeout bounds connect/read inactivity; a monotonic deadline is also checked
    between chunks and requests. Requests cannot interrupt an OS DNS stall.
    """

    def __init__(
        self,
        directory: Path,
        max_requests=12,
        max_bytes=20_000_000,
        seconds=120,
        host_cache=None,
        io_timeout=15,
    ):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.host_cache = Path(host_cache) if host_cache else self.directory / "hosts"
        if not 0 < io_timeout <= seconds:
            raise ValueError("I/O timeout must fit inside the acquisition deadline")
        self.io_timeout = io_timeout
        self.remaining = max_requests
        self.max_bytes = max_bytes
        self.deadline = time.monotonic() + seconds

    def get(self, url):
        folder = self.directory / digest(url)
        folder.mkdir(exist_ok=True)
        meta_path, body_path = folder / "response.json", folder / "body"
        previous_failures = 0
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            previous_failures = meta.get(
                "failure_count", 1 if meta.get("status") == "failed" else 0
            )
            if (
                meta.get("status") == "failed"
                and meta.get("cache_policy_version", 1) < 2
                and (
                    500 <= meta.get("http_status", 0) < 600
                    or meta.get("http_status") == 429
                )
            ):
                # Earlier caches incorrectly held transient HTTP failures for a day.
                meta["retry_after_epoch"] = failure_retry_epoch(
                    meta, meta.get("started_at_epoch", time.time())
                )
            if meta["status"] == "success" and body_path.exists():
                body = body_path.read_bytes()
                if hashlib.sha256(body).hexdigest() != meta["sha256"]:
                    raise AcquisitionError("Cached response checksum mismatch")
                return body, meta
            if time.time() < meta.get("retry_after_epoch", 0):
                raise AcquisitionError(
                    "Cached acquisition failure: " + meta.get("error", "unknown")
                )
        if os.getenv("ASR_ACQUISITION_CACHE_ONLY") == "1":
            raise AcquisitionError("Cache-only acquisition: no validated cached response")
        current = url
        attempt = {
            "requested_url": url,
            "started_at_epoch": time.time(),
            "redirects": [],
            "cache_policy_version": 2,
        }
        try:
            for _ in range(4):
                if self.remaining <= 0 or time.monotonic() >= self.deadline:
                    raise AcquisitionError("Acquisition request/time budget exhausted")
                host = urlsplit(current).hostname
                host_state = self.host_cache / (digest(host) + ".json")
                if (
                    host_state.exists()
                    and time.time()
                    < json.loads(host_state.read_text())["retry_after_epoch"]
                ):
                    attempt["server_retry_after_epoch"] = json.loads(
                        host_state.read_text()
                    )["retry_after_epoch"]
                    raise AcquisitionError("Host rate limit cooldown active")
                public_url(current)
                self.remaining -= 1
                remaining = max(
                    0.1, min(self.io_timeout, self.deadline - time.monotonic())
                )
                headers = {"User-Agent": "agentic-systematic-review/0.3"}
                if (
                    urlsplit(current).scheme == "https"
                    and host == "api.openalex.org"
                    and os.getenv("OPENALEX_API_KEY")
                ):
                    headers["Authorization"] = (
                        "Bearer " + os.environ["OPENALEX_API_KEY"]
                    )
                if (
                    urlsplit(current).scheme == "https"
                    and host == "api.semanticscholar.org"
                    and os.getenv("SEMANTIC_SCHOLAR_API_KEY")
                ):
                    headers["x-api-key"] = os.environ["SEMANTIC_SCHOLAR_API_KEY"]
                with requests.get(
                    current,
                    stream=True,
                    allow_redirects=False,
                    timeout=(remaining, remaining),
                    headers=headers,
                ) as response:
                    attempt["http_status"] = response.status_code
                    if response.is_redirect:
                        current = urljoin(current, response.headers["Location"])
                        attempt["redirects"].append(current)
                        continue
                    if response.status_code == 429:
                        retry = response.headers.get("Retry-After", "300")
                        try:
                            delay = max(1, int(retry))
                        except ValueError:
                            from email.utils import parsedate_to_datetime

                            try:
                                delay = max(
                                    1,
                                    parsedate_to_datetime(retry).timestamp()
                                    - time.time(),
                                )
                            except (TypeError, ValueError):
                                delay = 300
                        attempt["server_retry_after_epoch"] = time.time() + delay
                        atomic_json(
                            host_state,
                            {"host": host, "retry_after_epoch": time.time() + delay},
                        )
                    response.raise_for_status()
                    content = bytearray()
                    for chunk in response.iter_content(65536):
                        content.extend(chunk)
                        if (
                            len(content) > self.max_bytes
                            or time.monotonic() > self.deadline
                        ):
                            raise AcquisitionError(
                                "Acquisition byte/time budget exceeded"
                            )
                    body = bytes(content)
                    attempt.update(
                        status="success",
                        url=current,
                        bytes=len(body),
                        content_type=response.headers.get("Content-Type", ""),
                        sha256=hashlib.sha256(body).hexdigest(),
                    )
                    temporary = folder / "body.tmp"
                    temporary.write_bytes(body)
                    temporary.replace(body_path)
                    atomic_json(meta_path, attempt)
                    return body, attempt
            raise AcquisitionError("Redirect limit exceeded")
        except Exception as error:
            attempt.update(
                status="failed",
                error=str(error),
                failure_count=previous_failures + 1,
                retry_after_epoch=0,
            )
            attempt["retry_after_epoch"] = failure_retry_epoch(attempt)
            atomic_json(folder / (str(time.time_ns()) + ".failure.json"), attempt)
            atomic_json(meta_path, attempt)
            raise AcquisitionError(str(error)) from error

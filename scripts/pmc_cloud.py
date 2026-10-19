"""PMC public Cloud Service (2026 layout), with version/identity/checksum checks."""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import requests

from scripts.acquisition import AcquisitionError, PublicFetcher
from scripts.model_backend import atomic_json

BASE = "https://pmc-oa-opendata.s3.amazonaws.com/"


def https_url(url):
    if url.startswith("s3://pmc-oa-opendata/"):
        return BASE + url.removeprefix("s3://pmc-oa-opendata/")
    if url.startswith(BASE):
        return url
    raise ValueError("PMC metadata points outside the documented public dataset")


def response(url, fetcher=None, **kwargs):
    fetcher = fetcher or PublicFetcher(Path("data/benchmarks/pmc_http_cache"))
    prepared = requests.Request("GET", url, params=kwargs.get("params")).prepare().url
    body, _ = fetcher.get(prepared)
    return SimpleNamespace(content=body, json=lambda: json.loads(body))


def article_metadata(pmcid, fetcher=None):
    pmcid = pmcid.upper()
    if not pmcid.startswith("PMC") or not pmcid[3:].isdigit():
        raise ValueError("Invalid PMCID")
    listing = response(
        BASE,
        params={"list-type": "2", "prefix": pmcid + ".", "delimiter": "/"},
        fetcher=fetcher,
    )
    root = ET.fromstring(listing.content)
    if root.findtext("{*}IsTruncated") == "true":
        raise ValueError("Unexpected truncated article-version listing")
    prefixes = [p.text for p in root.findall(".//{*}CommonPrefixes/{*}Prefix")]
    if len(prefixes) > 8:
        raise ValueError(
            "Article version-list exceeds bounded automatic selection limit"
        )
    versions = []
    for prefix in prefixes:
        if not prefix.startswith(pmcid + ".") or not prefix.endswith("/"):
            raise ValueError("Invalid article-version prefix")
        name = prefix.rstrip("/")
        versions.append(
            response(BASE + prefix + name + ".json", fetcher=fetcher).json()
        )
    if not versions:
        raise ValueError("PMCID has no version in public article dataset")
    published = [
        v
        for v in versions
        if str(v.get("is_manuscript", "")).lower() not in ("yes", "true", "1")
    ]
    candidates = published or versions
    if len(candidates) != 1:
        raise ValueError(
            "Multiple published/manuscript versions require explicit selection"
        )
    selected = candidates[0]
    if str(selected.get("is_retracted", "")).lower() in ("yes", "true", "1"):
        raise ValueError("Article is marked retracted")
    if selected.get("pmcid") != pmcid:
        raise ValueError("Metadata PMCID mismatch")
    return selected


def checked_bytes(url, fetcher=None):
    url = https_url(url)
    data = response(url, fetcher=fetcher).content
    expected = parse_qs(urlsplit(url).query).get("md5", [])
    if expected and hashlib.md5(data).hexdigest() != expected[0]:
        raise ValueError("PMC object MD5 differs from metadata")
    return data


def download_pdf(pmcid, destination: Path, expected_pmid=None):
    try:
        fetcher = PublicFetcher(
            destination.parent / "cloud_http",
            host_cache=destination.parent.parent / "acquisition_hosts",
        )
        metadata = article_metadata(pmcid, fetcher=fetcher)
        if expected_pmid and str(metadata.get("pmid", "")) != str(expected_pmid):
            raise ValueError("Metadata PMID differs from requested trial")
        destination.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(destination.with_suffix(".metadata.json"), metadata)
        if not metadata.get("pdf_url"):
            return False, {"status": "no_pdf", "metadata": metadata}
        data = checked_bytes(metadata["pdf_url"], fetcher=fetcher)
        if not data.startswith(b"%PDF"):
            raise ValueError("Cloud object is not a PDF")
        destination.write_bytes(data)
        return True, {
            "status": "ok",
            "via": "pmc_cloud_2026",
            "url": https_url(metadata["pdf_url"]),
            "metadata": metadata,
        }
    except (
        requests.RequestException,
        ValueError,
        ET.ParseError,
        AcquisitionError,
    ) as error:
        return False, {"status": "error", "via": "pmc_cloud_2026", "error": str(error)}

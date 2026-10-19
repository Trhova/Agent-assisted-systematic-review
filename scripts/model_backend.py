"""Bounded, schema-validated model calls with content-addressed audit artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import requests
from jsonschema import Draft202012Validator


def digest(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, prefix=path.name + ".", delete=False
    ) as handle:
        handle.write(
            json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        )
        tmp = Path(handle.name)
    tmp.replace(path)


def request_identity(prompt, schema, backend="codex", model=None, allow_web=False):
    request = {
        "prompt": prompt,
        "schema": schema,
        "backend": backend,
        "model": model,
        "version": 1,
    }
    if allow_web:
        request.update(allow_web=True, version=2)
    return request


def model_json(
    prompt,
    schema,
    artifacts: Path,
    *,
    backend="codex",
    model=None,
    timeout=300,
    allow_web=False,
    max_attempts=2,
    images=None,
):
    if max_attempts not in (1, 2):
        raise ValueError("max_attempts must be one or two")
    request = request_identity(prompt, schema, backend, model, allow_web)
    image_bytes = []
    if images:
        if backend != "codex" or allow_web:
            raise ValueError("Audited image input requires isolated Codex backend")
        from PIL import Image
        import io
        for path in images:
            raw = Path(path).read_bytes()
            with Image.open(io.BytesIO(raw)) as img:
                if img.format != "PNG":
                    raise ValueError("Audited images currently require PNG")
                img.verify()
            image_bytes.append(raw)
        request.update(version=3, images=[{"sha256": hashlib.sha256(raw).hexdigest(), "modality": "image/png"} for raw in image_bytes])
    directory = artifacts / digest(request)
    directory.mkdir(parents=True, exist_ok=True)
    for i, raw in enumerate(image_bytes):
        target = directory / f"input-{i}.png"
        if target.exists() and target.read_bytes() != raw:
            raise ValueError("Preserved image checksum differs")
        target.write_bytes(raw)
    result_path = directory / "parsed.json"
    validator = Draft202012Validator(schema)
    if result_path.exists():
        result = json.loads(result_path.read_text())
        validator.validate(result)
        return result
    if os.getenv("ASR_MODEL_CACHE_ONLY") == "1":
        raise RuntimeError("Model cache-only mode: matching parsed request unavailable")
    atomic_json(directory / "request.json", request)
    if len(prompt) > 500_000:
        atomic_json(
            directory / "input_limit.json",
            {
                "characters": len(prompt),
                "limit": 500_000,
                "status": "requires_document_segmentation; source was not truncated or sent",
            },
        )
        raise ValueError(
            "Source exceeds audited input limit; document segmentation or source identity review required"
        )
    for attempt in range(max_attempts):
        stamp = str(time.time_ns())
        out = directory / f"{stamp}.response.json"
        try:
            if backend == "codex":
                # No repo, reference answers, browser, shell, MCP config, or prior conversation.
                with tempfile.TemporaryDirectory(prefix="asr-model-") as tmp:
                    root = Path(tmp)
                    sp = root / "schema.json"
                    sp.write_text(json.dumps(schema))
                    last = root / "result.json"
                    cmd = [
                        "codex",
                        "exec",
                        "--ignore-user-config",
                        "--ephemeral",
                        "--skip-git-repo-check",
                        "-C",
                        tmp,
                        "-s",
                        "read-only",
                        "-c",
                        'approval_policy="never"',
                        "-c",
                        "features.shell_tool=false",
                        "-c",
                        'web_search="live"' if allow_web else 'web_search="disabled"',
                        "--json",
                        "--output-schema",
                        str(sp),
                        "-o",
                        str(last),
                    ]
                    if model:
                        cmd += ["-m", model]
                    for i, raw in enumerate(image_bytes):
                        image_path = root / f"input-{i}.png"
                        image_path.write_bytes(raw)
                        cmd += ["--image", str(image_path)]
                    atomic_json(directory / f"{stamp}.submission.json", {"started_epoch": time.time(), "request_sha256": digest(request), "image_sha256": [hashlib.sha256(raw).hexdigest() for raw in image_bytes], "modality": "image/png" if image_bytes else "text", "adapter_attempt": attempt + 1})
                    proc = subprocess.run(
                        cmd + ["-"],
                        input=prompt,
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=timeout,
                    )
                    atomic_json(
                        out,
                        {
                            "response_received_epoch": time.time(),
                            "returncode": proc.returncode,
                            "stdout": proc.stdout,
                            "stderr": proc.stderr,
                        },
                    )
                    if proc.returncode or not last.exists():
                        raise RuntimeError(
                            "Codex model call failed; see response artifact"
                        )
                    # Reject calls that used tools even if a valid final answer exists.
                    web_calls = 0
                    for line in proc.stdout.splitlines():
                        try:
                            event = json.loads(line)
                        except ValueError:
                            continue
                        item = event.get("item", {})
                        if item.get("type") == "web_search":
                            web_calls += event.get("type") == "item.completed"
                        if item.get("type") in (
                            "command_execution",
                            "mcp_tool_call",
                        ) or (item.get("type") == "web_search" and not allow_web):
                            raise RuntimeError(
                                "Tool use detected in isolated extraction call"
                            )
                    if allow_web and (web_calls == 0 or web_calls > 12):
                        raise RuntimeError(
                            "Source discovery must perform between one and twelve audited web searches"
                        )
                    result = json.loads(last.read_text())
            elif backend == "openai":
                if allow_web:
                    raise ValueError(
                        "Source web discovery currently requires the audited Codex backend"
                    )
                key = os.getenv("OPENAI_API_KEY")
                if not key:
                    raise RuntimeError("OPENAI_API_KEY is absent")
                if not model:
                    raise ValueError("An explicit API model is required")
                payload = {
                    "model": model,
                    "input": prompt,
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "review_result",
                            "schema": schema,
                            "strict": True,
                        }
                    },
                }
                response = requests.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {key}"},
                    json=payload,
                    timeout=timeout,
                )
                atomic_json(
                    out,
                    {
                        "response_received_epoch": time.time(),
                        "status": response.status_code,
                        "body": response.text,
                        "headers": {"Retry-After": response.headers.get("Retry-After")}
                        if response.headers.get("Retry-After")
                        else {},
                    },
                )
                response.raise_for_status()
                obj = response.json()
                text = "".join(
                    c.get("text", "")
                    for x in obj.get("output", [])
                    for c in x.get("content", [])
                    if c.get("type") == "output_text"
                )
                result = json.loads(text)
            else:
                raise ValueError("Unknown backend")
            validator.validate(result)
            atomic_json(result_path, result)
            return result
        except Exception as error:
            atomic_json(
                directory / f"{stamp}.error.json",
                {"type": type(error).__name__, "error": str(error)},
            )
            if attempt + 1 == max_attempts:
                raise
            time.sleep(1)
    raise AssertionError("unreachable")

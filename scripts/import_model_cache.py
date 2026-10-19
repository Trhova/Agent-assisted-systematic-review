"""Import only request-bound, schema-valid, receipt-backed successful model caches."""

import argparse
import json
import hashlib
import shutil
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.model_backend import atomic_json, digest


def verify_entry(folder, *, model, backend):
    folder = Path(folder)
    request = json.loads((folder / "request.json").read_text())
    if digest(request) != folder.name:
        raise ValueError("Model request identity mismatch")
    if (
        request.get("model") != model
        or request.get("backend") != backend
        or request.get("allow_web")
    ):
        raise ValueError("Cache model/backend/tool policy differs")
    for i, asset in enumerate(request.get("images", [])):
        path = folder / f"input-{i}.png"
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
            raise ValueError("Image request asset checksum differs")
    parsed = json.loads((folder / "parsed.json").read_text())
    Draft202012Validator(request["schema"]).validate(parsed)
    receipts = []
    for receipt in folder.glob("*.response.json"):
        response = json.loads(receipt.read_text())
        if response.get("returncode") != 0:
            continue
        if request.get("images"):
            submission = folder / receipt.name.replace(".response.json", ".submission.json")
            if not submission.exists():
                continue
            sent = json.loads(submission.read_text())
            if sent.get("request_sha256") != folder.name or sent.get("image_sha256") != [x["sha256"] for x in request["images"]] or sent.get("modality") != "image/png":
                continue
        events = []
        for line in response.get("stdout", "").splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
        if any(
            e.get("item", {}).get("type")
            in {"command_execution", "mcp_tool_call", "web_search"}
            for e in events
        ):
            continue
        messages = [
            e["item"].get("text", "")
            for e in events
            if e.get("type") == "item.completed"
            and e.get("item", {}).get("type") == "agent_message"
        ]
        if not messages:
            continue
        try:
            if digest(json.loads(messages[-1])) == digest(parsed):
                receipts.append(receipt.name)
        except ValueError:
            continue
    if not receipts:
        raise ValueError(
            "Parsed cache lacks matching successful isolated response receipt"
        )
    return {
        "request_sha256": folder.name,
        "parsed_sha256": digest(parsed),
        "response_receipts": sorted(receipts),
    }


def import_cache(source, destination, *, model, backend):
    source, destination = Path(source), Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Cache destination must be empty")
    verified, skipped = [], []
    for folder in sorted(source.iterdir()):
        if not folder.is_dir() or not (folder / "parsed.json").exists():
            skipped.append(folder.name)
            continue
        verified.append(verify_entry(folder, model=model, backend=backend))
    destination.mkdir(parents=True, exist_ok=True)
    for item in verified:
        shutil.copytree(
            source / item["request_sha256"], destination / item["request_sha256"]
        )
    receipt = {
        "policy": "verified_model_cache_import_v1",
        "source": str(source.resolve()),
        "model": model,
        "backend": backend,
        "verified": verified,
        "skipped_without_success": skipped,
        "limitation": "Validates provenance and schema, not scientific truth. No failed request is converted to success.",
    }
    atomic_json(destination.parent / "model_cache_import.json", receipt)
    return receipt


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True)
    p.add_argument("--destination", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--backend", default="codex")
    a = p.parse_args()
    import_cache(a.source, a.destination, model=a.model, backend=a.backend)

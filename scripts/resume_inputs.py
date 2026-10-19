"""Preserve complete autonomous inputs when starting a separately observed run."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from scripts.model_backend import atomic_json, digest

INPUTS = (
    "search.json",
    "search_raw.json",
    "search_progress.json",
    "search_supplement.json",
    "screening.json",
    "model",
    "sources",
    "segments",
    "pdf_layout",
    "collection_resolution",
    "environment.json",
    "rob2_drafts/model",
    "rob2_drafts/layout",
)


def prepare(source, destination, search_origin=None):
    source, destination = Path(source), Path(destination)
    status = json.loads((source / "status.json").read_text())
    if status.get("status") == "running":
        raise ValueError("Cannot copy a running review's inputs")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(
            "Destination must be empty; existing results are never replaced"
        )
    search_origin = Path(search_origin) if search_origin else source
    if digest(json.loads((source / "search.json").read_text())) != digest(
        json.loads((search_origin / "search.json").read_text())
    ):
        raise ValueError("Search origin differs from the exact frozen search snapshot")
    if not (search_origin / "search_raw.json").exists():
        raise ValueError("Raw bibliographic provenance is required")
    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in INPUTS:
        origin = (
            search_origin
            if name in {"search.json", "search_raw.json", "search_progress.json"}
            else source
        )
        path = origin / name
        if not path.exists():
            continue
        if path.is_dir():
            shutil.copytree(path, destination / name)
        else:
            shutil.copy2(path, destination / name)
        copied.append(name)
    atomic_json(
        destination / "initialization.json",
        {
            "source": str(source.resolve()),
            "execution_context": {
                k: status.get(k) for k in ("protocol_sha256", "backend", "model")
            },
            "search_origin": str(search_origin.resolve()),
            "copied_inputs": copied,
            "search_sha256": hashlib.sha256(
                (destination / "search.json").read_bytes()
            ).hexdigest(),
            "search_raw_sha256": hashlib.sha256(
                (destination / "search_raw.json").read_bytes()
            ).hexdigest(),
            "note": "Autonomous input/cache continuation only, including content-addressed RoB model/geometry caches. Compiled RoB judgments, accepted effects, synthesis, reference answers and comparisons are not copied. Previous observations remain in the source run.",
        },
    )
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--search-origin", type=Path)
    args = parser.parse_args()
    print(prepare(args.source, args.destination, args.search_origin))

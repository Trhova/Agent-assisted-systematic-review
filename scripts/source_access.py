"""Automatic public-source discovery from bibliographic metadata and DOI links."""

import json
import os
from functools import lru_cache
from pathlib import Path

from scripts.discover_sources import discover_pdf


@lru_cache(maxsize=8)
def metadata_index(path, modified_ns, size):
    return {
        str(record["id"]): record
        for page in json.loads(Path(path).read_text())
        for record in page.get("resultList", {}).get("result", [])
        if record.get("source") == "MED" and record.get("id")
    }


def indexed_source_urls(record, work):
    raw_path = work / "search_raw.json"
    metadata = {}
    if raw_path.exists():
        state = raw_path.stat()
        metadata = metadata_index(
            str(raw_path.resolve()), state.st_mtime_ns, state.st_size
        ).get(str(record["id"]), {})
    return list(record.get("source_urls", [])) + [
        link["url"]
        for link in metadata.get("fullTextUrlList", {}).get("fullTextUrl", [])
        if link.get("availabilityCode") in ("OA", "F") and link.get("url")
    ]


def indexed_pdf(record, work, folder, model=None):
    return discover_pdf(
        record,
        folder,
        indexed_source_urls(record, work),
        web_fallback=os.getenv("ASR_WEB_DISCOVERY", "1") != "0",
        model=model,
    )

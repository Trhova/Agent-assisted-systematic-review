"""Frozen bibliographic-only hand-search leads; never preaccepted trial data."""
import json
from pathlib import Path
from urllib.parse import urlparse

from scripts.model_backend import atomic_json, digest

FIELDS = {"id", "title", "abstract", "pmcid", "doi", "date", "publication_types",
          "related_notices", "source_urls", "discovery_source", "date_evidence"}


def load(protocol, work):
    spec = protocol.get("bibliographic_supplement")
    if not spec:
        return []
    data = json.loads(Path(spec["path"]).read_text())
    if digest(data) != spec["sha256"]:
        raise ValueError("Frozen bibliographic supplement checksum differs")
    ids = set()
    for row in data:
        if set(row) - FIELDS or not all(row.get(k) for k in ("id", "title", "discovery_source")):
            raise ValueError("Supplement must contain bibliographic leads only")
        if not row.get("doi") and not row.get("source_urls"):
            raise ValueError("A DOI or primary source URL is required for a bibliographic lead")
        if row["id"] in ids:
            raise ValueError("Duplicate supplemental bibliographic identity")
        ids.add(row["id"])
        if any(urlparse(url).scheme != "https" for url in row.get("source_urls", [])):
            raise ValueError("Supplement source URLs must be public HTTPS leads")
    atomic_json(work / "frozen_bibliographic_supplement.json", data)
    return data

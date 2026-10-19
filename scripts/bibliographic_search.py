"""Restartable Europe PMC MED search with durable page and cursor provenance."""

from __future__ import annotations

import json
import re
import time

from scripts.model_backend import atomic_json

URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def search(protocol, work, fetch, max_pages=1000):
    query = protocol["query"]
    if protocol.get("validate_query_fields"):
        field_path = work / "query_fields.json"
        fields = (
            json.loads(field_path.read_text())
            if field_path.exists()
            else fetch(
                "https://www.ebi.ac.uk/europepmc/webservices/rest/fields",
                params={"format": "json"},
            ).json()
        )
        atomic_json(field_path, fields)
        allowed = {item["term"] for item in fields["searchTermList"]["searchTerms"]}
        used = set(re.findall(r"\b([A-Z_]+):", query))
        if used - allowed:
            raise ValueError(
                "Unsupported bibliographic query fields: " + str(sorted(used - allowed))
            )
    path = work / "search.json"
    if path.exists():
        result = json.loads(path.read_text())
        if result.get("query") != query:
            raise ValueError("Cached search query differs from frozen protocol")
        if not (work / "search_raw.json").exists():
            raise ValueError("Cached search is missing raw bibliographic provenance")
        return result
    progress_path = work / "search_progress.json"
    if progress_path.exists():
        progress = json.loads(progress_path.read_text())
        if progress.get("query") != query:
            raise ValueError("Search checkpoint query differs from frozen protocol")
    else:
        progress = {
            "query": query,
            "pages": [],
            "requested_cursors": [],
            "next_cursor": "*",
            "finished": False,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    while not progress["finished"]:
        if len(progress["pages"]) >= max_pages:
            raise ValueError("Search page budget exhausted; checkpoint preserved")
        cursor = progress["next_cursor"]
        if cursor in progress["requested_cursors"]:
            raise ValueError("Search cursor cycle detected; checkpoint preserved")
        response = fetch(
            URL,
            params={
                "query": query,
                "format": "json",
                "resultType": "core",
                "pageSize": 1000,
                "cursorMark": cursor,
            },
        ).json()
        if "resultList" not in response or "result" not in response["resultList"]:
            raise ValueError("Malformed bibliographic response; checkpoint preserved")
        page = response["resultList"]["result"]
        if not isinstance(page, list):
            raise ValueError("Malformed bibliographic records")
        progress["pages"].append(response)
        progress["requested_cursors"].append(cursor)
        nxt = response.get("nextCursorMark")
        progress["next_cursor"] = nxt
        progress["finished"] = not nxt or nxt == cursor or not page
        progress["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        atomic_json(progress_path, progress)
    records = {}
    for response in progress["pages"]:
        for r in response["resultList"]["result"]:
            rid = r.get("id")
            if r.get("source") != "MED" or not rid:
                continue
            records[rid] = {
                "id": rid,
                "title": r.get("title", ""),
                "abstract": re.sub("<[^>]+>", " ", r.get("abstractText", "")),
                "pmcid": r.get("pmcid", ""),
                "doi": r.get("doi", ""),
                "date": r.get("firstPublicationDate", ""),
                "publication_types": r.get("pubTypeList", {}).get("pubType", []),
                "related_notices": r.get("commentCorrectionList", {}).get(
                    "commentCorrection", []
                ),
            }
    atomic_json(work / "search_raw.json", progress["pages"])
    result = {
        "query": query,
        "retrieved_at": progress["updated_at"],
        "started_at": progress["started_at"],
        "records": list(records.values()),
        "hit_count": progress["pages"][0].get("hitCount", 0),
        "database": "Europe PMC MED subset; not a historical database snapshot",
        "checkpoint_note": "Restarted pages may reflect index updates during retrieval; raw pages and request cursors retained.",
    }
    atomic_json(path, result)
    return result

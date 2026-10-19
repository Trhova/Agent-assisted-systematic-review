"""Resolve collection leads to bibliographic identities without reference answers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlencode

from scripts.acquisition import PublicFetcher
from scripts.discover_sources import normalized
from scripts.model_backend import atomic_json, digest


def resolve_candidates(candidates, directory, max_candidates=16):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    records, ledger = {}, []
    for index, candidate in enumerate(candidates):
        title = candidate["title"]
        item = {
            "source_title": title,
            "source_occurrences": candidate["occurrences"],
            "status": "unresolved",
        }
        if index >= max_candidates or not title.strip():
            item["reason"] = "Candidate budget exceeded or source title absent"
            ledger.append(item)
            continue
        fetcher = PublicFetcher(
            directory / digest(title),
            max_requests=4,
            seconds=60,
            host_cache=directory / "hosts",
        )
        query = 'TITLE:"' + re.sub(r"[^\w\s-]", " ", title) + '" AND SRC:MED'
        try:
            url = (
                "https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
                + urlencode(
                    {
                        "query": query,
                        "format": "json",
                        "resultType": "core",
                        "pageSize": 10,
                    }
                )
            )
            raw, _ = fetcher.get(url)
            hits = json.loads(raw).get("resultList", {}).get("result", [])
            matches = [
                r
                for r in hits
                if normalized(r.get("title", "")) == normalized(title)
                and r.get("source") == "MED"
            ]
            if len(matches) != 1:
                item["reason"] = "No unique exact normalized title match in MED"
                item["hit_count"] = len(hits)
            else:
                r = matches[0]
                record = {
                    "id": r["id"],
                    "title": r["title"],
                    "abstract": re.sub("<[^>]+>", " ", r.get("abstractText", "")),
                    "pmcid": r.get("pmcid", ""),
                    "doi": r.get("doi", ""),
                    "date": r.get("firstPublicationDate", ""),
                    "publication_types": r.get("pubTypeList", {}).get("pubType", []),
                }
                records[record["id"]] = record
                item.update(status="resolved", record_id=record["id"])
        except Exception as error:
            item["reason"] = str(error)
        ledger.append(item)
        atomic_json(
            directory / "progress.json",
            {"records": list(records.values()), "ledger": ledger},
        )
    result = {
        "records": list(records.values()),
        "ledger": ledger,
        "status": "resolved"
        if all(x["status"] == "resolved" for x in ledger)
        else "incomplete",
    }
    atomic_json(directory / "result.json", result)
    return result

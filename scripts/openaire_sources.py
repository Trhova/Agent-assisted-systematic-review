"""Public OpenAIRE repository discovery, with DOI identity and access checks."""

import json
from urllib.parse import urlencode

from scripts.model_backend import atomic_json


def many(value):
    return value if isinstance(value, list) else [value] if value else []


def open_locations(payload, doi):
    results = payload.get("response", {}).get("results", {}).get("result", [])
    urls = []
    for result in many(results):
        record = result.get("metadata", {}).get("oaf:entity", {}).get("oaf:result", {})
        ids = many(record.get("pid"))
        if not any(
            p.get("@classid") == "doi" and str(p.get("$", "")).lower() == doi.lower()
            for p in ids
        ):
            continue
        for child in many(record.get("children", {}).get("result")):
            for instance in many(child.get("instance")):
                if instance.get("accessright", {}).get("@classid") != "OPEN":
                    continue
                for resource in many(instance.get("webresource")):
                    url = resource.get("url", {}).get("$", "")
                    if url.startswith(("https://", "http://")) and url not in urls:
                        urls.append(url)
    return urls


def discover(doi, folder, fetcher):
    url = "https://api.openaire.eu/search/publications?" + urlencode(
        {"doi": doi, "format": "json"}
    )
    body, metadata = fetcher.get(url)
    payload = json.loads(body)
    urls = open_locations(payload, doi)
    atomic_json(
        folder / "openaire.json",
        {"response": payload, "acquisition": metadata, "open_urls": urls},
    )
    return urls

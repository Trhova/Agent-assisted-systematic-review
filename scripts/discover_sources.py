"""Automatic DOI/metadata source discovery, independent of benchmark references."""

from __future__ import annotations

import hashlib
import importlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin

import pdfplumber

from scripts.acquisition import AcquisitionError, PublicFetcher
from scripts.model_backend import atomic_json, digest


class PDFLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name", "").lower() in {
            "citation_pdf_url",
            "wkhealth_pdf_url",
        }:
            self.links.append(attrs.get("content", ""))
        if tag == "link" and attrs.get("type", "").lower() == "application/pdf":
            self.links.append(attrs.get("href", ""))


def normalized(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def source_identity(record, first_page):
    # Only the front page counts: a DOI in a cited bibliography is not identity.
    text = normalized(first_page)
    title = normalized(record.get("title", ""))
    doi = record.get("doi", "").lower().strip()
    # Allow PDF line breaks inside a DOI, but do not accept a DOI-prefix match
    # (10.1234/trial must not identify 10.1234/trial-followup).
    doi_pattern = (
        r"(?<![a-z0-9])"
        + r"\s*".join(re.escape(c) for c in doi)
        + r"(?=$|\s|[<>\"')\]}]|[.,;:](?=$|\s))"
    )
    doi_match = bool(doi and re.search(doi_pattern, first_page.lower()))
    title_match = len(title) >= 30 and title in text
    return {
        "verified": doi_match or title_match,
        "doi_front_page": doi_match,
        "title_front_page": title_match,
        "method": "exact normalized title or DOI on first page",
    }


def front_page_text(pdf):
    with pdfplumber.open(pdf) as document:
        return document.pages[0].extract_text() or "" if document.pages else ""


def discover_pdf(
    record,
    folder,
    indexed_urls=(),
    fetcher=None,
    web_fallback=False,
    providers=True,
    model=None,
):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    fetcher = fetcher or PublicFetcher(
        folder / "acquisition", host_cache=folder.parent / "acquisition_hosts"
    )
    log = {"record_id": record["id"], "version": 1, "candidates": [], "errors": []}
    queue = [(u, "bibliographic index") for u in indexed_urls]
    doi = record.get("doi", "").strip()
    # Public repository locations can succeed when the publisher blocks requests.
    if doi and providers:
        try:
            raw, meta = fetcher.get(
                "https://api.openalex.org/works/https://doi.org/" + quote(doi, safe="/")
            )
            item = json.loads(raw)
            atomic_json(
                folder / "openalex.json", {"response": item, "acquisition": meta}
            )
            if (
                item.get("doi", "").lower().removeprefix("https://doi.org/")
                != doi.lower()
            ):
                raise AcquisitionError("OpenAlex DOI identity mismatch")
            for location in item.get("locations", []):
                if location.get("is_oa"):
                    for key in ("pdf_url", "landing_page_url"):
                        if location.get(key):
                            queue.append(
                                (location[key], "OpenAlex open repository location")
                            )
        except Exception as error:
            log["errors"].append({"stage": "openalex", "error": str(error)})
    if doi and providers:
        try:
            from scripts.openaire_sources import discover as discover_openaire

            queue.extend(
                (url, "OpenAIRE open repository location")
                for url in discover_openaire(doi, folder, fetcher)
            )
        except (AcquisitionError, ValueError, TypeError, AttributeError, OSError) as error:
            log["errors"].append({"stage": "openaire", "error": str(error)})
    if providers and record.get("id", "").isdigit():
        try:
            raw, meta = fetcher.get(
                "https://api.semanticscholar.org/graph/v1/paper/PMID:"
                + record["id"]
                + "?fields=title,externalIds,openAccessPdf"
            )
            item = json.loads(raw)
            atomic_json(
                folder / "semantic_scholar.json",
                {"response": item, "acquisition": meta},
            )
            if str(item.get("externalIds", {}).get("PubMed", "")) != record["id"]:
                raise AcquisitionError("Semantic Scholar PMID identity mismatch")
            pdf_url = (item.get("openAccessPdf") or {}).get("url")
            if pdf_url:
                queue.append((pdf_url, "Semantic Scholar open-access location"))
        except Exception as error:
            log["errors"].append({"stage": "semantic_scholar", "error": str(error)})
    if doi and providers:
        try:
            raw, meta = fetcher.get(
                "https://api.crossref.org/works/" + quote(doi, safe="")
            )
            item = json.loads(raw)["message"]
            atomic_json(
                folder / "crossref.json", {"response": item, "acquisition": meta}
            )
            if item.get("DOI", "").lower() != doi.lower():
                raise AcquisitionError("Crossref DOI identity mismatch")
            for link in item.get("link", []):
                if link.get("content-type") in {"application/pdf", "unspecified"}:
                    queue.append((link["URL"], "Crossref full-text metadata"))
            landing = item.get("resource", {}).get("primary", {}).get(
                "URL"
            ) or item.get("URL")
            if landing:
                queue.append((landing, "Crossref publisher landing"))
        except Exception as error:
            log["errors"].append({"stage": "crossref", "error": str(error)})
        queue.append(("https://doi.org/" + quote(doi, safe="/"), "DOI resolver"))
    seen = set()
    for url, origin in queue:
        if not url or url in seen or len(seen) >= 10:
            continue
        seen.add(url)
        item = {"url": url, "origin": origin}
        log["candidates"].append(item)
        try:
            body, meta = fetcher.get(url)
            if not body.startswith(b"%PDF"):
                from scripts.html_fulltext import extract_html

                html = extract_html(record, body, meta["url"])
                if html:
                    artifact = folder / ("accepted-" + digest(url)[:12] + ".html")
                    artifact.write_bytes(body)
                    html["html_relative_path"] = artifact.name
                    html["acquisition_method"] = (
                        "automatic DOI/index/publisher metadata; scholarly HTML"
                    )
                    item.update(status="accepted_html", identity=html["identity"])
                    atomic_json(folder / "discovery.json", log)
                    return html
                parser = PDFLinks()
                parser.feed(body.decode("utf-8", errors="replace"))
                queue.extend(
                    (urljoin(meta["url"], u), "publisher PDF metadata")
                    for u in parser.links[:3]
                )
                item["status"] = "landing_page"
                continue
            pdf = folder / ("discovered-" + digest(url)[:12] + ".pdf")
            pdf.write_bytes(body)
            identity = source_identity(record, front_page_text(pdf))
            item["identity"] = identity
            if not identity["verified"]:
                item["status"] = "identity_unverified"
                continue
            parsed = importlib.import_module(
                "scripts.02_download_pdfs"
            ).extract_pdf_text(pdf)
            pages = parsed["pages"]
            text = "\n".join(f"[page {p['page']}] {p['text']}" for p in pages)
            if len(text) < 500:
                item["status"] = "insufficient_text"
                continue
            item["status"] = "accepted"
            atomic_json(folder / "discovery.json", log)
            return {
                "text": text,
                "sha256": digest(text),
                "url": meta["url"],
                "format": "automatically discovered public PDF",
                "pdf_relative_path": pdf.name,
                "pdf_sha256": hashlib.sha256(body).hexdigest(),
                "identity": identity,
                "acquisition_method": "automatic DOI/index/publisher metadata",
                "license": "No redistribution license asserted; public access only",
                "parser_version": 2,
            }
        except Exception as error:
            item.update(status="failed", error=str(error))
        atomic_json(folder / "discovery.json", log)
    if web_fallback:
        try:
            from scripts.web_source_discovery import discover

            urls = discover(record, folder, model=model)
            log["web_candidate_urls"] = urls
            if urls:
                candidate_folder = folder / "web_candidate_downloads"
                result = discover_pdf(
                    record,
                    candidate_folder,
                    urls,
                    fetcher=PublicFetcher(
                        candidate_folder / "acquisition",
                        max_requests=8,
                        seconds=90,
                        host_cache=folder.parent / "acquisition_hosts",
                    ),
                    web_fallback=False,
                    providers=False,
                )
                if result:
                    for artifact_key in ["pdf_relative_path", "html_relative_path"]:
                        if result.get(artifact_key):
                            result[artifact_key] = (
                                "web_candidate_downloads/" + result[artifact_key]
                            )
                    result["acquisition_method"] = (
                        "automatic audited web discovery followed by source identity verification"
                    )
                    result["discovery_artifacts"] = str(folder / "web_discovery.json")
                    atomic_json(folder / "discovery.json", log)
                    return result
                # A public-copy landing page is not full-text access. One bounded
                # alternate search can try different sources after download failure.
                alternatives = discover(
                    record, folder / "alternate_search", model=model, failed_urls=urls
                )
                alternatives = [u for u in alternatives if u not in urls]
                log["alternate_candidate_urls"] = alternatives
                if alternatives:
                    alternate_folder = folder / "alternate_candidate_downloads"
                    result = discover_pdf(
                        record,
                        alternate_folder,
                        alternatives,
                        fetcher=PublicFetcher(
                            alternate_folder / "acquisition",
                            max_requests=8,
                            seconds=90,
                            host_cache=folder.parent / "acquisition_hosts",
                        ),
                        web_fallback=False,
                        providers=False,
                    )
                    if result:
                        for artifact_key in ["pdf_relative_path", "html_relative_path"]:
                            if result.get(artifact_key):
                                result[artifact_key] = (
                                    "alternate_candidate_downloads/"
                                    + result[artifact_key]
                                )
                        result["acquisition_method"] = (
                            "automatic audited alternate-source search after inaccessible public-copy candidates"
                        )
                        result["discovery_artifacts"] = str(
                            folder / "alternate_search" / "web_discovery.json"
                        )
                        atomic_json(folder / "discovery.json", log)
                        return result
        except Exception as error:
            log["errors"].append({"stage": "web_discovery", "error": str(error)})
    atomic_json(folder / "discovery.json", log)
    return None

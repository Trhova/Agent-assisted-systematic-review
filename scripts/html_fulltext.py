"""Conservative scholarly HTML extraction; abstract-only pages are not full texts."""

from __future__ import annotations

import hashlib
import re

from bs4 import BeautifulSoup

from scripts.model_backend import digest


def normalized(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def abstract_heading(heading, article):
    for parent in heading.parents:
        labels = " ".join(str(parent.get(k, "")) for k in ["id", "class", "data-title"])
        if "abstract" in labels.lower() or str(
            parent.get("aria-labelledby", "")
        ).lower().startswith("abs"):
            return True
        if parent is article:
            break
    return False


def extract_html(record, raw, url):
    if b"<html" not in raw[:10000].lower():
        return None
    soup = BeautifulSoup(raw, "html.parser")
    metadata = {}
    for tag in soup.find_all("meta"):
        key = tag.get("name", "").lower()
        if key in {"citation_title", "citation_doi", "citation_pmid"}:
            metadata[key] = tag.get("content", "").strip()
    doi = metadata.get("citation_doi", "").lower().removeprefix("https://doi.org/")
    expected_doi = record.get("doi", "").lower().strip()
    if doi and expected_doi and doi != expected_doi:
        return None
    if metadata.get("citation_pmid") and metadata["citation_pmid"] != record["id"]:
        return None
    title = normalized(metadata.get("citation_title", ""))
    title_match = len(title) >= 30 and title == normalized(record.get("title", ""))
    doi_match = bool(doi and expected_doi and doi == expected_doi)
    if not doi_match and not title_match:
        return None
    for tag in soup.select(
        "script, style, nav, header, footer, aside, form, .ref-list, .references, [data-title='References'], section[id^='ref-list']"
    ):
        tag.decompose()
    # These are scientific article containers, never the whole site body.
    candidates = soup.select(
        "[itemprop='articleBody'], #artText, .article-body, article"
    )
    candidates.sort(key=lambda x: len(x.get_text(" ", strip=True)), reverse=True)
    for article in candidates:
        headings = [
            h.get_text(" ", strip=True).lower()
            for h in article.find_all("h2")
            if not abstract_heading(h, article)
        ]
        # Requiring full section headings prevents structured abstract H3s from
        # turning subscription landing pages into purported full-text reports.
        if not any(re.search(r"\bmethods\b", h) for h in headings):
            continue
        if not any(re.search(r"\bresults\b", h) for h in headings):
            continue
        if len(article.get_text(" ", strip=True)) < 5000:
            continue
        # Preserve cell boundaries rather than concatenating adjacent numbers.
        for table in article.find_all("table"):
            rows = []
            caption = table.find("caption")
            if caption:
                rows.append(caption.get_text(" ", strip=True))
            for row in table.find_all("tr"):
                rows.append(
                    " | ".join(
                        cell.get_text(" ", strip=True)
                        for cell in row.find_all(["th", "td"], recursive=False)
                    )
                )
            table.replace_with("\n" + "\n".join(rows) + "\n")
        text = (
            "Article title: "
            + metadata.get("citation_title", record.get("title", ""))
            + "\n"
            + article.get_text("\n", strip=True)
        )
        return {
            "text": text,
            "sha256": digest(text),
            "url": url,
            "format": "automatically discovered scholarly HTML",
            "identity": {
                "doi_metadata": doi_match,
                "title_metadata": title_match,
                "metadata": metadata,
            },
            "html_sha256": hashlib.sha256(raw).hexdigest(),
            "parser_version": 2,
            "html_parser_version": 1,
            "coverage": "Scientific article container with full Methods and Results section headings; no character truncation",
            "projection_exclusions": [
                "scripts and styles",
                "site navigation",
                "reference list",
            ],
            "license": "No redistribution license asserted; public access only",
        }
    return None

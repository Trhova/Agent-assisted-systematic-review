"""Retain JATS front matter and recover image-only tables from licensed PDFs."""

from __future__ import annotations

import importlib
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.model_backend import atomic_json, digest
from scripts.pmc_cloud import download_pdf


def upgrade_source(record, folder: Path, doc):
    already_parsed = doc.get("parser_version") == 2
    if already_parsed and (
        not doc.get("table_recovery_error")
        or time.time() - doc.get("table_recovery_attempt_epoch", 0) < 3600
    ):
        return doc
    original = dict(doc)
    xml_path = folder / "article.xml"
    if xml_path.exists():
        root = ET.fromstring(xml_path.read_text())
        names = [
            " ".join(n.itertext())
            for n in root.findall(".//front/article-meta/contrib-group/contrib/name")
        ]
        title = root.find(".//front/article-meta/title-group/article-title")
        header = "Article authors: " + "; ".join(names)
        if title is not None:
            header += "\nArticle title: " + " ".join(title.itertext())
        if not already_parsed:
            doc["text"] = header + "\n" + doc["text"]
        image_tables = [
            t.get("id", "")
            for t in root.findall(".//table-wrap")
            if t.find(".//graphic") is not None and t.find(".//table") is None
        ]
        doc["image_tables"] = image_tables
        if image_tables and len(doc["text"]) < 500_000 and record.get("pmcid"):
            doc["table_recovery_attempt_epoch"] = time.time()
            pdf = folder / "article.cloud.pdf"
            if not pdf.exists():
                ok, metadata = download_pdf(record["pmcid"], pdf, record["id"])
                atomic_json(folder / "cloud_retrieval.json", metadata)
            else:
                ok = True
                metadata = (
                    json.loads((folder / "cloud_retrieval.json").read_text())
                    if (folder / "cloud_retrieval.json").exists()
                    else {}
                )
            if ok:
                parsed = importlib.import_module(
                    "scripts.02_download_pdfs"
                ).extract_pdf_text(pdf)
                atomic_json(folder / "cloud_pdf_text.json", parsed)
                pdf_text = "\n".join(
                    f"[PDF page {p['page']}] {p['text']}"
                    for p in parsed.get("pages", [])
                )
                if len(pdf_text) > 500:
                    doc["text"] += (
                        "\nSUPPLEMENTARY VIEW OF THE SAME ARTICLE FROM PMC CLOUD PDF:\n"
                        + pdf_text
                    )
                    doc.pop("table_recovery_error", None)
                    doc["pdf_source"] = metadata.get("url")
                    doc["format"] += " + PMC Cloud PDF"
            else:
                doc["table_recovery_error"] = metadata
    doc["parser_version"] = 2
    doc["sha256"] = digest(doc["text"])
    atomic_json(folder / ("text." + original["sha256"][:12] + ".json"), original)
    atomic_json(folder / "text.json", doc)
    return doc

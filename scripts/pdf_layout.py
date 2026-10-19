"""Audited alternative reading order for large multi-column collections.

The original PDF/text is never replaced. Pages with no clear central gutter keep
the original extraction order. This is a discovery projection, not OCR or proof
that table/image semantics have been recovered.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pdfplumber

from scripts.model_backend import atomic_json, digest


def has_central_gutter(chars, width, x_origin=0):
    middle = x_origin + width / 2
    left = [c for c in chars if c["x1"] <= middle]
    right = [c for c in chars if c["x0"] >= middle]
    crossing = [
        c for c in chars if c["x0"] < middle < c["x1"] and c.get("text", "").strip()
    ]
    return not crossing and len(left) >= 200 and len(right) >= 200


def source_pdf(folder, document):
    """Locate only the accepted PDF, including old discovery ledgers."""
    folder = Path(folder)
    relative = document.get("pdf_relative_path")
    if relative:
        path = (folder / relative).resolve()
        if not path.is_relative_to(folder.resolve()):
            raise ValueError("PDF source path escapes its artifact directory")
        if not path.is_file() or hashlib.sha256(
            path.read_bytes()
        ).hexdigest() != document.get("pdf_sha256"):
            raise ValueError("Accepted PDF missing or checksum changed")
        return path
    # Backward-compatible lookup from source identity and acquisition evidence,
    # never the first arbitrary PDF downloaded while trying candidate URLs.
    accepted = []
    for directory in [
        folder,
        folder / "web_candidate_downloads",
        folder / "alternate_candidate_downloads",
    ]:
        ledger = directory / "discovery.json"
        if not ledger.exists():
            continue
        for candidate in json.loads(ledger.read_text()).get("candidates", []):
            if candidate.get("status") == "accepted" and candidate.get(
                "identity", {}
            ).get("verified"):
                path = directory / (
                    "discovered-" + digest(candidate["url"])[:12] + ".pdf"
                )
                if path.is_file():
                    accepted.append(path)
    if len(accepted) == 1:
        return accepted[0]
    if len(accepted) > 1:
        raise ValueError("Ambiguous accepted PDF sources")
    if document.get("format", "").startswith("automatically discovered"):
        return None
    for name in ["article.pdf", "article.cloud.pdf"]:
        path = folder / name
        if path.is_file():
            return path
    return None


def project_pdf(pdf_path, output, parent_source_sha256=None):
    pdf_path, output = Path(pdf_path), Path(output)
    file_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    previous_root = output / (file_hash + "-v2")
    root = output / (file_hash + "-v3")
    root.mkdir(parents=True, exist_ok=True)
    cache = root / "document.json"
    if cache.exists():
        return json.loads(cache.read_text())
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for index, page in enumerate(pdf.pages, 1):
            path = root / f"page-{index:05d}.json"
            previous = previous_root / path.name
            if not path.exists() and previous.exists():
                candidate = json.loads(previous.read_text())
                boxes = [part["bbox"] for part in candidate["parts"]]
                x0, top, x1, bottom = page.bbox
                expected = (
                    [[x0, top, x1, bottom]]
                    if len(boxes) == 1
                    else [
                        [x0, top, (x0 + x1) / 2, bottom],
                        [(x0 + x1) / 2, top, x1, bottom],
                    ]
                )
                if boxes == expected and candidate.get("pdf_sha256") == file_hash:
                    candidate["reused_from"] = str(previous)
                    atomic_json(path, candidate)
            if path.exists():
                result = json.loads(path.read_text())
            else:
                x0, top, x1, bottom = page.bbox
                middle = (x0 + x1) / 2
                if has_central_gutter(page.chars, x1 - x0, x0):
                    boxes = [(x0, top, middle, bottom), (middle, top, x1, bottom)]
                    parts = [
                        {
                            "bbox": list(box),
                            "text": page.crop(box).extract_text(x_tolerance=1) or "",
                        }
                        for box in boxes
                    ]
                    method = "left column then right column; central gutter contains no text glyphs"
                else:
                    parts = [
                        {
                            "bbox": [x0, top, x1, bottom],
                            "text": page.extract_text(x_tolerance=1) or "",
                        }
                    ]
                    method = "original full-page order; no confident two-column split"
                result = {
                    "page": index,
                    "method": method,
                    "parts": parts,
                    "pdf_sha256": file_hash,
                }
                atomic_json(path, result)
            pages.append(result)
            page.close()
    text = "\n".join(
        f"[page {p['page']} region {i + 1}] {part['text']}"
        for p in pages
        for i, part in enumerate(p["parts"])
    )
    result = {
        "text": text,
        "sha256": digest(text),
        "pdf_sha256": file_hash,
        "parent_source_sha256": parent_source_sha256,
        "url": str(pdf_path),
        "format": "PDF geometric reading-order discovery projection",
        "parser_version": 3,
        "x_tolerance": 1,
        "pages": len(pages),
        "two_column_pages": sum(len(p["parts"]) == 2 for p in pages),
        "limitations": [
            "No OCR or automatic table interpretation",
            "Unsplittable pages retain possibly interleaved source order",
        ],
        "geometry_directory": str(root),
    }
    atomic_json(cache, result)
    return result

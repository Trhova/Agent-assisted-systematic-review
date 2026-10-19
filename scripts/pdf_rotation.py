"""Append provenance-bearing readable views of predominantly rotated PDF pages."""

from __future__ import annotations

import hashlib
import io
import math
from collections import Counter

import pdfplumber
from pdfplumber.utils.exceptions import PdfminerException
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from scripts.model_backend import atomic_json, digest
from scripts.pdf_layout import source_pdf


def dominant_rotation(chars):
    """Require at least 100 glyphs and 80% agreement on a cardinal rotation."""
    angles = []
    for char in chars:
        if not char.get("text", "").strip() or not char.get("matrix"):
            continue
        a, b = char["matrix"][:2]
        angle = math.degrees(math.atan2(b, a)) % 360
        cardinal = round(angle / 90) * 90 % 360
        if abs((angle - cardinal + 180) % 360 - 180) <= 2:
            angles.append(cardinal)
        else:
            angles.append(None)
    if len(angles) < 100:
        return 0
    angle, count = Counter(angles).most_common(1)[0]
    return angle if angle in (90, 180, 270) and count / len(angles) >= 0.8 else 0


def _append_rotated_view(folder, document):
    if document.get("rotation_view_version") == 1:
        return document
    pdf_path = source_pdf(folder, document)
    if pdf_path is None:
        return document
    original = dict(document)
    pdf_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    rotations = []
    with pdfplumber.open(pdf_path) as pdf:
        for index, page in enumerate(pdf.pages):
            rotation = dominant_rotation(page.chars)
            if rotation:
                rotations.append((index, rotation))
            page.close()
    views = []
    if rotations:
        reader = PdfReader(pdf_path)
        for index, rotation in rotations:
            writer = PdfWriter()
            page = reader.pages[index]
            page.rotate(rotation)
            writer.add_page(page)
            buffer = io.BytesIO()
            writer.write(buffer)
            buffer.seek(0)
            with pdfplumber.open(buffer) as pdf:
                text = pdf.pages[0].extract_text(x_tolerance=1) or ""
            views.append(
                {"page": index + 1, "clockwise_rotation": rotation, "text": text}
            )
    projection = {
        "version": 1,
        "pdf_sha256": pdf_hash,
        "parent_source_sha256": document["sha256"],
        "method": "Cardinal glyph-matrix majority; 100+ nonspace glyphs, >=80% agreement; in-memory page rotation, no OCR or numerical changes",
        "pages": views,
    }
    atomic_json(folder / ("rotation-view-" + pdf_hash[:16] + ".json"), projection)
    if views:
        document["text"] += (
            "\nALTERNATE ROTATION-CORRECTED VIEW OF THE SAME PRIMARY PDF:\n"
            + "\n".join(
                f"[Original PDF page {v['page']}; view rotated {v['clockwise_rotation']} degrees clockwise]\n{v['text']}"
                for v in views
            )
        )
        document["sha256"] = digest(document["text"])
    document["rotation_view_version"] = 1
    document["rotation_view"] = {k: v for k, v in projection.items() if k != "pages"}
    document["rotation_view"]["pages"] = [v["page"] for v in views]
    atomic_json(
        folder / ("text.before-rotation-" + original["sha256"][:12] + ".json"), original
    )
    atomic_json(folder / "text.json", document)
    return document


def append_rotated_view(folder, document):
    try:
        return _append_rotated_view(folder, document)
    except (PdfminerException, PdfReadError) as error:
        # An optional reading-order view must not erase usable JATS/primary text.
        # Identity/checksum failures are deliberately NOT caught here.
        document = dict(document)
        document["rotation_view_version"] = 1
        document["rotation_view_error"] = str(error)
        atomic_json(
            folder / "rotation-view-error.json",
            {"parent_source_sha256": document["sha256"], "error": str(error)},
        )
        atomic_json(folder / "text.json", document)
        return document

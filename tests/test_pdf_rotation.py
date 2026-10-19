import hashlib

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from scripts.model_backend import digest
from scripts.pdf_rotation import append_rotated_view, dominant_rotation


def test_rotation_detection_requires_dominant_supported_geometry():
    turned = {"text": "A", "matrix": (0, 9, -9, 0, 1, 1)}
    upright = {"text": "B", "matrix": (9, 0, 0, 9, 1, 1)}
    assert dominant_rotation([turned] * 101) == 90
    assert dominant_rotation([turned] * 99) == 0
    assert dominant_rotation([turned] * 100 + [upright] * 100) == 0


@pytest.mark.parametrize("matrix", ["0 1 -1 0", "-1 0 0 -1", "0 -1 1 0"])
def test_rotated_view_preserves_raw_source_and_numeric_order(tmp_path, matrix):
    writer = PdfWriter()
    page = writer.add_blank_page(800, 800)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    content = DecodedStreamObject()
    line = "FBG 7.2 1.2 48 placebo 8.2 2.3 53"
    content.set_data(
        (
            "BT /F1 10 Tf " + matrix + " 400 400 Tm (" + (line + " ") * 5 + ") Tj ET"
        ).encode()
    )
    page[NameObject("/Contents")] = writer._add_object(content)
    path = tmp_path / "article.pdf"
    writer.write(path)
    raw = path.read_bytes()
    original = {
        "text": "original raw view",
        "sha256": digest("original raw view"),
        "pdf_relative_path": path.name,
        "pdf_sha256": hashlib.sha256(raw).hexdigest(),
    }
    doc = append_rotated_view(tmp_path, original.copy())
    assert doc["text"].startswith(original["text"])
    assert line in doc["text"]
    assert doc["rotation_view"]["parent_source_sha256"] == original["sha256"]
    assert doc["rotation_view"]["pages"] == [1]
    assert path.read_bytes() == raw
    assert append_rotated_view(tmp_path, doc.copy()) == doc
    assert list(tmp_path.glob("text.before-rotation-*.json"))


def test_optional_projection_failure_preserves_primary_text(tmp_path):
    (tmp_path / "article.pdf").write_bytes(b"not a PDF")
    original = {"text": "Usable primary JATS", "sha256": digest("Usable primary JATS")}
    doc = append_rotated_view(tmp_path, original)
    assert doc["text"] == original["text"]
    assert doc["sha256"] == original["sha256"]
    assert doc["rotation_view_error"]
    assert (tmp_path / "rotation-view-error.json").exists()

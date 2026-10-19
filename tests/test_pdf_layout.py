from scripts.pdf_layout import has_central_gutter


def test_column_split_requires_both_columns_and_no_crossing_glyph():
    left = [{"x0": 10, "x1": 20, "text": "x"}] * 250
    right = [{"x0": 70, "x1": 80, "text": "x"}] * 250
    assert has_central_gutter(left + right, 100)
    assert not has_central_gutter(left, 100)
    assert not has_central_gutter(
        left + right + [{"x0": 49, "x1": 51, "text": "x"}], 100
    )


def test_source_projection_selects_accepted_discovery_pdf_only(tmp_path):
    from scripts.model_backend import atomic_json, digest
    from scripts.pdf_layout import source_pdf

    rejected = {"url": "https://example.org/wrong", "status": "identity_unverified"}
    accepted = {
        "url": "https://example.org/right",
        "status": "accepted",
        "identity": {"verified": True},
    }
    directory = tmp_path / "web_candidate_downloads"
    atomic_json(directory / "discovery.json", {"candidates": [rejected, accepted]})
    for c in [rejected, accepted]:
        (directory / ("discovered-" + digest(c["url"])[:12] + ".pdf")).write_bytes(
            b"%PDF fixture"
        )
    expected = directory / ("discovered-" + digest(accepted["url"])[:12] + ".pdf")
    assert (
        source_pdf(tmp_path, {"format": "automatically discovered public PDF"})
        == expected
    )


def test_explicit_pdf_provenance_checks_path_and_hash(tmp_path):
    import hashlib

    import pytest

    from scripts.pdf_layout import source_pdf

    path = tmp_path / "source.pdf"
    path.write_bytes(b"%PDF source")
    doc = {
        "pdf_relative_path": path.name,
        "pdf_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    assert source_pdf(tmp_path, doc) == path
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        source_pdf(tmp_path, doc)
    with pytest.raises(ValueError, match="escapes"):
        source_pdf(tmp_path, {**doc, "pdf_relative_path": "../wrong.pdf"})


def test_nonzero_page_origin_never_crops_outside_parent(tmp_path, monkeypatch):
    from scripts.pdf_layout import project_pdf

    class Region:
        def extract_text(self, **kwargs):
            return "complete column"

    class Page:
        bbox = (2, -29, 602, 756)
        chars = [{"x0": 20, "x1": 30, "text": "a"}] * 220 + [
            {"x0": 500, "x1": 510, "text": "b"}
        ] * 220

        def crop(self, box):
            assert box[0] >= 2 and box[1] >= -29 and box[2] <= 602 and box[3] <= 756
            return Region()

        def close(self):
            pass

    class PDF:
        pages = [Page()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("scripts.pdf_layout.pdfplumber.open", lambda *a: PDF())
    path = tmp_path / "source.pdf"
    path.write_bytes(b"%PDF fixture")
    result = project_pdf(path, tmp_path / "layout")
    assert result["parser_version"] == 3
    assert result["two_column_pages"] == 1
    assert result["text"].count("complete column") == 2

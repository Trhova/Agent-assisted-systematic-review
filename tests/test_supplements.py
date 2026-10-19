import hashlib
import io
import json
import zipfile

import pytest

from scripts.model_backend import digest
from scripts.supplements import augment, linked_attachments, parse_attachment


def docx():
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        z.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Reported endpoint</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>12 ± 3</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>14 ± 4</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>',
        )
    return data.getvalue()


def test_docx_cells_and_challenge_rejection():
    assert "12 ± 3 | 14 ± 4" in parse_attachment(docx(), ".docx")
    with pytest.raises(ValueError, match="not a DOCX"):
        parse_attachment(b"<html>challenge</html>", ".docx")
    with pytest.raises(ValueError, match="not supported"):
        parse_attachment(b"data", ".xls")


def test_primary_link_only_and_no_duplicate_append(tmp_path, monkeypatch):
    raw = b'<html><section id="supplementary-material"><a href="/bin/s1.docx">Supplement 1</a></section><section class="ref-list"><a href="/bin/unrelated.pdf">Cited</a></section></html>'
    (tmp_path / "source.html").write_bytes(raw)
    doc = dict(
        text="primary",
        sha256=digest("primary"),
        url="https://example.org/paper",
        html_relative_path="source.html",
        html_sha256=hashlib.sha256(raw).hexdigest(),
    )
    assert linked_attachments(tmp_path, doc, {}) == ["https://example.org/bin/s1.docx"]
    calls = []

    def get(self, url):
        calls.append(url)
        body = docx()
        return body, {"sha256": hashlib.sha256(body).hexdigest()}

    monkeypatch.setattr("scripts.supplements.PublicFetcher.get", get)
    augmented = augment({}, tmp_path, doc)
    assert "12 ± 3 | 14 ± 4" in augmented["text"]
    assert augment({}, tmp_path, augmented) == augmented
    assert len(calls) == 1
    assert (
        json.loads(
            (tmp_path / augmented["supplements"]["primary_snapshot"]).read_text()
        )
        == doc
    )


def test_jats_links_and_attachment_bound(tmp_path, monkeypatch):
    (tmp_path / "article.xml").write_text(
        '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
        + "".join(f'<supplementary-material xlink:href="s{i}.txt"/>' for i in range(6))
        + "</article>"
    )
    doc = dict(text="primary", sha256=digest("primary"), format="JATS")
    monkeypatch.setattr(
        "scripts.supplements.PublicFetcher.get",
        lambda *a: (b"actual", {"sha256": hashlib.sha256(b"actual").hexdigest()}),
    )
    result = augment({"pmcid": "PMC123"}, tmp_path, doc)
    assert [a["status"] for a in result["supplements"]["attachments"]] == [
        "parsed"
    ] * 4 + ["not_attempted"] * 2
    assert (
        result["supplements"]["attachments"][0]["url"]
        == "https://pmc.ncbi.nlm.nih.gov/articles/PMC123/bin/s0.txt"
    )


def test_cloud_fallback_and_single_report_guard(tmp_path, monkeypatch):
    import scripts.autonomous_review as runner

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "scripts.acquisition.PublicFetcher.get",
        lambda *a: (_ for _ in ()).throw(ValueError("JATS unavailable")),
    )

    def download(pmcid, dest, expected):
        assert pmcid == "PMC123" and expected == "42"
        dest.write_bytes(b"%PDF-fixture")
        return True, {
            "url": "https://example.org/verified.pdf",
            "metadata": {"pmcid": pmcid, "pmid": expected},
        }

    monkeypatch.setattr("scripts.pmc_cloud.download_pdf", download)
    import importlib

    parser = importlib.import_module("scripts.02_download_pdfs")
    monkeypatch.setattr(
        parser,
        "extract_pdf_text",
        lambda *a: {"pages": [{"page": 1, "text": "actual report " * 60}]},
    )
    result = runner.fulltext({"id": "42", "pmcid": "PMC123"}, tmp_path)
    assert result["format"] == "PMC Cloud PDF"
    assert result["identity"]["pmid"] == "42"
    assert not runner.is_collection(
        {"title": "A randomized clinical trial with a long supplement"}
    )
    assert runner.is_collection({"title": "Conference abstracts"})


def test_archive_recovery_skips_unsupported_images_without_spending_bound(
    tmp_path, monkeypatch
):
    from scripts.supplements import archive_member

    xml = (
        '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
        + "".join(
            f'<supplementary-material xlink:href="image{i}.tiff"/>' for i in range(8)
        )
        + '<supplementary-material xlink:href="data.docx"/></article>'
    )
    (tmp_path / "article.xml").write_text(xml)
    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, "w") as z:
        z.writestr("PMC123/data.docx", docx())
    calls = []

    def get(self, url):
        calls.append(url)
        body = (
            bundle.getvalue()
            if url.endswith("supplementaryFiles")
            else b"<html>challenge</html>"
        )
        return body, {"sha256": hashlib.sha256(body).hexdigest()}

    monkeypatch.setattr("scripts.supplements.PublicFetcher.get", get)
    result = augment(
        {"pmcid": "PMC123"},
        tmp_path,
        dict(text="primary", sha256=digest("primary"), format="JATS"),
    )
    assert len(calls) == 2
    assert [a["status"] for a in result["supplements"]["attachments"]] == [
        "unsupported_format"
    ] * 8 + ["parsed"]
    assert "12 ± 3 | 14 ± 4" in result["text"]
    with pytest.raises(ValueError, match="absent or ambiguous"):
        archive_member(bundle.getvalue(), "other.docx")
    assert not (tmp_path / "PMC123").exists()  # Never extract archive paths to disk.


def test_docx_format_runs_do_not_corrupt_numbers_and_keep_explicit_boundaries():
    body=io.BytesIO()
    with zipfile.ZipFile(body,'w') as z:
        z.writestr('word/document.xml','''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Fig. S</w:t></w:r><w:r><w:t>15</w:t><w:tab/><w:t>caption</w:t><w:br/><w:t>next line</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>2</w:t></w:r><w:r><w:t>42</w:t></w:r></w:p><w:p><w:r><w:t>25 events</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>237</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>''')
    parsed=parse_attachment(body.getvalue(),'.docx')
    assert 'Fig. S15\tcaption\nnext line' in parsed
    assert '242\n25 events | 237' in parsed
    assert '2 42' not in parsed

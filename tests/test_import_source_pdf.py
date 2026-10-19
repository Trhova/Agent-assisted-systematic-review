import hashlib
import importlib
import json

import pytest

from scripts.import_source_pdf import import_pdf


@pytest.fixture
def source(tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"%PDF-1.7\nfixture")
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"url": "https://example.org/original.pdf", "status": 200,
                                  "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()}))
    monkeypatch.setattr("scripts.import_source_pdf.front_page_text", lambda p: "Original trial report DOI 10.1234/trial ")
    monkeypatch.setattr(importlib.import_module("scripts.02_download_pdfs"), "extract_pdf_text",
                        lambda p: {"pages": [{"page": 1, "text": "Original text " * 50}]})
    return pdf, receipt, tmp_path / "destination", {"id": "123", "doi": "10.1234/trial"}


def test_import_reparses_and_retains_originals(source):
    pdf, receipt, target, record = source
    doc = import_pdf(pdf, receipt, target, record=record)
    assert doc["text"].startswith("[page 1] Original text")
    assert (target / "original.pdf").read_bytes() == pdf.read_bytes()
    assert (target / "acquisition_receipt.json").read_bytes() == receipt.read_bytes()
    assert doc["identity"]["doi_front_page"]
    with pytest.raises(ValueError, match="empty"):
        import_pdf(pdf, receipt, target, record=record)


@pytest.mark.parametrize("change", ["checksum", "status", "url", "identity", "nonpdf"])
def test_import_rejects_unverified_sources(source, change):
    pdf, receipt, target, record = source
    data = json.loads(receipt.read_text())
    if change == "checksum":
        data["sha256"] = "wrong"
    elif change == "status":
        data["status"] = 403
    elif change == "url":
        data["url"] = "https://user:password@example.org/secret.pdf"
    elif change == "identity":
        record["doi"] = "10.1234/unrelated"
    else:
        pdf.write_bytes(b"<html>blocked</html>")
        data["sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    receipt.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        import_pdf(pdf, receipt, target, record=record)
    assert not target.exists()


def test_selected_pages_preserve_collection_and_exclude_other_reports(source):
    from pypdf import PdfWriter, PdfReader
    pdf, receipt, target, record = source
    writer=PdfWriter()
    for width in (101,202,303): writer.add_blank_page(width=width,height=100)
    with pdf.open('wb') as f: writer.write(f)
    r=json.loads(receipt.read_text());r['sha256']=hashlib.sha256(pdf.read_bytes()).hexdigest();receipt.write_text(json.dumps(r))
    doc=import_pdf(pdf,receipt,target,record=record,page_range=(2,3))
    assert (target/'retrieved_collection.pdf').read_bytes()==pdf.read_bytes()
    selected=PdfReader(target/'original.pdf')
    assert len(selected.pages)==2 and float(selected.pages[0].mediabox.width)==202
    assert doc['page_selection']['collection_sha256']==r['sha256']
    assert doc['pdf_sha256']==hashlib.sha256((target/'original.pdf').read_bytes()).hexdigest()
    assert (target/'acquisition_receipt.json').read_bytes()==receipt.read_bytes()
    with pytest.raises(ValueError,match='range'):
        import_pdf(pdf,receipt,target.parent/'bad',record=record,page_range=(0,2))

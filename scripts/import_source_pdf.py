"""Import an already retrieved original PDF with an immutable acquisition receipt.

No supplied extracted text or model decisions are trusted. Reparse the PDF and
verify article identity on its first page using the normal acquisition checks.
"""
import argparse
import hashlib
import importlib
import json
import io
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from scripts.discover_sources import front_page_text, source_identity
from scripts.model_backend import atomic_json, digest


def import_pdf(pdf, receipt, destination, *, record, page_range=None):
    pdf, receipt, destination = Path(pdf), Path(receipt), Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Source destination must be empty")
    raw, receipt_raw = pdf.read_bytes(), receipt.read_bytes()
    acquisition = json.loads(receipt_raw)
    checksum = hashlib.sha256(raw).hexdigest()
    if acquisition.get("status") != 200 or acquisition.get("sha256") != checksum:
        raise ValueError("Successful acquisition receipt and exact PDF checksum required")
    for key in ("url", "final_url"):
        if key == "final_url" and key not in acquisition:
            continue
        parts = urlsplit(acquisition.get(key, ""))
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ValueError("Public HTTPS source URL without credentials required")
    if not raw.startswith(b"%PDF-"):
        raise ValueError("Source is not a PDF")
    original_raw = raw
    selection = None
    if page_range is not None:
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(io.BytesIO(raw))
        if len(page_range) != 2 or any(type(n) is not int for n in page_range):
            raise ValueError("Page range requires two integer one-based bounds")
        first, last = page_range
        if not 1 <= first <= last <= len(reader.pages):
            raise ValueError("Page range outside retrieved collection")
        writer = PdfWriter()
        for index in range(first - 1, last):
            writer.add_page(reader.pages[index])
        buffer = io.BytesIO(); writer.write(buffer); raw = buffer.getvalue()
        selection = {"first_page": first, "last_page": last, "collection_pages": len(reader.pages),
                     "collection_relative_path": "retrieved_collection.pdf", "collection_sha256": checksum,
                     "selection": "contiguous caller-qualified original report; no completeness inferred from identity"}
    with tempfile.TemporaryDirectory(prefix="asr-pdf-import-") as temporary:
        parse_path = Path(temporary) / "selected.pdf"
        parse_path.write_bytes(raw)
        identity = source_identity(record, front_page_text(parse_path))
        if not identity["verified"]:
            raise ValueError("Primary article identity not established on first page")
        parsed = importlib.import_module("scripts.02_download_pdfs").extract_pdf_text(parse_path)
    checksum = hashlib.sha256(raw).hexdigest()
    text = "\n".join(f"[page {p['page']}] {p['text']}" for p in parsed["pages"])
    if len(text) < 500:
        raise ValueError("Insufficient original PDF text; OCR or manual source review needed")
    doc = {
        "text": text, "sha256": digest(text),
        "url": acquisition.get("final_url", acquisition["url"]),
        "format": "receipt-verified original PDF import", "parser_version": 2,
        "identity": identity, "pdf_relative_path": "original.pdf", "pdf_sha256": checksum,
        "acquisition_method": "preserved retrieval; first-page identity; fresh standard parser",
        "license": "No redistribution license asserted; public access only",
        "import_provenance": {
            "record": record, "receipt_relative_path": "acquisition_receipt.json",
            "receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
            "policy": "original_pdf_import_v1",
        },
    }
    if selection is not None:
        doc["page_selection"] = selection
        doc["import_provenance"]["policy"] = "original_pdf_page_import_v2"
        doc["format"] = "receipt-verified original report pages from PDF collection"
    destination.mkdir(parents=True, exist_ok=True)
    if selection is not None:
        (destination / "retrieved_collection.pdf").write_bytes(original_raw)
    (destination / "original.pdf").write_bytes(raw)
    (destination / "acquisition_receipt.json").write_bytes(receipt_raw)
    atomic_json(destination / "text.json", doc)
    return doc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--record", required=True, help="JSON bibliographic record")
    parser.add_argument("--pages", nargs=2, type=int, metavar=("FIRST", "LAST"))
    args = parser.parse_args()
    import_pdf(args.pdf, args.receipt, args.destination,
               record=json.loads(Path(args.record).read_text()), page_range=args.pages)


if __name__ == "__main__":
    main()

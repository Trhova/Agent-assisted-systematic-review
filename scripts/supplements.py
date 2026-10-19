"""Bounded attachments linked by a verified primary article; never execute files."""

from __future__ import annotations

import hashlib
import io
import json
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from scripts.acquisition import PublicFetcher
from scripts.model_backend import atomic_json, digest


def linked_attachments(folder, document, record):
    links = []
    base = document.get("url", "")
    html = document.get("html_relative_path")
    if html:
        path = (folder / html).resolve()
        if not path.is_relative_to(folder.resolve()):
            raise ValueError("HTML artifact escapes source folder")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != document.get("html_sha256"):
            raise ValueError("HTML artifact checksum changed")
        soup = BeautifulSoup(raw, "html.parser")
        for ref in soup.select(".ref-list, .references, section[id^='ref-list']"):
            ref.decompose()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            labels = " ".join(
                str(p.get("id", "")) + " " + str(p.get("class", ""))
                for p in [a, *a.parents]
                if hasattr(p, "get")
            )
            if "/bin/" in href or "supplement" in labels.lower():
                if Path(urlsplit(href).path).suffix.lower() in {
                    ".pdf",
                    ".docx",
                    ".txt",
                    ".csv",
                    ".xlsx",
                    ".xls",
                    ".doc",
                    ".zip",
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".tiff",
                    ".tif",
                }:
                    links.append(urljoin(base, href))
    xml = folder / "article.xml"
    if xml.exists() and document.get("format", "").startswith("JATS"):
        root = ET.fromstring(xml.read_bytes())
        for item in root.findall(".//supplementary-material"):
            for node in item.iter():
                href = node.get("{http://www.w3.org/1999/xlink}href")
                if href:
                    pmc_base = f"https://pmc.ncbi.nlm.nih.gov/articles/{record.get('pmcid', '')}/bin/"
                    links.append(urljoin(pmc_base, href))
    return list(dict.fromkeys(links))


def publisher_attachment_candidates(document, record, url):
    """Springer asset route bound to verified DOI and exact primary-linked name."""
    import re
    from urllib.parse import quote, unquote
    identity = document.get("identity", {})
    doi = identity.get("metadata", {}).get("citation_doi", "").lower()
    if not identity.get("doi_metadata") or doi != str(record.get("doi", "")).lower():
        return []
    match = re.fullmatch(r"10\.1007/s(\d+)-(\d{2,4})-(\d+)-[a-z0-9]+", doi)
    name = unquote(Path(urlsplit(url).path).name)
    asset = re.fullmatch(r"(\d+)_(\d{4})_(\d+)_MOESM\d+_ESM\.(docx|pdf|txt|csv)", name)
    if not match or not asset:
        return []
    journal, year, article = match.groups()
    if journal != asset[1] or year[-2:] != asset[2][-2:] or int(article) != int(asset[3]):
        return []
    return ["https://static-content.springer.com/esm/" + quote("art:" + doi, safe="") + "/MediaObjects/" + name]


def parse_attachment(body, suffix):
    if suffix == ".docx":
        if not body.startswith(b"PK"):
            raise ValueError("Attachment is not a DOCX ZIP container")
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            if sum(f.file_size for f in archive.infolist()) > 20_000_000:
                raise ValueError("DOCX uncompressed byte budget exceeded")
            raw = archive.read("word/document.xml")
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ValueError("XML entities are unsupported")
        root = ET.fromstring(raw)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        def paragraph_text(node):
            parts=[]
            for token in node.iter():
                if token.tag.endswith("}t"):
                    parts.append(token.text or "")
                elif token.tag.endswith("}tab"):
                    parts.append("\t")
                elif token.tag.endswith(("}br", "}cr")):
                    parts.append("\n")
            return "".join(parts)
        paragraphs = []
        for child in root.find("w:body", ns):
            if child.tag.endswith("}tbl"):
                for row in child.findall("w:tr", ns):
                    paragraphs.append(
                        " | ".join(
                            "\n".join(paragraph_text(p) for p in cell.findall(".//w:p", ns))
                            for cell in row.findall("w:tc", ns)
                        )
                    )
            else:
                paragraphs.append(
                    paragraph_text(child)
                )
        return "\n".join(paragraphs)
    if suffix == ".pdf":
        if not body.startswith(b"%PDF"):
            raise ValueError("Attachment is not PDF")
        import pdfplumber

        text = []
        with pdfplumber.open(io.BytesIO(body)) as pdf:
            if len(pdf.pages) > 100:
                raise ValueError("Supplement PDF exceeds 100-page parsing budget")
            for i, page in enumerate(pdf.pages, 1):
                text.append(f"[Supplement page {i}]\n" + (page.extract_text() or ""))
                page.close()
        return "\n".join(text)
    if suffix in {".txt", ".csv"}:
        text = body.decode("utf-8-sig")
        if "<html" in text[:1000].lower():
            raise ValueError("HTML challenge is not an attachment")
        return text
    raise ValueError("Attachment format is not supported")


def archive_member(body, basename):
    if not body.startswith(b"PK"):
        raise ValueError("Europe PMC supplementary response is not a ZIP archive")
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        infos = archive.infolist()
        if len(infos) > 1000 or sum(i.file_size for i in infos) > 50_000_000:
            raise ValueError(
                "Supplement archive exceeds member/uncompressed byte budget"
            )
        matches = [
            i for i in infos if Path(i.filename).name == basename and not i.is_dir()
        ]
        if len(matches) != 1:
            raise ValueError(
                "Linked attachment is absent or ambiguous in article archive"
            )
        return archive.read(matches[0]), matches[0].filename


def attachment_context(body,suffix,folder,item):
    if suffix != '.docx':return parse_attachment(body,suffix)
    from scripts.docx_evidence import extract,render
    raw=folder/item['relative_path']
    if hashlib.sha256(raw.read_bytes()).hexdigest()!=item['raw_sha256']:
        raise ValueError('Attachment raw checksum differs')
    asset_dir=folder/('docx-assets-'+item['raw_sha256'][:16])
    evidence=extract(raw,asset_dir)
    sidecar='docx-context-'+item['raw_sha256'][:16]+'.json'
    atomic_json(folder/sidecar,evidence)
    item['ordered_context']={'policy':evidence['policy'],'relative_path':sidecar,'sha256':hashlib.sha256((folder/sidecar).read_bytes()).hexdigest(),'asset_directory':asset_dir.name,'raw_sha256':item['raw_sha256']}
    item['parser_policy']='docx_evidence_order_v2'
    return render(evidence)


def augment(record, folder: Path, document):
    # Rebuild only from the preserved primary, never append an attachment twice.
    prior = document.get("supplements", {})
    if prior.get("version") == 2 and time.time() < prior.get(
        "retry_after_epoch", float("inf")
    ):
        return document
    if prior:
        document = json.loads((folder / prior["primary_snapshot"]).read_text())
    links = linked_attachments(folder, document, record)
    snapshot = "primary-" + document["sha256"][:16] + ".json"
    if not (folder / snapshot).exists():
        atomic_json(folder / snapshot, document)
    attachments = []
    fetcher = PublicFetcher(
        folder / "supplement_http",
        max_requests=8,
        seconds=90,
        io_timeout=30,
        host_cache=folder.parent / "acquisition_hosts",
    )
    additions = []
    attempted = 0
    for url in links:
        item = {"url": url}
        attachments.append(item)
        suffix = Path(urlsplit(url).path).suffix.lower()
        if suffix == ".docx":
            item["parser_policy"] = "docx_inline_text_v2"
        if suffix not in {".pdf", ".docx", ".txt", ".csv"}:
            item.update(
                status="unsupported_format",
                reason="No automatic parser for this attachment format",
            )
            continue
        if attempted >= 4:
            item.update(
                status="not_attempted",
                reason="Four supported attachment budget exhausted",
            )
            continue
        attempted += 1
        try:
            body, meta = fetcher.get(url)
            name = "supplement-" + meta["sha256"][:16] + suffix
            (folder / name).write_bytes(body)
            item.update(raw_sha256=meta["sha256"], relative_path=name)
            text = attachment_context(body, suffix, folder, item)
            if not text.strip():
                raise ValueError("Attachment has no extractable text")
            item.update(status="parsed", text_sha256=digest(text), characters=len(text))
            additions.append(
                "\nLINKED PRIMARY-ARTICLE SUPPLEMENT: " + url + "\n" + text
            )
        except Exception as error:
            item.update(status="unavailable_or_unsupported", reason=str(error))
            if record.get("pmcid"):
                archive_url = (
                    "https://www.ebi.ac.uk/europepmc/webservices/rest/"
                    + record["pmcid"]
                    + "/supplementaryFiles"
                )
                try:
                    bundle, meta = fetcher.get(archive_url)
                    archive_name = "supplement-archive-" + meta["sha256"][:16] + ".bin"
                    (folder / archive_name).write_bytes(bundle)
                    item["archive"] = {
                        "url": archive_url,
                        "relative_path": archive_name,
                        "sha256": meta["sha256"],
                    }
                    body, member = archive_member(bundle, Path(urlsplit(url).path).name)
                    raw_hash = hashlib.sha256(body).hexdigest()
                    name = "supplement-" + raw_hash[:16] + suffix
                    (folder / name).write_bytes(body)
                    item.update(raw_sha256=raw_hash, relative_path=name)
                    text = attachment_context(body, suffix, folder, item)
                    if not text.strip():
                        raise ValueError("Archived attachment has no extractable text")
                    item.update(
                        status="parsed",
                        direct_error=str(error),
                        archive_member=member,
                        raw_sha256=raw_hash,
                        relative_path=name,
                        text_sha256=digest(text),
                        characters=len(text),
                    )
                    additions.append(
                        "\nLINKED PRIMARY-ARTICLE SUPPLEMENT: "
                        + url
                        + "\nRETRIEVED VIA: "
                        + archive_url
                        + " MEMBER: "
                        + member
                        + "\n"
                        + text
                    )
                except Exception as archive_error:
                    item["archive_error"] = str(archive_error)
            if item["status"] != "parsed":
                for publisher_url in publisher_attachment_candidates(document, record, url):
                    attempt = {"url": publisher_url, "identity_basis": "verified primary DOI plus exact linked attachment filename", "policy": "springer_primary_attachment_v1"}
                    item.setdefault("publisher_attempts", []).append(attempt)
                    try:
                        body, meta = fetcher.get(publisher_url)
                        name = "supplement-" + meta["sha256"][:16] + suffix
                        (folder / name).write_bytes(body)
                        item.update(raw_sha256=meta["sha256"], relative_path=name)
                        text = attachment_context(body, suffix, folder, item)
                        if not text.strip():
                            raise ValueError("Publisher attachment has no extractable text")
                        item.update(status="parsed", text_sha256=digest(text), characters=len(text), retrieved_via=publisher_url)
                        attempt.update(status="parsed", raw_sha256=meta["sha256"])
                        additions.append("\nLINKED PRIMARY-ARTICLE SUPPLEMENT: " + url + "\nRETRIEVED VIA DOI/EXACT-FILENAME PUBLISHER ROUTE: " + publisher_url + "\n" + text)
                        break
                    except Exception as publisher_error:
                        attempt.update(status="unavailable_or_unsupported", reason=str(publisher_error))
    result = dict(document)
    result["supplement_text"] = "\n".join(additions)
    result["text"] += result["supplement_text"]
    result["sha256"] = digest(result["text"])
    result["supplements"] = {
        "version": 2,
        "primary_snapshot": snapshot,
        "attachments": attachments,
    }
    if any(a["status"] == "unavailable_or_unsupported" for a in attachments):
        result["supplements"]["retry_after_epoch"] = time.time() + 86400
    from scripts.primary_image_queue import build as build_image_queue
    result["primary_image_queue"] = build_image_queue(folder,result)
    atomic_json(folder / "text.json", result)
    return result

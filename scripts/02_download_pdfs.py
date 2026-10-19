from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any, Optional

import requests

from scripts.utils import (
    add_common_args,
    ensure_dir,
    load_table,
    make_run_manifest,
    parse_only_list,
    setup_logging,
    write_json,
)


def _email_for_unpaywall() -> str:
    import os

    return os.environ.get("UNPAYWALL_EMAIL", "").strip() or os.environ.get("NCBI_EMAIL", "").strip()


def _user_agent() -> str:
    email = _email_for_unpaywall()
    base = "agentic-systematic-review/0.1"
    return f"{base} (mailto:{email})" if email else base


def pmid_to_pmcid(pmid: str) -> Optional[str]:
    if not pmid:
        return None
    url = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    r = requests.get(url, params={"ids": pmid, "format": "json"}, timeout=60, headers={"User-Agent": _user_agent()})
    if r.status_code != 200:
        return None
    try:
        obj = r.json()
    except Exception:
        return None
    recs = obj.get("records") or []
    if not recs:
        return None
    pmcid = (recs[0].get("pmcid") or "").strip()
    return pmcid or None


def europe_pmc_lookup(pmid: str) -> dict[str, Any]:
    if not pmid:
        return {"status": "skipped", "reason": "missing_pmid"}
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    query = f"EXT_ID:{pmid} AND SRC:MED"
    try:
        r = requests.get(
            url,
            params={"query": query, "format": "json", "pageSize": "1"},
            timeout=60,
            headers={"User-Agent": _user_agent()},
        )
        r.raise_for_status()
        obj = r.json()
    except Exception as e:
        return {"status": "error", "error": str(e), "query": query}

    results = (((obj.get("resultList") or {}).get("result")) or [])
    if not results:
        return {"status": "not_found", "query": query}
    res = results[0] or {}

    pmcid = (res.get("pmcid") or "").strip()
    doi = (res.get("doi") or "").strip()

    ft = (res.get("fullTextUrlList") or {}).get("fullTextUrl") or []
    pdf_candidates = []
    for item in ft:
        if not isinstance(item, dict):
            continue
        u = (item.get("url") or "").strip()
        if not u:
            continue
        style = (item.get("documentStyle") or "").strip().lower()
        availability = (item.get("availability") or "").strip().lower()
        if style == "pdf" or u.lower().endswith(".pdf"):
            pdf_candidates.append({"url": u, "documentStyle": style, "availability": availability, "site": item.get("site")})

    out: dict[str, Any] = {
        "status": "ok",
        "pmcid": pmcid,
        "doi": doi,
        "hasPDF": res.get("hasPDF"),
        "hasFullText": res.get("hasFullText"),
        "isOpenAccess": res.get("isOpenAccess"),
        "pdf_candidates": pdf_candidates[:5],
    }
    if pdf_candidates:
        out["pdf_url"] = pdf_candidates[0]["url"]
    return out


def pmc_oa_links(pmcid: str) -> dict[str, Any]:
    if not pmcid:
        return {"status": "skipped", "reason": "missing_pmcid"}
    pmcid = pmcid.strip()
    if not pmcid.upper().startswith("PMC"):
        pmcid = "PMC" + pmcid
    url = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
    r = requests.get(url, params={"id": pmcid}, timeout=60, headers={"User-Agent": _user_agent()})
    if r.status_code != 200:
        return {"status": "error", "http_status": r.status_code, "text": r.text[:500]}
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(r.text)
    except Exception:
        return {"status": "error", "error": "invalid_xml"}

    links: dict[str, str] = {}
    for link in root.findall(".//link"):
        fmt = (link.attrib.get("format") or "").lower().strip()
        href = (link.attrib.get("href") or "").strip()
        if not fmt or not href:
            continue
        links[fmt] = href

    return {"status": "ok", "pmcid": pmcid, "links": links}


def _ftp_to_https(url: str) -> str:
    if url.startswith("ftp://ftp.ncbi.nlm.nih.gov/"):
        return "https://ftp.ncbi.nlm.nih.gov/" + url.removeprefix("ftp://ftp.ncbi.nlm.nih.gov/")
    return url


def try_download_pmc_oa(pmcid: str, dest_pdf: Path, *, work_dir: Path) -> tuple[bool, dict[str, Any]]:
    """Use the public 2026 PMC Cloud dataset; legacy OA/FTP retired Aug 2026."""
    from scripts.pmc_cloud import download_pdf
    ensure_dir(work_dir)
    ok, metadata = download_pdf(pmcid, dest_pdf)
    write_json(work_dir / "cloud_status.json", metadata)
    return ok, metadata


def try_download_pmc_pdf(pmcid: str, dest: Path) -> tuple[bool, dict[str, Any]]:
    if not pmcid:
        return False, {"status": "skipped", "reason": "missing_pmcid"}
    pmcid = pmcid.strip()
    if not pmcid.upper().startswith("PMC"):
        pmcid = "PMC" + pmcid

    candidates = [
        f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/",
        f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/",
    ]
    tmp = dest.with_suffix(dest.suffix + ".part")

    last_err = ""
    for url in candidates:
        try:
            with requests.get(
                url,
                headers={"User-Agent": _user_agent(), "Accept": "application/pdf"},
                stream=True,
                timeout=60,
                allow_redirects=True,
            ) as r:
                r.raise_for_status()
                final_url = r.url
                first = b""
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        first = chunk
                        break
                if not first.startswith(b"%PDF"):
                    continue
                ensure_dir(dest.parent)
                with tmp.open("wb") as f:
                    f.write(first)
                    for chunk in r.iter_content(chunk_size=1024 * 128):
                        if chunk:
                            f.write(chunk)
            tmp.replace(dest)
            return True, {"status": "ok", "final_url": final_url, "via": url}
        except Exception as e:
            last_err = str(e)
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass

    return False, {"status": "not_found", "tried": candidates, "last_error": last_err}


def pmc_pdf_urls_from_html(pmcid: str) -> tuple[list[str], dict[str, Any]]:
    if not pmcid:
        return [], {"status": "skipped", "reason": "missing_pmcid"}
    pmcid = pmcid.strip()
    if not pmcid.upper().startswith("PMC"):
        pmcid = "PMC" + pmcid
    url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent": _user_agent()})
        r.raise_for_status()
        html = r.text
    except Exception as e:
        return [], {"status": "error", "error": str(e), "url": url}

    # Common pattern: href="/articles/PMCxxxxxx/pdf/<filename>.pdf"
    matches = re.findall(r'href="([^"]+\\.pdf[^"]*)"', html, flags=re.IGNORECASE)
    urls: list[str] = []
    for href in matches:
        href = href.strip()
        if not href:
            continue
        if "pmc" not in href.lower():
            continue
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = "https://pmc.ncbi.nlm.nih.gov" + href
        if href.lower().endswith(".pdf") or ".pdf?" in href.lower():
            urls.append(href)

    # De-dupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out[:10], {"status": "ok", "url": url, "count": len(out)}


def unpaywall_pdf_url(doi: str) -> tuple[Optional[str], dict[str, Any]]:
    email = _email_for_unpaywall()
    if not doi or not email:
        return None, {"status": "skipped", "reason": "missing_doi_or_unpaywall_email"}
    url = f"https://api.unpaywall.org/v2/{doi}"
    r = requests.get(url, params={"email": email}, timeout=60, headers={"User-Agent": _user_agent()})
    if r.status_code != 200:
        return None, {"status": "error", "http_status": r.status_code, "text": r.text[:500]}
    obj = r.json()
    best = obj.get("best_oa_location") or {}
    pdf = (best.get("url_for_pdf") or "").strip()
    if pdf:
        return pdf, {"status": "ok", "url_for_pdf": pdf}
    return None, {"status": "no_pdf_url", "best_oa_location": best}


def try_download_doi_pdf(doi: str, dest: Path) -> tuple[bool, dict[str, Any]]:
    if not doi:
        return False, {"status": "skipped", "reason": "missing_doi"}
    url = f"https://doi.org/{doi}"
    tmp = dest.with_suffix(dest.suffix + ".part")
    headers = {"Accept": "application/pdf", "User-Agent": _user_agent()}
    try:
        with requests.get(url, headers=headers, stream=True, timeout=45, allow_redirects=True) as r:
            r.raise_for_status()
            final_url = r.url
            first = b""
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    first = chunk
                    break
            ct = (r.headers.get("Content-Type") or "").lower()
            if not first.startswith(b"%PDF"):
                return False, {"status": "not_pdf", "content_type": ct, "final_url": final_url}
            ensure_dir(dest.parent)
            with tmp.open("wb") as f:
                f.write(first)
                for chunk in r.iter_content(chunk_size=1024 * 128):
                    if chunk:
                        f.write(chunk)
        tmp.replace(dest)
        return True, {"status": "ok", "final_url": final_url}
    except Exception as e:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        return False, {"status": "error", "error": str(e), "url": url}

def download_file(url: str, dest: Path) -> None:
    ensure_dir(dest.parent)
    with requests.get(url, stream=True, timeout=120, headers={"User-Agent": _user_agent()}) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 128):
                if chunk:
                    f.write(chunk)


def extract_pdf_text(pdf_path: Path) -> dict[str, Any]:
    try:
        import pdfplumber

        pages = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                pages.append({"page": i, "text": (page.extract_text() or "").strip()})
                page.close()
        return {"status": "ok", "pages": pages}
    except Exception as e:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdf_path))
            pages = []
            for i, page in enumerate(reader.pages, start=1):
                pages.append({"page": i, "text": (page.extract_text() or "").strip()})
            return {"status": "ok", "pages": pages, "fallback": "pypdf"}
        except Exception as e2:
            return {"status": "error", "error": f"{e} | {e2}", "pages": []}


def main() -> None:
    parser = argparse.ArgumentParser(description="Download/ingest PDFs and extract page-indexed text JSON.")
    add_common_args(parser, table_required=True)
    parser.add_argument("--pdf-dir", type=Path, default=None, help="Local folder of PDFs (match by PMID in filename).")
    args = parser.parse_args()

    logger = setup_logging(args.verbose)
    root = Path(".").resolve()
    only = parse_only_list(args.only)

    if args.dry_run and not args.table.exists():
        logger.info("Dry run: table not found (%s); nothing to do.", args.table)
        return

    df = load_table(args.table)
    included = df[df["Include_YN"].astype(str).str.upper().str.strip().isin(["Y", "U"])].copy()
    if included.empty:
        # Early-stage convenience: fetch PDFs for likely trials even before screening.
        candidates = df.copy()
        if "ExcludedByPTFilter" in candidates.columns:
            candidates = candidates[candidates["ExcludedByPTFilter"].fillna(False) == False]  # noqa: E712
        candidates = candidates[candidates["Include_YN"].astype(str).str.upper().str.strip() != "N"]
        included = candidates
    if only:
        included = included[included["record_id"].astype(str).isin(only)]
    if args.limit and args.limit > 0:
        included = included.head(args.limit)

    raw_records_path = Path("data/raw/pubmed_records.jsonl")
    meta_by_record: dict[str, dict[str, Any]] = {}
    if raw_records_path.exists():
        with raw_records_path.open("r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                rid = str(r.get("record_id") or "")
                if rid:
                    meta_by_record[rid] = r

    pdf_out_dir = Path("data/raw/pdfs")
    text_out_dir = Path("data/intermediate/fulltext_text")
    step_dir = Path("data/intermediate/download_pdfs")
    ensure_dir(pdf_out_dir)
    ensure_dir(text_out_dir)
    ensure_dir(step_dir)

    processed = 0
    pdf_found = 0
    text_ok = 0

    for _, row in included.iterrows():
        record_id = str(row["record_id"])
        pmid = str(row["PMID"])
        per_dir = step_dir / "records" / record_id
        ensure_dir(per_dir)

        # Prefer PMID-first naming so filenames correspond to PubMed IDs.
        pdf_path = pdf_out_dir / f"{pmid}__{record_id}.pdf"
        legacy_pdf_path = pdf_out_dir / f"{record_id}__{pmid}.pdf"
        text_path = text_out_dir / f"{record_id}.json"

        # Migrate legacy filename if present.
        if legacy_pdf_path.exists() and (not pdf_path.exists() or args.overwrite):
            try:
                ensure_dir(pdf_path.parent)
                legacy_pdf_path.replace(pdf_path)
            except Exception:
                # If cross-device rename fails, fall back to copy+unlink.
                try:
                    ensure_dir(pdf_path.parent)
                    shutil.copyfile(legacy_pdf_path, pdf_path)
                    legacy_pdf_path.unlink()
                except Exception:
                    pass

        if text_path.exists() and not args.overwrite:
            logger.info("Skip (exists): %s", record_id)
            continue

        if args.dry_run:
            logger.info("Dry run: would fetch/parse PDF for %s", record_id)
            continue

        status: dict[str, Any] = {"record_id": record_id, "pmid": pmid, "pdf_status": "missing", "text_status": "missing"}
        status["pdf_exists_at_start"] = pdf_path.exists()
        meta = meta_by_record.get(record_id, {}) or {}
        doi = str(meta.get("doi") or "").strip()
        pmcid = str(meta.get("pmcid") or "").strip()

        # 3) Local ingest first
        if args.pdf_dir and args.pdf_dir.exists():
            candidates = list(args.pdf_dir.glob(f"*{pmid}*.pdf"))
            if candidates:
                ensure_dir(pdf_path.parent)
                shutil.copyfile(candidates[0], pdf_path)
                status["pdf_status"] = "local_ingest"

        # 1) PMC OA (including PMID->PMCID conversion) via oa.fcgi (pdf or tgz package)
        if not pdf_path.exists():
            pmcid_idconv = pmid_to_pmcid(pmid) or ""
            if pmcid_idconv and pmcid_idconv != pmcid:
                status["pmcid_from_idconv"] = pmcid_idconv
                pmcid = pmcid_idconv
            if pmcid:
                ok, meta_pmc = try_download_pmc_oa(pmcid, pdf_path, work_dir=per_dir / "pmc")
                status["pmc_oa"] = meta_pmc
                if ok:
                    status["pdf_status"] = "pmc_oa"
                else:
                    status["pdf_status"] = "pmc_oa_missing"

        # 2) Europe PMC (often provides PMCID/DOI + OA PDF links)
        if not pdf_path.exists():
            epmc = europe_pmc_lookup(pmid)
            status["europe_pmc"] = epmc
            epmc_pmcid = str((epmc.get("pmcid") or "")).strip()
            epmc_doi = str((epmc.get("doi") or "")).strip()
            epmc_pdf = str((epmc.get("pdf_url") or "")).strip()

            if not pmcid and epmc_pmcid:
                pmcid = epmc_pmcid
                status["pmcid_from_europepmc"] = pmcid

            if not doi and epmc_doi:
                doi = epmc_doi
                status["doi_from_europepmc"] = doi

            if epmc_pdf:
                try:
                    download_file(epmc_pdf, pdf_path)
                    status["pdf_status"] = "europepmc_pdf"
                except Exception as e:
                    status["pdf_status"] = "europepmc_failed"
                    status["pdf_error"] = str(e)

            if (not pdf_path.exists()) and pmcid:
                ok, meta_pmc = try_download_pmc_oa(pmcid, pdf_path, work_dir=per_dir / "pmc")
                status["pmc_oa"] = meta_pmc
                if ok:
                    status["pdf_status"] = "pmc_oa"

        # 3) DOI resolver (Unpaywall OA + direct DOI PDF attempt)
        if not pdf_path.exists():
            if doi:
                url, meta_u = unpaywall_pdf_url(doi)
                status["unpaywall"] = meta_u
                if url:
                    try:
                        download_file(url, pdf_path)
                        status["pdf_status"] = "unpaywall_oa_pdf"
                    except Exception as e:
                        status["pdf_status"] = "unpaywall_failed"
                        status["pdf_error"] = str(e)
                else:
                    ok, meta_doi = try_download_doi_pdf(doi, pdf_path)
                    status["doi_direct"] = meta_doi
                    if ok:
                        status["pdf_status"] = "doi_direct_pdf"
                    else:
                        status["pdf_status"] = status.get("pdf_status") or "doi_direct_failed"
            else:
                status["pdf_status"] = "missing"
                status["pdf_note"] = "No DOI available; use --pdf-dir for local ingest."

        if pdf_path.exists():
            pdf_found += 1
            if status.get("pdf_status") in (None, "", "missing"):
                status["pdf_status"] = "exists"
            extracted = extract_pdf_text(pdf_path)
            write_json(text_path, extracted, overwrite=True)
            status["text_status"] = extracted.get("status")
            if extracted.get("status") == "ok":
                text_ok += 1

        write_json(per_dir / "status.json", status, overwrite=True)
        processed += 1

    manifest = make_run_manifest("download_pdfs", vars(args), root=root)
    manifest["counts"] = {"included_processed": processed, "pdf_found": pdf_found, "text_ok": text_ok}
    write_json(step_dir / "run_manifest.json", manifest, overwrite=True)


if __name__ == "__main__":
    main()

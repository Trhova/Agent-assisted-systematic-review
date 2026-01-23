from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import requests

from scripts.utils import (
    add_common_args,
    ensure_dir,
    make_run_manifest,
    read_yaml,
    record_id_from,
    setup_logging,
    write_json,
    write_jsonl,
)


def _ncbi_params() -> dict[str, str]:
    import os

    params: dict[str, str] = {"retmode": "json"}
    api_key = os.environ.get("NCBI_API_KEY", "").strip()
    tool = os.environ.get("NCBI_TOOL", "").strip()
    email = os.environ.get("NCBI_EMAIL", "").strip()
    if api_key:
        params["api_key"] = api_key
    if tool:
        params["tool"] = tool
    if email:
        params["email"] = email
    return params


def esearch(term: str, *, retmax: int) -> dict[str, Any]:
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": term, "retmax": str(retmax), "usehistory": "y", **_ncbi_params()}
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def efetch(pmids: list[str]) -> str:
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        **{k: v for k, v in _ncbi_params().items() if k != "retmode"},
    }
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    return r.text


def main() -> None:
    parser = argparse.ArgumentParser(description="PubMed search + metadata/abstract fetch (writes raw JSON/JSONL).")
    add_common_args(parser, table_required=False)
    parser.add_argument("--retmax", type=int, default=500, help="Max PMIDs to retrieve per query (before --limit).")
    args = parser.parse_args()

    logger = setup_logging(args.verbose)
    root = Path(".").resolve()
    protocol = read_yaml(args.protocol)
    queries = read_yaml(Path("protocol/queries.yaml")).get("queries", [])

    start = protocol["timeframe"]["start_year"]
    end = protocol["timeframe"]["end_year"]
    date_filter = f"({start}:{end}[dp])"
    human_filter = "(humans[mh] NOT (animals[mh] NOT humans[mh]))"
    pubmed_cfg = protocol.get("pubmed", {}) or {}
    excluded_pt_cfg = {str(x).strip().lower() for x in (pubmed_cfg.get("exclude_publication_types") or []) if str(x).strip()}
    preferred_trial_pt_cfg = {str(x).strip().lower() for x in (pubmed_cfg.get("require_publication_types") or []) if str(x).strip()}
    rct_signal_terms = [str(x).strip().lower() for x in (pubmed_cfg.get("rct_signal_terms") or []) if str(x).strip()]

    raw_search_path = Path("data/raw/pubmed_search.json")
    raw_records_path = Path("data/raw/pubmed_records.jsonl")
    records_artifacts_dir = Path("data/intermediate/search_pubmed/records")
    manifest_path = Path("data/intermediate/search_pubmed/run_manifest.json")

    if args.dry_run:
        for q in queries:
            if q.get("enabled", True) is False:
                continue
            term = f"({q['term']}) AND {date_filter} AND {human_filter}"
            logger.info("Dry run query: %s", q.get("name", "query"))
            logger.info("  term=%s", term)
        logger.info("Dry run: would search + efetch PubMed (retmax=%d, limit=%d).", args.retmax, args.limit)
        return

    if raw_search_path.exists() and raw_records_path.exists() and not args.overwrite:
        logger.info("Raw PubMed outputs exist; skipping (use --overwrite to refresh).")
        manifest = make_run_manifest("search_pubmed", vars(args), root=root)
        manifest["skipped"] = True
        write_json(manifest_path, manifest, overwrite=True)
        return

    all_pmids: list[str] = []
    searches: list[dict[str, Any]] = []
    for q in queries:
        if q.get("enabled", True) is False:
            continue
        term = f"({q['term']}) AND {date_filter} AND {human_filter}"
        logger.info("PubMed esearch: %s", q.get("name", "query"))
        resp = esearch(term, retmax=args.retmax)
        searches.append({"name": q.get("name", ""), "kind": q.get("kind", ""), "enabled": True, "term": term, "response": resp})
        ids = resp.get("esearchresult", {}).get("idlist", []) or []
        all_pmids.extend([str(i) for i in ids])

    # Deduplicate while preserving order
    seen: set[str] = set()
    pmids: list[str] = []
    for pmid in all_pmids:
        if pmid in seen:
            continue
        seen.add(pmid)
        pmids.append(pmid)

    if args.limit and args.limit > 0:
        pmids = pmids[: args.limit]

    write_json(raw_search_path, {"queries": searches}, overwrite=True)

    logger.info("Fetching %d PubMed records (efetch XML)...", len(pmids))
    parsed_records: list[dict[str, Any]] = []
    batch = 200
    for i in range(0, len(pmids), batch):
        xml = efetch(pmids[i : i + batch])
        import xml.etree.ElementTree as ET

        root_xml = ET.fromstring(xml)
        for article in root_xml.findall(".//PubmedArticle"):
            pmid = "".join(article.findtext(".//PMID") or "").strip()
            title = "".join(article.findtext(".//ArticleTitle") or "").strip()
            abstract_parts = []
            for a in article.findall(".//Abstract/AbstractText"):
                label = (a.attrib.get("Label") or "").strip()
                t = "".join(a.itertext()).strip()
                abstract_parts.append(f"{label}: {t}".strip(": ").strip() if label else t)
            abstract = "\n".join([p for p in abstract_parts if p]).strip()

            journal = "".join(article.findtext(".//Journal/Title") or "").strip()
            year = "".join(article.findtext(".//PubDate/Year") or "").strip()
            if not year:
                medline = "".join(article.findtext(".//MedlineDate") or "").strip()
                m = re.search(r"(19|20)\\d{2}", medline)
                year = m.group(0) if m else ""

            doi = ""
            pmcid = ""
            for aid in article.findall(".//ArticleIdList/ArticleId"):
                t = (aid.attrib.get("IdType") or "").lower()
                if t == "doi":
                    doi = "".join(aid.itertext()).strip()
                if t == "pmc":
                    pmcid = "".join(aid.itertext()).strip()

            publication_types = []
            for pt in article.findall(".//PublicationTypeList/PublicationType"):
                v = "".join(pt.itertext()).strip()
                if v:
                    publication_types.append(v)

            pt_norm = {p.strip().lower() for p in publication_types if p.strip()}
            excluded_pt = excluded_pt_cfg
            preferred_trial_pt = preferred_trial_pt_cfg
            text = f"{title}\n\n{abstract}".lower()
            has_trial_language = any(w in text for w in (rct_signal_terms or ["randomized", "placebo", "trial"]))

            excluded_by_filter = False
            exclusion_reason = ""
            if pt_norm & excluded_pt:
                excluded_by_filter = True
                exclusion_reason = "Excluded by PublicationTypeList: " + "; ".join(sorted(pt_norm & excluded_pt))
            elif pt_norm & preferred_trial_pt:
                excluded_by_filter = False
            else:
                if not has_trial_language:
                    excluded_by_filter = True
                    exclusion_reason = "Not clearly a primary clinical trial (PT missing/ambiguous + no trial language)"

            record_id = record_id_from(pmid, title)
            rec = {
                "pmid": pmid,
                "year": year,
                "journal": journal,
                "title": title,
                "abstract": abstract,
                "doi": doi,
                "pmcid": pmcid,
                "publication_types": publication_types,
                "excluded_by_pt_filter": excluded_by_filter,
                "exclusion_reason_auto": exclusion_reason,
                "record_id": record_id,
            }
            parsed_records.append(rec)

            ensure_dir(records_artifacts_dir / record_id)
            write_json(records_artifacts_dir / record_id / "record.json", rec, overwrite=True)

    # Deduplicate by PMID again (defensive)
    by_pmid: dict[str, dict[str, Any]] = {}
    for r in parsed_records:
        if r["pmid"] and r["pmid"] not in by_pmid:
            by_pmid[r["pmid"]] = r
    deduped = list(by_pmid.values())

    write_jsonl(raw_records_path, deduped, overwrite=True)
    logger.info("Saved %d deduped records -> %s", len(deduped), raw_records_path)

    manifest = make_run_manifest("search_pubmed", vars(args), root=root)
    manifest["counts"] = {"pmids_total": len(pmids), "records_deduped": len(deduped)}
    write_json(manifest_path, manifest, overwrite=True)


if __name__ == "__main__":
    main()

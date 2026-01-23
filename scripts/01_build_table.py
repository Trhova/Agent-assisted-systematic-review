from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.utils import (
    add_common_args,
    ensure_dir,
    iter_jsonl,
    make_run_manifest,
    parse_only_list,
    setup_logging,
    stable_screening_columns,
    write_json,
)


def hints_from_text(text: str) -> dict[str, Any]:
    t = (text or "").lower()

    def has(*words: str) -> bool:
        return any(w in t for w in words)

    randomized = has("random", "randomised", "randomized")
    placebo = has("placebo")
    double_blind = has("double-blind", "double blind", "dbl blind")

    alive_hint = "unknown"
    if has("probiotic", "synbiotic", "live biotherapeutic", "live bacteria", "live microbe"):
        alive_hint = "true"
    if has("heat-killed", "heat killed", "pasteur", "pasteurized", "inactivated", "postbiotic"):
        alive_hint = "false"

    indication = "unknown"
    if has("type 2 diabetes", "t2d", "prediabet"):
        indication = "t2d_prediabetes"
    elif has("obesity", "overweight", "weight loss", "bmi"):
        indication = "obesity_overweight"
    elif has("nafld", "masld", "fatty liver"):
        indication = "masld_nafld"
    elif has("nash"):
        indication = "nash"

    endpoints = []
    for tag, kws in [
        ("HbA1c", ["hba1c", "glycated hemoglobin"]),
        ("fasting_glucose", ["fasting glucose", "fpg"]),
        ("HOMA-IR", ["homa-ir", "homa ir"]),
        ("weight", ["weight", "bmi", "waist"]),
        ("MRI-PDFF", ["pdff", "mri", "mr spectroscopy", "mrs"]),
        ("ALT/AST", ["alt", "ast", "alanine aminotransferase", "aspartate aminotransferase"]),
        ("microbiome", ["microbiome", "16s", "metagen", "shotgun"]),
    ]:
        if has(*kws):
            endpoints.append(tag)

    tier_suggest = "unknown"
    if any(e in endpoints for e in ["HbA1c", "fasting_glucose", "weight", "MRI-PDFF"]):
        tier_suggest = "Tier 2a"
    if has("diagnos", "incident diabetes"):
        tier_suggest = "Tier 1"

    trial_ids = sorted(set(re.findall(r"\\bNCT\\d{8}\\b", text or "")))

    return {
        "IndicationBucketHint": indication,
        "EndpointsTagged": ";".join(endpoints),
        "TierSuggestedFromAbstract": tier_suggest,
        "InterventionAliveHint": alive_hint,
        "RandomizedHint": "true" if randomized else "unknown",
        "PlaceboHint": "true" if placebo else "unknown",
        "DoubleBlindHint": "true" if double_blind else "unknown",
        "TrialRegistryIDs": ",".join(trial_ids),
        "NeedsRegistryCheck": len(trial_ids) == 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the canonical screening/extraction table from raw PubMed JSONL.")
    add_common_args(parser, table_required=False)
    args = parser.parse_args()

    logger = setup_logging(args.verbose)
    root = Path(".").resolve()
    only = parse_only_list(args.only)
    raw_records_path = Path("data/raw/pubmed_records.jsonl")
    out_parquet = Path("data/outputs/screening_table.parquet")
    out_csv = Path("data/outputs/screening_table.csv")
    manifest_path = Path("data/intermediate/build_table/run_manifest.json")

    if args.dry_run:
        logger.info("Dry run: would read %s and write %s + %s", raw_records_path, out_parquet, out_csv)
        return

    if not raw_records_path.exists():
        raise FileNotFoundError(f"Missing {raw_records_path}. Run scripts/00_search_pubmed.py first.")

    if out_parquet.exists() and out_csv.exists() and not args.overwrite and not only and not (args.limit and args.limit > 0):
        logger.info("Screening table exists; skipping (use --overwrite to rebuild).")
        manifest = make_run_manifest("build_table", vars(args), root=root)
        manifest["skipped"] = True
        write_json(manifest_path, manifest, overwrite=True)
        return

    cols = stable_screening_columns()
    records = list(iter_jsonl(raw_records_path))

    if only:
        records = [r for r in records if str(r.get("record_id")) in only]
    if args.limit and args.limit > 0:
        records = records[: args.limit]

    rows = []
    for r in records:
        text = f"{r.get('title','')}\n\n{r.get('abstract','')}".strip()
        hints = hints_from_text(text)
        publication_types = r.get("publication_types") or []
        pubtypes_str = ";".join([str(x).strip() for x in publication_types if str(x).strip()])

        rows.append(
            {
                "PMID": r.get("pmid", ""),
                "Year": r.get("year", ""),
                "Journal": r.get("journal", ""),
                "Title": r.get("title", ""),
                "IndicationBucketHint": hints["IndicationBucketHint"],
                "EndpointsTagged": hints["EndpointsTagged"],
                "TierSuggestedFromAbstract": hints["TierSuggestedFromAbstract"],
                "InterventionAliveHint": hints["InterventionAliveHint"],
                "RandomizedHint": hints["RandomizedHint"],
                "PlaceboHint": hints["PlaceboHint"],
                "DoubleBlindHint": hints["DoubleBlindHint"],
                "TrialRegistryIDs": hints["TrialRegistryIDs"],
                "NeedsRegistryCheck": hints["NeedsRegistryCheck"],
                "PublicationTypes": pubtypes_str,
                "ExcludedByPTFilter": bool(r.get("excluded_by_pt_filter", False)),
                "ExclusionReasonAuto": str(r.get("exclusion_reason_auto", "") or ""),
                "Include_YN": "",
                "Reason_Exclude": "",
                "Intervention_Class": "",
                "Intervention_Name": "",
                "Strains_or_Consortium": "",
                "Dose": "",
                "Duration_weeks": "",
                "Population_notes": "",
                "Primary_endpoint_verbatim": "",
                "Primary_endpoint_category": "",
                "Outcome_direction": "",
                "Effect_size": "",
                "Durability_timepoint": "",
                "TierFinal": "",
                "RoB2_overall": "",
                "RoB2_notes": "",
                "Multiplicity_flags": "",
                "Comments": "",
                "record_id": r.get("record_id", ""),
            }
        )

    df = pd.DataFrame(rows, columns=cols)
    df = df.sort_values(["Year", "PMID"], ascending=[False, True], kind="stable")

    ensure_dir(out_parquet.parent)
    df.to_parquet(out_parquet, index=False)
    df.to_csv(out_csv, index=False)
    logger.info("Wrote screening table -> %s and %s", out_parquet, out_csv)

    manifest = make_run_manifest("build_table", vars(args), root=root)
    manifest["counts"] = {"records": len(df)}
    write_json(manifest_path, manifest, overwrite=True)


if __name__ == "__main__":
    main()

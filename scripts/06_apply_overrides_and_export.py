from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.utils import (
    add_common_args,
    ensure_dir,
    load_table,
    make_run_manifest,
    parse_only_list,
    read_yaml,
    setup_logging,
    stable_screening_columns,
    write_json,
)


def _parse_weeks(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower()
    if not s or s == "unknown":
        return None
    m = re.search(r"(\\d+(?:\\.\\d+)?)\\s*week", s)
    if m:
        return float(m.group(1))
    m = re.search(r"^(\\d+(?:\\.\\d+)?)$", s)
    if m:
        return float(m.group(1))
    return None


def _flag_join(flags: list[str]) -> str:
    return ";".join([f for f in flags if f])


def assign_tier(row: pd.Series, protocol: dict[str, Any]) -> tuple[str, str]:
    flags: list[str] = []

    randomized = str(row.get("RandomizedHint", "")).strip().lower() == "true"
    placebo = str(row.get("PlaceboHint", "")).strip().lower() == "true"
    rob2 = str(row.get("RoB2_overall", "")).strip().lower() or "unknown"

    if not randomized:
        flags.append("not_randomized")
    if not placebo:
        flags.append("no_placebo")

    acceptable_rob2 = set(protocol["tier_rules"]["acceptable_rob2"])
    rob2_ok = rob2 in acceptable_rob2
    if not rob2_ok:
        flags.append(f"rob2_{rob2 or 'unknown'}")

    category = str(row.get("Primary_endpoint_category", "")).strip()
    outcome = str(row.get("Outcome_direction", "")).strip().lower()
    primary_met = outcome == "improved"
    if outcome in {"", "unknown"}:
        flags.append("primary_outcome_unknown")

    duration_weeks = _parse_weeks(row.get("Duration_weeks"))
    durability = _parse_weeks(row.get("Durability_timepoint")) or duration_weeks
    thresholds = protocol["durability_thresholds_weeks"]
    needs_weeks = None
    if category in {"hba1c", "fasting_glucose", "homa_ir"}:
        needs_weeks = thresholds["glycemic"]
    if category in {"weight", "bmi", "waist_circumference"}:
        needs_weeks = thresholds["weight"]
    if category in {"mri_pdff", "mrs_liver_fat"}:
        needs_weeks = thresholds["liver_fat_imaging"]
    if needs_weeks and (durability is None or durability < float(needs_weeks)):
        flags.append("durability_below_threshold")

    effect_size = str(row.get("Effect_size", "")).lower()
    if re.search(r"\\bns\\b|p\\s*>\\s*0\\.05|not significant", effect_size):
        flags.append("primary_not_significant")
        primary_met = False

    minimum_bar = randomized and placebo
    if not minimum_bar:
        return protocol["tier_rules"]["tiers"]["tier_3"], _flag_join(flags)

    if not primary_met:
        return protocol["tier_rules"]["tiers"]["tier_3"], _flag_join(flags)

    if not rob2_ok:
        return protocol["tier_rules"]["tiers"]["tier_2b"], _flag_join(flags)

    clinical_non = set(protocol["endpoint_taxonomy"]["clinical_non_surrogate"])
    validated = set(protocol["endpoint_taxonomy"]["validated_surrogate"])
    if category in clinical_non:
        return protocol["tier_rules"]["tiers"]["tier_1"], _flag_join(flags)
    if category in validated:
        return protocol["tier_rules"]["tiers"]["tier_2a"], _flag_join(flags)

    flags.append("endpoint_not_validated_surrogate")
    return protocol["tier_rules"]["tiers"]["tier_2b"], _flag_join(flags)


def apply_overrides(df: pd.DataFrame, overrides_path: Path, logger) -> int:
    if not overrides_path.exists():
        return 0
    applied = 0
    with overrides_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rid = str(obj.get("record_id") or "").strip()
            field = str(obj.get("field") or "").strip()
            new_value = obj.get("new_value")
            old_value = obj.get("old_value")
            if not rid or not field:
                continue
            if field not in df.columns:
                continue
            mask = df["record_id"].astype(str) == rid
            if not mask.any():
                continue
            if old_value is not None:
                current = df.loc[mask, field].iloc[0]
                if str(current) != str(old_value):
                    logger.warning("Override old_value mismatch for %s.%s (table=%r, override=%r)", rid, field, current, old_value)
            df.loc[mask, field] = new_value
            applied += 1
    return applied


def prisma_counts(df: pd.DataFrame) -> dict[str, Any]:
    identified = len(df)
    deduplicated = len(df)
    excluded_by_pt_filter = 0
    excluded_by_heuristic_filter = 0
    if "ExcludedByPTFilter" in df.columns:
        excluded_mask = df["ExcludedByPTFilter"].fillna(False) == True  # noqa: E712
        excluded_by_pt_filter = int(excluded_mask.sum())
        if "ExclusionReasonAuto" in df.columns:
            heur = df["ExclusionReasonAuto"].astype(str).str.startswith("Not clearly a primary clinical trial")
            excluded_by_heuristic_filter = int((excluded_mask & heur).sum())

    screened = int((df["Include_YN"].astype(str).str.strip() != "").sum())
    excluded_title_abstract = int((df["Include_YN"].astype(str).str.upper().str.strip() == "N").sum())
    included = int((df["Include_YN"].astype(str).str.upper().str.strip() == "Y").sum())

    fulltext_dir = Path("data/intermediate/fulltext_text")
    fulltext_present = set(p.stem for p in fulltext_dir.glob("*.json")) if fulltext_dir.exists() else set()
    fulltext_assessed = int(df[df["record_id"].astype(str).isin(fulltext_present)].shape[0])

    reasons = (
        df.loc[df["Include_YN"].astype(str).str.upper().str.strip() == "N", "Reason_Exclude"]
        .astype(str)
        .str.strip()
    )
    top = reasons[reasons != ""].value_counts().head(20).to_dict()

    return {
        "identified": identified,
        "deduplicated": deduplicated,
        "excluded_by_pt_filter": excluded_by_pt_filter,
        "excluded_by_heuristic_filter": excluded_by_heuristic_filter,
        "screened": screened,
        "excluded_title_abstract": excluded_title_abstract,
        "fulltext_assessed": fulltext_assessed,
        "excluded_fulltext": {"count": 0, "reasons": {}},
        "included": included,
        "top_exclusion_reasons": top,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply deterministic tiering + human overrides, then export final table + PRISMA counts.")
    add_common_args(parser, table_required=True)
    args = parser.parse_args()

    logger = setup_logging(args.verbose)
    root = Path(".").resolve()
    only = parse_only_list(args.only)

    if args.dry_run and not args.table.exists():
        logger.info("Dry run: table not found (%s); nothing to do.", args.table)
        return

    protocol = read_yaml(Path(args.protocol))
    df = load_table(args.table)
    cols = stable_screening_columns()
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]

    df_work = df[df["record_id"].astype(str).isin(only)].copy() if only else df.copy()
    if args.limit and args.limit > 0:
        df_work = df_work.head(args.limit)

    if args.dry_run:
        logger.info("Dry run: would tier/export %d records", len(df_work))
        return

    per_dir = Path("data/intermediate/export/records")
    ensure_dir(per_dir)

    for _, row in df_work.iterrows():
        rid = str(row["record_id"])
        tier, flags = assign_tier(row, protocol)
        df.loc[df["record_id"] == rid, "TierFinal"] = tier
        df.loc[df["record_id"] == rid, "Multiplicity_flags"] = flags
        write_json(per_dir / f"{rid}.json", {"record_id": rid, "TierFinal": tier, "Multiplicity_flags": flags}, overwrite=True)

    overrides_path = Path("overrides/overrides.jsonl")
    applied = apply_overrides(df, overrides_path, logger)
    logger.info("Applied %d overrides from %s", applied, overrides_path)

    outputs_dir = Path("data/outputs")
    ensure_dir(outputs_dir)
    final_parquet = outputs_dir / "final_table.parquet"
    final_csv = outputs_dir / "final_table.csv"
    df.to_parquet(final_parquet, index=False)
    df.to_csv(final_csv, index=False)

    prisma = prisma_counts(df)
    write_json(outputs_dir / "prisma_counts.json", prisma, overwrite=True)

    manifest_dir = Path("data/intermediate/export")
    ensure_dir(manifest_dir)
    manifest = make_run_manifest("apply_overrides_and_export", vars(args), root=root)
    manifest["counts"] = {"records_tiered": int(len(df_work)), "overrides_applied": applied}
    write_json(manifest_dir / "run_manifest.json", manifest, overwrite=True)


if __name__ == "__main__":
    main()

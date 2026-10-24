from __future__ import annotations

import argparse
import json
import logging
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

# Assessment states written to the derived ``AssessmentStatus`` column. They partition
# the table, so PRISMA counts derived from them always add up to ``identified``.
STATUS_EXCLUDED_PT_FILTER = "excluded_pt_filter"
STATUS_NOT_SCREENED = "not_screened"
STATUS_EXCLUDED_ABSTRACT = "excluded_abstract"
STATUS_FULLTEXT_NOT_ASSESSED = "fulltext_not_assessed"
STATUS_EXCLUDED_FULLTEXT = "excluded_fulltext"
STATUS_INCLUDED = "included"
STATUS_INCLUDED_UNCERTAIN = "included_uncertain"

ASSESSED_STATUSES = {STATUS_EXCLUDED_FULLTEXT, STATUS_INCLUDED, STATUS_INCLUDED_UNCERTAIN}
TIERED_STATUSES = {STATUS_INCLUDED, STATUS_INCLUDED_UNCERTAIN}

# Columns the export step derives itself. Overrides on these are applied after
# derivation; overrides on every other column are applied before, so they feed it.
DERIVED_COLUMNS = {"TierFinal", "MagnitudeBarPass", "MagnitudeBarNotes", "Multiplicity_flags", "AssessmentStatus"}

# Legacy spellings used by earlier extraction prompts, in addition to protocol exclusions.
_LEGACY_NONLIVING_CLASSES = {"fmt", "postbiotic", "postbiotics_or_nonliving", "nonliving_small_molecules", "diet_only"}

DEFAULT_OUTPUTS_DIR = Path("data/outputs")
DEFAULT_WORK_DIR = Path("data/intermediate/export")
DEFAULT_OVERRIDES = Path("overrides/overrides.jsonl")
DEFAULT_FULLTEXT_DIR = Path("data/intermediate/fulltext_text")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def _parse_weeks(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        return float(value)
    s = str(value).strip().lower()
    if not s or s == "unknown":
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:week|wk)", s)
    if m:
        return float(m.group(1))
    m = re.search(r"^(\d+(?:\.\d+)?)$", s)
    if m:
        return float(m.group(1))
    return None


def _flag_join(flags: list[str]) -> str:
    return ";".join([f for f in flags if f])


def _is_true_hint(value: Any) -> bool:
    return _text(value).lower() == "true"


def _is_false_hint(value: Any) -> bool:
    return _text(value).lower() == "false"


def _normalize_rob2(value: Any) -> str:
    s = _text(value).lower()
    if s in {"low", "some_concerns", "high"}:
        return s
    # Back-compat: some scripts store "Low"/"Some concerns"/"High"
    if s in {"some concerns"}:
        return "some_concerns"
    return s or "unknown"


def _excluded_intervention_classes(protocol: dict[str, Any]) -> set[str]:
    return {str(x).strip().lower() for x in (protocol.get("exclusions") or [])} | _LEGACY_NONLIVING_CLASSES


def _intervention_alive_ok(row: pd.Series, protocol: dict[str, Any] | None = None) -> bool:
    if _is_false_hint(row.get("InterventionAliveHint")):
        return False
    cls = _text(row.get("Intervention_Class")).lower()
    excluded = _excluded_intervention_classes(protocol or {})
    if cls in excluded:
        return False
    return True


def include_decision(row: pd.Series) -> str:
    """Screening decision as recorded in ``Include_YN``: ``Y``, ``N``, ``U`` or ``''`` (not screened)."""
    return _text(row.get("Include_YN")).upper()


def has_fulltext_extraction(row: pd.Series) -> bool:
    """True when full-text extraction (script 04) has written a decision for this row.

    ``Outcome_direction`` is a required literal in the extraction schema and is written
    unconditionally by script 04 (``unknown`` at worst), so it is the marker for a
    completed full-text assessment. Design hints alone come from the abstract stage.
    """
    return _text(row.get("Outcome_direction")) != ""


def fulltext_exclusion(row: pd.Series, protocol: dict[str, Any]) -> tuple[str, str] | None:
    """Deterministic full-text exclusion per protocol exclusions and the minimum design bar.

    Only *explicit* evidence excludes; ``unknown`` hints never do (they lower the tier instead).
    Returns (Reason_Exclude_Category, Reason_Exclude) or None when the record stays in.
    """
    cls = _text(row.get("Intervention_Class")).lower()
    if cls and cls in _excluded_intervention_classes(protocol):
        return "Intervention not live microbiome", f"Intervention not live microbiome: Intervention_Class={cls}"
    if _is_false_hint(row.get("InterventionAliveHint")):
        return "Intervention not live microbiome", "Intervention not live microbiome: InterventionAliveHint=false"
    if _is_false_hint(row.get("RandomizedHint")):
        return "Not RCT", "Not RCT: RandomizedHint=false"
    if _is_false_hint(row.get("PlaceboHint")):
        return "No placebo control", "No placebo control: PlaceboHint=false"
    return None


def assessment_status(row: pd.Series, protocol: dict[str, Any]) -> str:
    """Classify where a record stands in the review flow, from its decision columns only."""
    decision = include_decision(row)
    if decision == "":
        pt_excluded = row.get("ExcludedByPTFilter")
        if pt_excluded is True or _text(pt_excluded).lower() == "true":
            return STATUS_EXCLUDED_PT_FILTER
        return STATUS_NOT_SCREENED
    if decision == "N":
        # Script 04 only extracts Y/U records, so an N with extraction data is a
        # full-text exclusion (from this step or a human override), not an abstract one.
        return STATUS_EXCLUDED_FULLTEXT if has_fulltext_extraction(row) else STATUS_EXCLUDED_ABSTRACT
    if decision not in {"Y", "U"}:
        return STATUS_NOT_SCREENED
    if not has_fulltext_extraction(row):
        return STATUS_FULLTEXT_NOT_ASSESSED
    if fulltext_exclusion(row, protocol) is not None:
        return STATUS_EXCLUDED_FULLTEXT
    return STATUS_INCLUDED if decision == "Y" else STATUS_INCLUDED_UNCERTAIN


def _primary_outcome_met(row: pd.Series) -> tuple[bool, list[str]]:
    flags: list[str] = []
    outcome = _text(row.get("Outcome_direction")).lower()
    effect_size = _text(row.get("Effect_size")).lower()
    if outcome in {"", "unknown"}:
        flags.append("primary_outcome_unknown")
        return False, flags
    if outcome != "improved":
        flags.append(f"primary_outcome_{outcome}")
        return False, flags
    if re.search(r"\bns\b|p\s*>\s*0\.05|not significant|non-significant", effect_size):
        flags.append("primary_not_significant")
        return False, flags
    return True, flags


def _durability_ok(row: pd.Series, protocol: dict[str, Any]) -> tuple[bool, list[str]]:
    flags: list[str] = []
    category = _text(row.get("Primary_endpoint_category"))
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
        return False, flags
    return True, flags


def _has_multiplicity_concerns(row: pd.Series) -> list[str]:
    flags: list[str] = []
    txt = f"{_text(row.get('Primary_endpoint_verbatim'))}\n{_text(row.get('Effect_size'))}\n{_text(row.get('Population_notes'))}".lower()
    if "post hoc" in txt or "post-hoc" in txt:
        flags.append("post_hoc")
    if "secondary endpoint" in txt or "secondary outcome" in txt:
        flags.append("secondary_only")
    if "multiple comparisons" in txt or "multiple testing" in txt:
        flags.append("multiple_testing")
    if "exploratory" in txt:
        flags.append("exploratory")
    return flags


def _magnitude_bar(row: pd.Series, protocol: dict[str, Any]) -> tuple[str, str]:
    """
    Separate classification layer (not part of TierFinal assignment).
    Returns (MagnitudeBarPass, MagnitudeBarNotes) where pass is Y/N/U.
    """
    tier = _text(row.get("TierFinal"))
    if tier not in {protocol["tier_rules"]["tiers"]["tier_1"], protocol["tier_rules"]["tiers"]["tier_2a"]}:
        return "", ""

    category = _text(row.get("Primary_endpoint_category")).lower()
    effect = _text(row.get("Effect_size"))
    if not effect:
        return "U", "insufficient data (Effect_size empty)"

    thresholds = protocol.get("magnitude_thresholds", {}) or {}

    if category == "hba1c":
        m = re.search(r"(-?\d+(?:\.\d+)?)", effect)
        if not m:
            return "U", "insufficient data (no numeric HbA1c delta found)"
        delta = abs(float(m.group(1)))
        need = float(thresholds.get("hba1c_absolute_vs_placebo_min", 0.3))
        return ("Y" if delta >= need else "N"), f"parsed_abs_delta={delta}; threshold={need}"

    if category in {"weight", "bmi", "waist_circumference"}:
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", effect)
        if not m:
            return "U", "insufficient data (no % change found)"
        pct = float(m.group(1))
        need = float(thresholds.get("weight_percent_vs_placebo_min", 3.0))
        strong = float(thresholds.get("weight_percent_vs_placebo_strong", 5.0))
        passed = "Y" if pct >= need else "N"
        strength = "strong" if pct >= strong else "minimal" if pct >= need else "below"
        return passed, f"parsed_pct={pct}; threshold={need}; strength={strength}"

    if category in {"alt_ast"}:
        return "N", "ALT/AST are weak surrogates; never count as strong magnitude"

    return "U", f"no magnitude rule implemented for category={category}"


def assign_tier(row: pd.Series, protocol: dict[str, Any]) -> tuple[str, str]:
    """Deterministic evidence tier for a record that has been screened in and assessed at full text.

    Records without a screening decision or without full-text extraction are *not*
    tiered: they return an empty tier so that "not assessed" is never reported as
    "Tier 3" (which means assessed and failing the efficacy bar).
    """
    if include_decision(row) not in {"Y", "U"} or not has_fulltext_extraction(row):
        return "", ""

    flags: list[str] = []

    randomized = _is_true_hint(row.get("RandomizedHint"))
    placebo = _is_true_hint(row.get("PlaceboHint"))
    rob2 = _normalize_rob2(row.get("RoB2_overall"))

    if not randomized:
        flags.append("not_randomized_or_unknown")
    if not placebo:
        flags.append("no_placebo_or_unknown")

    acceptable_rob2 = set(protocol["tier_rules"]["acceptable_rob2"])
    rob2_ok = rob2 in acceptable_rob2
    if not rob2_ok:
        flags.append(f"rob2_{rob2 or 'unknown'}")

    if not _intervention_alive_ok(row, protocol):
        flags.append("not_alive_intervention")
        return protocol["tier_rules"]["tiers"]["tier_3"], _flag_join(flags)

    primary_met, primary_flags = _primary_outcome_met(row)
    flags.extend(primary_flags)

    durability_ok, dur_flags = _durability_ok(row, protocol)
    flags.extend(dur_flags)

    mult_flags = _has_multiplicity_concerns(row)
    flags.extend(mult_flags)

    minimum_bar = randomized and placebo
    if not minimum_bar:
        return protocol["tier_rules"]["tiers"]["tier_3"], _flag_join(flags)

    if not primary_met:
        return protocol["tier_rules"]["tiers"]["tier_3"], _flag_join(flags)

    # If effect is present but follow-up is short, treat as fragile signal.
    if not durability_ok:
        return protocol["tier_rules"]["tiers"]["tier_2b"], _flag_join(flags)

    if not rob2_ok:
        return protocol["tier_rules"]["tiers"]["tier_2b"], _flag_join(flags)

    category = _text(row.get("Primary_endpoint_category"))
    clinical_non = set(protocol["endpoint_taxonomy"]["clinical_non_surrogate"])
    validated = set(protocol["endpoint_taxonomy"]["validated_surrogate"])
    if category in clinical_non:
        return protocol["tier_rules"]["tiers"]["tier_1"], _flag_join(flags)
    if category in validated:
        return protocol["tier_rules"]["tiers"]["tier_2a"], _flag_join(flags)

    flags.append("endpoint_not_validated_surrogate")
    return protocol["tier_rules"]["tiers"]["tier_2b"], _flag_join(flags)


def derive_record(row: pd.Series, protocol: dict[str, Any]) -> dict[str, Any]:
    """Derive inclusion, assessment status, tier and magnitude bar for one row.

    Only ``Include_YN``/``Reason_Exclude*`` of records excluded at full text are
    changed; abstract-stage decisions and un-screened records are left as they are.
    """
    out: dict[str, Any] = {
        "Include_YN": include_decision(row),
        "Reason_Exclude": _text(row.get("Reason_Exclude")),
        "Reason_Exclude_Category": _text(row.get("Reason_Exclude_Category")),
        "TierFinal": "",
        "Multiplicity_flags": "",
        "MagnitudeBarPass": "",
        "MagnitudeBarNotes": "",
    }
    status = assessment_status(row, protocol)
    out["AssessmentStatus"] = status

    if status == STATUS_EXCLUDED_FULLTEXT:
        exclusion = fulltext_exclusion(row, protocol)
        if exclusion is not None:
            out["Include_YN"] = "N"
            out["Reason_Exclude_Category"], out["Reason_Exclude"] = exclusion
        return out

    if status in TIERED_STATUSES:
        tier, flags = assign_tier(row, protocol)
        out["TierFinal"] = tier
        out["Multiplicity_flags"] = flags
        tiered = row.copy()
        tiered["TierFinal"] = tier
        out["MagnitudeBarPass"], out["MagnitudeBarNotes"] = _magnitude_bar(tiered, protocol)
    return out


def apply_overrides(
    df: pd.DataFrame,
    overrides_path: Path,
    logger: logging.Logger,
    *,
    fields: set[str] | None = None,
    skip_fields: set[str] | None = None,
) -> int:
    """Apply ``overrides.jsonl`` rows to ``df`` in place. Returns the number applied.

    ``fields`` restricts application to those columns; ``skip_fields`` excludes columns.
    """
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
            if fields is not None and field not in fields:
                continue
            if skip_fields is not None and field in skip_fields:
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


def _fulltext_record_ids(fulltext_dir: Path) -> set[str]:
    if not fulltext_dir.exists():
        return set()
    return {p.stem for p in fulltext_dir.glob("*.json")}


def prisma_counts(df: pd.DataFrame, *, fulltext_dir: Path = DEFAULT_FULLTEXT_DIR) -> dict[str, Any]:
    """PRISMA-style counts derived from ``AssessmentStatus`` (a partition of the table).

    ``fulltext_retrieved`` counts records whose full text was downloaded and parsed;
    ``fulltext_assessed`` counts records with a full-text extraction decision. The two
    differ whenever script 04 has not been run on retrieved texts.
    """
    if "AssessmentStatus" not in df.columns:
        raise ValueError("prisma_counts requires the derived AssessmentStatus column; run derive_record first")
    status = df["AssessmentStatus"].astype(str).str.strip()
    counts = status.value_counts().to_dict()

    def n(key: str) -> int:
        return int(counts.get(key, 0))

    identified = int(len(df))
    excluded_by_pt_filter = n(STATUS_EXCLUDED_PT_FILTER)
    excluded_by_heuristic_filter = 0
    if "ExclusionReasonAuto" in df.columns:
        heur = df["ExclusionReasonAuto"].astype(str).str.startswith("Not clearly a primary clinical trial")
        excluded_by_heuristic_filter = int(((status == STATUS_EXCLUDED_PT_FILTER) & heur).sum())

    not_screened = n(STATUS_NOT_SCREENED)
    excluded_title_abstract = n(STATUS_EXCLUDED_ABSTRACT)
    fulltext_not_assessed = n(STATUS_FULLTEXT_NOT_ASSESSED)
    excluded_fulltext = n(STATUS_EXCLUDED_FULLTEXT)
    included = n(STATUS_INCLUDED)
    included_uncertain = n(STATUS_INCLUDED_UNCERTAIN)
    screened = identified - excluded_by_pt_filter - not_screened
    fulltext_assessed = excluded_fulltext + included + included_uncertain

    fulltext_present = _fulltext_record_ids(fulltext_dir)
    fulltext_retrieved = int(df["record_id"].astype(str).isin(fulltext_present).sum())

    ft_mask = status == STATUS_EXCLUDED_FULLTEXT
    ft_reasons = df.loc[ft_mask, "Reason_Exclude_Category"].astype(str).str.strip()
    ft_reasons = ft_reasons.where(ft_reasons != "", "unspecified")
    excluded_fulltext_reasons = {str(k): int(v) for k, v in ft_reasons.value_counts().to_dict().items()}

    abs_mask = status == STATUS_EXCLUDED_ABSTRACT
    reasons = df.loc[abs_mask, "Reason_Exclude"].astype(str).str.strip()
    top = {str(k): int(v) for k, v in reasons[reasons != ""].value_counts().head(20).to_dict().items()}

    tier_mask = status.isin(TIERED_STATUSES)
    tiers = df.loc[tier_mask, "TierFinal"].astype(str).str.strip()
    tiers = tiers.where(tiers != "", "untiered")
    tier_counts = {str(k): int(v) for k, v in tiers.value_counts().sort_index().to_dict().items()}

    warnings: list[str] = []
    if not_screened:
        warnings.append(f"{not_screened} records have no abstract screening decision (scripts/03_screen_abstracts_llm.py has not been run on them)")
    if fulltext_not_assessed:
        warnings.append(f"{fulltext_not_assessed} screened-in records have no full-text extraction decision (scripts/04_extract_fulltext_llm.py has not been run on them)")
    if fulltext_retrieved and fulltext_assessed == 0:
        warnings.append(f"{fulltext_retrieved} full texts were retrieved but none has been assessed")
    if included_uncertain:
        warnings.append(f"{included_uncertain} records carry an uncertain (U) decision and need a human override")

    assessment_complete = not_screened == 0 and fulltext_not_assessed == 0 and included_uncertain == 0
    partition_total = (
        excluded_by_pt_filter + not_screened + excluded_title_abstract + fulltext_not_assessed
        + excluded_fulltext + included + included_uncertain
    )
    assert partition_total == identified, "AssessmentStatus must partition the table"

    return {
        "identified": identified,
        "deduplicated": identified,
        "excluded_by_pt_filter": excluded_by_pt_filter,
        "excluded_by_heuristic_filter": excluded_by_heuristic_filter,
        "not_screened": not_screened,
        "screened": screened,
        "excluded_title_abstract": excluded_title_abstract,
        "fulltext_retrieved": fulltext_retrieved,
        "fulltext_not_assessed": fulltext_not_assessed,
        "fulltext_assessed": fulltext_assessed,
        "excluded_fulltext": {"count": excluded_fulltext, "reasons": excluded_fulltext_reasons},
        "included": included,
        "included_uncertain": included_uncertain,
        "tiers_included": tier_counts,
        "top_exclusion_reasons": top,
        "assessment_complete": assessment_complete,
        "warnings": warnings,
    }


def _ensure_stable_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = stable_screening_columns()
    for c in cols:
        if c not in df.columns:
            df[c] = "" if c not in {"NeedsFullTextReview"} else False
    return df[cols]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply deterministic inclusion/tiering + human overrides, then export final table + PRISMA counts."
    )
    add_common_args(parser, table_required=True)
    parser.add_argument("--outputs-dir", type=Path, default=DEFAULT_OUTPUTS_DIR, help="Directory for final_table.* and prisma_counts.json")
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR, help="Directory for per-record derivations and the run manifest")
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES, help="Path to overrides.jsonl")
    parser.add_argument("--fulltext-dir", type=Path, default=DEFAULT_FULLTEXT_DIR, help="Directory of parsed full texts ({record_id}.json), read only for PRISMA counts")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logger = setup_logging(args.verbose)
    root = Path(".").resolve()
    only = parse_only_list(args.only)

    if args.dry_run and not args.table.exists():
        logger.info("Dry run: table not found (%s); nothing to do.", args.table)
        return

    protocol = read_yaml(Path(args.protocol))
    df = _ensure_stable_columns(load_table(args.table))

    df_work = df[df["record_id"].astype(str).isin(only)].copy() if only else df.copy()
    if args.limit and args.limit > 0:
        df_work = df_work.head(args.limit)

    if args.dry_run:
        logger.info("Dry run: would derive/export %d records", len(df_work))
        return

    # Human corrections to input columns feed the derivation; corrections to derived
    # columns are applied afterwards so they are the final word.
    applied = apply_overrides(df, args.overrides, logger, skip_fields=DERIVED_COLUMNS)

    per_dir = args.work_dir / "records"
    ensure_dir(per_dir)

    work_ids = set(df_work["record_id"].astype(str))
    for idx in df.index[df["record_id"].astype(str).isin(work_ids)]:
        row = df.loc[idx]
        rid = str(row["record_id"])
        derived = derive_record(row, protocol)
        for field, value in derived.items():
            df.at[idx, field] = value
        write_json(per_dir / f"{rid}.json", {"record_id": rid, **derived}, overwrite=True)

    applied += apply_overrides(df, args.overrides, logger, fields=DERIVED_COLUMNS)
    logger.info("Applied %d overrides from %s", applied, args.overrides)

    ensure_dir(args.outputs_dir)
    df.to_parquet(args.outputs_dir / "final_table.parquet", index=False)
    df.to_csv(args.outputs_dir / "final_table.csv", index=False)

    prisma = prisma_counts(df, fulltext_dir=args.fulltext_dir)
    write_json(args.outputs_dir / "prisma_counts.json", prisma, overwrite=True)
    logger.info(
        "PRISMA: identified=%d not_screened=%d excluded_abstract=%d fulltext_assessed=%d excluded_fulltext=%d included=%d included_uncertain=%d",
        prisma["identified"], prisma["not_screened"], prisma["excluded_title_abstract"], prisma["fulltext_assessed"],
        prisma["excluded_fulltext"]["count"], prisma["included"], prisma["included_uncertain"],
    )
    for w in prisma["warnings"]:
        logger.warning("Assessment incomplete: %s", w)

    ensure_dir(args.work_dir)
    manifest = make_run_manifest("apply_overrides_and_export", vars(args), root=root)
    manifest["counts"] = {
        "records_derived": int(len(df_work)),
        "overrides_applied": applied,
        "assessment_status": {str(k): int(v) for k, v in df["AssessmentStatus"].astype(str).value_counts().to_dict().items()},
    }
    write_json(args.work_dir / "run_manifest.json", manifest, overwrite=True)


if __name__ == "__main__":
    main()

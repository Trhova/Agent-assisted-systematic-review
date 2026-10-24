"""Regression tests for scripts/06_apply_overrides_and_export.py.

Background (docs/final_table_inclusion_fix_2026-10-24.md): the export step used to tier
every record, so rows that had never been screened or extracted came out as "Tier 3"
with an empty Include_YN, indistinguishable from assessed studies that failed the
efficacy bar. These tests pin the honest behaviour and the deterministic inclusion.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.utils import read_yaml, stable_screening_columns

exp = importlib.import_module("scripts.06_apply_overrides_and_export")

REPO = Path(__file__).resolve().parents[1]
PROTOCOL = read_yaml(REPO / "protocol" / "protocol.yaml")


def _row(**over: object) -> pd.Series:
    base = {c: "" for c in stable_screening_columns()}
    base["NeedsFullTextReview"] = False
    base["ExcludedByPTFilter"] = False
    base["RandomizedHint"] = "true"
    base["PlaceboHint"] = "true"
    base["InterventionAliveHint"] = "true"
    base["record_id"] = "rid"
    base.update(over)
    return pd.Series(base)


def _extracted(**over: object) -> dict[str, object]:
    """Columns written by scripts/04 for a clean positive HbA1c trial."""
    fields: dict[str, object] = {
        "Include_YN": "Y",
        "Intervention_Class": "probiotics",
        "Duration_weeks": "12",
        "Primary_endpoint_category": "hba1c",
        "Outcome_direction": "improved",
        "Effect_size": "-0.5% vs placebo, p=0.01",
        "RoB2_overall": "Low",
    }
    fields.update(over)
    return fields


# --- regression: unassessed rows must not be tiered -----------------------------------


def test_unscreened_row_is_not_tier_3():
    # Exactly the state of every row in the January 2026 screening table.
    row = _row(TierSuggestedFromAbstract="Tier 2a")
    tier, flags = exp.assign_tier(row, PROTOCOL)
    assert tier == ""
    assert flags == ""
    assert exp.assessment_status(row, PROTOCOL) == exp.STATUS_NOT_SCREENED


def test_screened_in_without_extraction_is_fulltext_not_assessed():
    row = _row(Include_YN="Y")
    assert exp.assign_tier(row, PROTOCOL) == ("", "")
    derived = exp.derive_record(row, PROTOCOL)
    assert derived["AssessmentStatus"] == exp.STATUS_FULLTEXT_NOT_ASSESSED
    assert derived["TierFinal"] == ""
    assert derived["Include_YN"] == "Y"


def test_parse_weeks_reads_text_durations():
    # The old regexes were double-escaped inside raw strings and never matched.
    assert exp._parse_weeks("12 weeks") == 12.0
    assert exp._parse_weeks("12") == 12.0
    assert exp._parse_weeks("8.5 wk") == 8.5
    assert exp._parse_weeks(12) == 12.0
    assert exp._parse_weeks("unknown") is None


# --- deterministic inclusion and tiering on assessed rows ------------------------------


def test_assessed_positive_trial_is_included_tier_2a_with_magnitude():
    derived = exp.derive_record(_row(**_extracted()), PROTOCOL)
    assert derived["AssessmentStatus"] == exp.STATUS_INCLUDED
    assert derived["Include_YN"] == "Y"
    assert derived["TierFinal"] == "Tier 2a"
    assert derived["Multiplicity_flags"] == ""
    assert derived["MagnitudeBarPass"] == "Y"


def test_clinical_endpoint_is_tier_1_and_short_followup_is_tier_2b():
    tier_1 = exp.derive_record(_row(**_extracted(Primary_endpoint_category="incident_t2d")), PROTOCOL)
    assert tier_1["TierFinal"] == "Tier 1"
    short = exp.derive_record(_row(**_extracted(Duration_weeks="8 weeks")), PROTOCOL)
    assert short["TierFinal"] == "Tier 2b"
    assert "durability_below_threshold" in short["Multiplicity_flags"]


def test_assessed_failed_primary_is_included_tier_3():
    derived = exp.derive_record(_row(**_extracted(Outcome_direction="no_effect")), PROTOCOL)
    assert derived["AssessmentStatus"] == exp.STATUS_INCLUDED
    assert derived["TierFinal"] == "Tier 3"
    assert "primary_outcome_no_effect" in derived["Multiplicity_flags"]


def test_protocol_exclusion_at_fulltext_sets_include_n_with_reason():
    derived = exp.derive_record(_row(**_extracted(Intervention_Class="fmt")), PROTOCOL)
    assert derived["AssessmentStatus"] == exp.STATUS_EXCLUDED_FULLTEXT
    assert derived["Include_YN"] == "N"
    assert derived["Reason_Exclude_Category"] == "Intervention not live microbiome"
    assert derived["TierFinal"] == ""
    # Re-deriving from the exported row is stable (idempotent export).
    exported = _extracted(Intervention_Class="fmt")
    exported.update({k: derived[k] for k in ("Include_YN", "Reason_Exclude", "Reason_Exclude_Category")})
    again = exp.derive_record(_row(**exported), PROTOCOL)
    assert again["AssessmentStatus"] == exp.STATUS_EXCLUDED_FULLTEXT


def test_unknown_design_hints_lower_tier_but_do_not_exclude():
    derived = exp.derive_record(_row(**_extracted(PlaceboHint="unknown")), PROTOCOL)
    assert derived["AssessmentStatus"] == exp.STATUS_INCLUDED
    assert derived["TierFinal"] == "Tier 3"
    assert "no_placebo_or_unknown" in derived["Multiplicity_flags"]


def test_uncertain_decision_is_carried_forward_not_upgraded():
    derived = exp.derive_record(_row(**_extracted(Include_YN="U")), PROTOCOL)
    assert derived["AssessmentStatus"] == exp.STATUS_INCLUDED_UNCERTAIN
    assert derived["Include_YN"] == "U"
    assert derived["TierFinal"] == "Tier 2a"


def test_abstract_exclusion_keeps_reason():
    derived = exp.derive_record(_row(Include_YN="N", Reason_Exclude="Not RCT: cohort", Reason_Exclude_Category="Not RCT"), PROTOCOL)
    assert derived["AssessmentStatus"] == exp.STATUS_EXCLUDED_ABSTRACT
    assert derived["Reason_Exclude"] == "Not RCT: cohort"


# --- end-to-end export into a scratch directory ----------------------------------------


def _table() -> pd.DataFrame:
    rows = [
        _row(record_id="r_unscreened"),
        _row(record_id="r_ptfilter", ExcludedByPTFilter=True, ExclusionReasonAuto="Not clearly a primary clinical trial"),
        _row(record_id="r_abs_n", Include_YN="N", Reason_Exclude="Not RCT: review", Reason_Exclude_Category="Not RCT"),
        _row(record_id="r_y_noft", Include_YN="Y"),
        _row(record_id="r_inc", **_extracted()),
        _row(record_id="r_inc_t3", **_extracted(Outcome_direction="no_effect")),
        _row(record_id="r_fmt", **_extracted(Intervention_Class="fmt")),
        _row(record_id="r_unc", **_extracted(Include_YN="U")),
    ]
    return pd.DataFrame(rows)[stable_screening_columns()]


def test_export_end_to_end_writes_consistent_prisma_counts(tmp_path: Path):
    table = tmp_path / "screening_table.parquet"
    _table().to_parquet(table, index=False)
    fulltext_dir = tmp_path / "fulltext_text"
    fulltext_dir.mkdir()
    for rid in ("r_y_noft", "r_inc", "r_inc_t3", "r_fmt", "r_unc"):
        (fulltext_dir / f"{rid}.json").write_text("{}", encoding="utf-8")
    overrides = tmp_path / "overrides.jsonl"
    overrides.write_text(
        json.dumps({"record_id": "r_unc", "field": "Include_YN", "old_value": "U", "new_value": "Y", "reviewer": "t"}) + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "outputs"
    work_dir = tmp_path / "work"

    exp.main([
        "--protocol", str(REPO / "protocol" / "protocol.yaml"),
        "--table", str(table),
        "--outputs-dir", str(out_dir),
        "--work-dir", str(work_dir),
        "--overrides", str(overrides),
        "--fulltext-dir", str(fulltext_dir),
    ])

    final = pd.read_parquet(out_dir / "final_table.parquet").set_index("record_id")
    assert list(final.reset_index()[stable_screening_columns()].columns) == stable_screening_columns()
    assert final.loc["r_unscreened", "TierFinal"] == ""
    assert final.loc["r_unscreened", "AssessmentStatus"] == exp.STATUS_NOT_SCREENED
    assert final.loc["r_ptfilter", "AssessmentStatus"] == exp.STATUS_EXCLUDED_PT_FILTER
    assert final.loc["r_y_noft", "AssessmentStatus"] == exp.STATUS_FULLTEXT_NOT_ASSESSED
    assert final.loc["r_inc", "TierFinal"] == "Tier 2a"
    assert final.loc["r_inc_t3", "TierFinal"] == "Tier 3"
    assert final.loc["r_fmt", "Include_YN"] == "N"
    # The human override on Include_YN was applied before derivation.
    assert final.loc["r_unc", "Include_YN"] == "Y"
    assert final.loc["r_unc", "AssessmentStatus"] == exp.STATUS_INCLUDED

    prisma = json.loads((out_dir / "prisma_counts.json").read_text(encoding="utf-8"))
    assert prisma["identified"] == 8
    assert prisma["excluded_by_pt_filter"] == 1
    assert prisma["excluded_by_heuristic_filter"] == 1
    assert prisma["not_screened"] == 1
    assert prisma["screened"] == 6
    assert prisma["excluded_title_abstract"] == 1
    assert prisma["fulltext_retrieved"] == 5
    assert prisma["fulltext_not_assessed"] == 1
    assert prisma["fulltext_assessed"] == 4
    assert prisma["excluded_fulltext"] == {"count": 1, "reasons": {"Intervention not live microbiome": 1}}
    assert prisma["included"] == 3
    assert prisma["included_uncertain"] == 0
    assert prisma["tiers_included"] == {"Tier 2a": 2, "Tier 3": 1}
    assert prisma["assessment_complete"] is False
    assert (
        prisma["excluded_by_pt_filter"] + prisma["not_screened"] + prisma["excluded_title_abstract"]
        + prisma["fulltext_not_assessed"] + prisma["excluded_fulltext"]["count"] + prisma["included"]
        + prisma["included_uncertain"]
    ) == prisma["identified"]
    assert (work_dir / "records" / "r_inc.json").exists()
    manifest = json.loads((work_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["overrides_applied"] == 1


@pytest.mark.skipif(not (REPO / "data" / "outputs" / "screening_table.parquet").exists(), reason="project screening table not present")
def test_project_table_without_llm_steps_is_reported_as_not_screened():
    df = pd.read_parquet(REPO / "data" / "outputs" / "screening_table.parquet")
    df = exp._ensure_stable_columns(df)
    derived = pd.DataFrame([exp.derive_record(df.loc[i], PROTOCOL) for i in df.index], index=df.index)
    for col in derived.columns:
        df[col] = derived[col]
    prisma = exp.prisma_counts(df, fulltext_dir=REPO / "data" / "intermediate" / "fulltext_text")
    if prisma["not_screened"] == prisma["identified"]:
        # State as of 2026-10-24: scripts 03-05 never ran on this table.
        assert (df["TierFinal"] == "").all()
        assert prisma["included"] == 0 and prisma["fulltext_assessed"] == 0
        assert prisma["assessment_complete"] is False
        assert any("abstract screening" in w for w in prisma["warnings"])

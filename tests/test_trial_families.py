import pytest
from itertools import permutations

from scripts.trial_families import resolve, shared_control_guard


def row(rid, study="NCT00123456", mean=1):
    return {
        "record_id": rid,
        "study_id": study,
        "mean_treatment": mean,
        "outcome": "ALT",
    }


def test_registry_alias_dedup_preserves_source_reports():
    result = resolve([row("a"), row("b", "nct 00123456")])
    assert len(result["rows"]) == 1
    assert result["rows"][0]["duplicate_report_ids"] == ["a", "b"]


def test_discordant_and_shared_control_rows_not_chosen_to_match_target():
    result = resolve([row("a"), row("b", mean=2)])
    assert not result["rows"] and result["unresolved"]
    with pytest.raises(ValueError, match="Shared control"):
        shared_control_guard(
            [
                {"study_id": "trial", "control_arm_id": "C"},
                {"study_id": "trial", "control_arm_id": "C"},
            ]
        )


def test_unverified_link_rejected():
    with pytest.raises(ValueError, match="Unverified"):
        resolve(
            [row("a", "A"), row("b", "B")],
            [{"report_a": "a", "report_b": "b", "relationship": "same_trial"}],
        )


def test_transitive_distinctness_conflict_rejected_in_every_link_order():
    """Pair adjudications may conflict only after transitive family closure."""
    def link(a, b, relationship):
        return {
            "report_a": a, "report_b": b, "relationship": relationship,
            "evidence_a": "Verified primary statement A",
            "evidence_b": "Verified primary statement B",
            "independently_verified": True,
        }

    links = [link("a", "c", "distinct_trials"),
             link("a", "b", "same_trial"), link("b", "c", "same_trial")]
    for ordered in permutations(links):
        result = resolve([row(r, r) for r in "abc"], iter(ordered))
        assert not result["rows"]
        assert any("conflicts" in x["reason"] for x in result["unresolved"])


def test_source_supported_subgroup_is_not_an_independent_effect():
    # Scientific shape exposed by Ublosakka-Jones 2018/2019: one trial's
    # complete cohort and exercise-tested subgroup have different estimates.
    result = resolve([
        row("complete_report", "NCT02752217", mean=60),
        row("subgroup_report", "NCT 02752217", mean=63),
        row("independent_trial", "NCT02200926", mean=56),
    ])
    assert [r["record_id"] for r in result["rows"]] == ["independent_trial"]
    assert result["unresolved"][0]["reports"] == ["complete_report", "subgroup_report"]

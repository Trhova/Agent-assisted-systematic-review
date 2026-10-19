import json
from pathlib import Path

import pytest

from scripts.model_backend import atomic_json, digest
from scripts.outcome_availability import build, export


def fixture(tmp_path):
    run = tmp_path / "run"
    atomic_json(run / "status.json", {"status": "incomplete", "counts": {"unresolved": 2}})
    text = "Mortality was observed until discharge. No scheduled assessment is specified."
    atomic_json(run / "sources/2/text.json", {"text": text, "sha256": digest(text)})
    rows = [
        {"id": "1", "status": "missing_fulltext"},
        {"id": "2", "status": "extracted", "result": {"eligibility": "include", "reason": "Target timepoint unresolved", "missing": ['No horizon: "Mortality was observed until discharge."'], "rows": []}},
        {"id": "3", "status": "extracted", "result": {"eligibility": "include", "rows": [{"limitations": ["Incomplete follow-up"], "validation_errors": []}], "missing": ["Some mortality data missing"]}},
        {"id": "4", "status": "extracted", "result": {"eligibility": "exclude", "reason": "Different outcome reported", "rows": []}},
    ]
    atomic_json(run / "extractions.json", rows)
    atomic_json(run / "accepted.json", [{"record_id": "3"}])
    atomic_json(run / "synthesis.json", {"estimate": 1.004, "k": 2})
    return run


def test_distinguishes_access_timing_accepted_limits_and_reported_exclusion(tmp_path):
    run = fixture(tmp_path)
    before = {str(p): p.read_bytes() for p in run.rglob('*') if p.is_file()}
    report = export(run, tmp_path / "new_export")
    categories = [r["category"] for r in report["records"]]
    assert categories == ["missing_fulltext_access", "unresolved_target_inputs", "accepted_with_reported_limitations", "reported_different_or_unavailable_outcome"]
    assert report["records"][1]["evidence_anchors"][0]["matches_source_text"]
    assert [q["record_id"] for q in report["continuation_queue"]] == ["1", "2"]
    assert report["synthesis_unchanged"]["estimate"] == 1.004
    assert all(Path(p).read_bytes() == b for p, b in before.items())
    with pytest.raises(ValueError, match="empty"):
        export(run, tmp_path / "new_export")


def test_quote_matching_never_claims_outcome_certainty(tmp_path):
    run = fixture(tmp_path)
    p = run / "sources/2/text.json"
    source = json.loads(p.read_text()); source["sha256"] = "wrong"
    atomic_json(p, source)
    report = build(run)
    r = report["records"][1]
    assert not r["source"]["text_hash_valid"]
    assert not r["evidence_anchors"][0]["matches_source_text"]
    assert r["category"] == "unresolved_target_inputs"
    assert 'no new claim-level adjudication' in r["support_status"]


@pytest.mark.parametrize("reason,cue", [("Unknown units", "units"), ("No analyzed sample size", "denominators"), ("No SD for change score", "dispersion")])
def test_routes_original_reasons_without_deciding_trial_error(tmp_path, reason, cue):
    run = fixture(tmp_path)
    atomic_json(run / "extractions.json", [{"id": "2", "status": "extracted", "result": {"missing": [reason]}}])
    r = build(run)
    assert cue in r["records"][0]["routing_cues"]
    assert r["records"][0]["reasons"][0]["text"] == reason
    assert r["continuation_queue"][0]["automatic_scientific_action_authorized"] is False


def test_active_run_and_parent_destination_refused(tmp_path):
    run = fixture(tmp_path)
    with pytest.raises(ValueError):
        export(run, tmp_path)
    atomic_json(run / "status.json", {"status": "running"})
    with pytest.raises(ValueError, match="finished"):
        build(run)


def test_mentioned_outcome_does_not_turn_design_exclusion_into_outcome_exclusion(tmp_path):
    run = fixture(tmp_path)
    atomic_json(run / "extractions.json", [{"id": "9", "status": "extracted", "result": {"eligibility": "exclude", "reason": "Nonrandomized case series reporting a mortality outcome; administration route unclear"}}])
    r = build(run)["records"][0]
    assert r["category"] == "reported_other_exclusion"
    assert "intervention_route" in r["routing_cues"]


def test_family_blocker_routes_pair_evidence_not_accepted_extraction_reason(tmp_path):
    run = fixture(tmp_path)
    atomic_json(run / "accepted.json", [{"record_id": "2"}, {"record_id": "3"}])
    atomic_json(run / "trial_families.json", {"rows": [], "unresolved": [{"reports": ["2", "3"], "reason": "Potential trial overlap unresolved"}]})
    atomic_json(run / "family_links.json", [{"report_a": "2", "report_b": "3", "relationship": "unclear", "reason": "Possible re-enrollment at shared sites", "evidence_a": "Mortality was observed until discharge.", "evidence_b": "Unmatched quote", "independently_verified": False}])
    report = build(run)
    pair = report["family_continuation_queue"][0]
    assert pair["reports"] == ["2", "3"]
    assert pair["pair_assessments"][0]["anchors"][0]["matches_source_text"]
    assert not pair["pair_assessments"][0]["anchors"][1]["matches_source_text"]
    assert not pair["automatic_scientific_action_authorized"]
    r = next(r for r in report["records"] if r["record_id"] == "3")
    assert r["category"] == "accepted_not_independent"
    assert "independence" in r["routing_cues"]
    assert any(x["locator"] == "family_links.json#/0/reason" for x in r["reasons"])
    q = next(q for q in report["continuation_queue"] if q["record_id"] == "3")
    assert len(q["actions"]) == 1 and "both original" in q["actions"][0]
    assert "family_links.json" in report["input_sha256"]


def test_family_source_paths_reject_traversal(tmp_path):
    run = fixture(tmp_path)
    atomic_json(run / "trial_families.json", {"rows": [], "unresolved": [{"reports": ["../outside"], "reason": "unknown"}]})
    with pytest.raises(ValueError, match="Unsafe family"):
        build(run)


def test_family_backend_failure_routes_to_receipt_not_new_scientific_claim(tmp_path):
    run = fixture(tmp_path)
    atomic_json(run / "trial_families.json", {"rows": [], "unresolved": [{"reports": ["2", "3"], "reason": "Potential trial overlap unresolved"}]})
    atomic_json(run / "family_links.json", [{"report_a": "2", "report_b": "3", "relationship": "unclear", "reason": "Codex model call failed; see response artifact"}])
    report = build(run)
    assert "failed requests" in report['family_continuation_queue'][0]['action']
    assert "not a scientific overlap finding" in report['family_continuation_queue'][0]['action']


def test_companion_evidence_is_consumed_without_changing_old_gate(tmp_path,monkeypatch):
    import hashlib
    import scripts.companion_denominators as companion
    run=fixture(tmp_path);baseline=build(run)
    note={'record_id':'2','companion_id':'new','target_source_file_sha256':hashlib.sha256((run/'sources/2/text.json').read_bytes()).hexdigest(),
          'source_checked':True,'family_supported':True,'denominators_supported':False,'numerical_admission':False}
    monkeypatch.setattr(companion,'annotation',lambda path:note)
    report=export(run,tmp_path/'annotated',companion_assessments=['assessment'])
    assert report['counts']==baseline['counts'] and report['synthesis_unchanged']==baseline['synthesis_unchanged']
    item=next(q for q in report['continuation_queue'] if q['record_id']=='2')
    assert item['companion_denominator_evidence']==[note] and 'completed primary-companion' in item['actions'][0]


def test_companion_annotation_cannot_attach_to_changed_target_source(tmp_path,monkeypatch):
    import scripts.companion_denominators as companion
    run=fixture(tmp_path)
    monkeypatch.setattr(companion,'annotation',lambda path:{'record_id':'2','companion_id':'new','target_source_file_sha256':'wrong'})
    with pytest.raises(ValueError,match='target source differs'):
        export(run,tmp_path/'annotated',companion_assessments=['assessment'])

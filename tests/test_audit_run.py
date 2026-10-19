import copy
import json

import pytest

from scripts.audit_run import audit, same
from scripts.autonomous_review import compare
from scripts.meta_analysis import synthesize
from scripts.model_backend import atomic_json, digest
from scripts.trial_families import resolve


def finished_run(tmp_path):
    protocol = dict(
        id="fixture",
        query="frozen query",
        outcome="ALT",
        unit="U/L",
        value_type="endpoint",
        measure="MD",
        model="fixed",
    )
    source = "Unadjusted endpoint means and SDs, 20 analyzed per arm."
    rows = [
        dict(
            record_id=str(i),
            study_id=str(i),
            outcome="ALT",
            unit="U/L",
            value_type="endpoint",
            timepoint_reported="week 12",
            n_treatment=20,
            n_control=20,
            mean_treatment=8 + i,
            mean_control=11,
            sd_treatment=2,
            sd_control=3,
            evidence=[source],
            design="parallel",
            validation_errors=[],
            source_sha256=digest(source),
        )
        for i in (1, 2)
    ]
    links = [
        dict(
            report_a="1",
            report_b="2",
            relationship="distinct_trials",
            independently_verified=True,
            evidence_a=source,
            evidence_b=source,
        )
    ]
    code = {"fixture.py": "# Test fixture only"}
    artifacts = {
        "protocol": protocol,
        "accepted": rows,
        "code_snapshots/" + digest(code): code,
        "extractions": [
            dict(
                id=r["record_id"],
                status="extracted",
                source_sha256=r["source_sha256"],
                result=dict(eligibility="include", rows=[r]),
            )
            for r in rows
        ],
        "trial_families": resolve(rows, links),
        "family_links": links,
        "screening": [dict(id=r["record_id"], decision="include") for r in rows],
        "search": dict(
            query=protocol["query"],
            hit_count=2,
            records=[dict(id=r["record_id"]) for r in rows],
        ),
        "synthesis": synthesize(rows, "MD", "fixed"),
        "status": dict(
            status="complete",
            protocol_sha256=digest(protocol),
            code_sha256=digest(code),
            errors=[],
            counts=dict(
                screened=2,
                fulltexts_attempted=2,
                accepted_effects=2,
                independent_effects=2,
                abstract_candidates=2,
                unresolved=0,
            ),
        ),
    }
    for row in rows:
        artifacts["sources/" + row["record_id"] + "/text"] = dict(
            text=source, sha256=digest(source)
        )
    for name, data in artifacts.items():
        atomic_json(tmp_path / (name + ".json"), data)
    return artifacts


def test_full_artifact_chain_passes_without_mutation(tmp_path):
    artifacts = finished_run(tmp_path)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*.json")}
    result = audit(tmp_path)
    assert result["valid"] and result["completion_supported"]
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob("*.json")}
    syn = artifacts["synthesis"]
    reference = dict(
        artifacts["protocol"],
        **{k: syn[k] for k in ("estimate", "ci_low", "ci_high", "k")},
        absolute_tolerance=0.02,
        expected_record_ids=["1", "2"],
    )
    atomic_json(tmp_path / "ref.json", reference)
    compare(tmp_path, tmp_path / "ref.json")
    assert json.loads((tmp_path / "benchmark_comparison.json").read_text())[
        "reproduced"
    ]


@pytest.mark.parametrize(
    "artifact,mutate,issue",
    [
        ("protocol", lambda d: d.update(query="changed"), "protocol_hash"),
        (
            "sources/1/text",
            lambda d: d.update(text="different source"),
            "source_hash:1",
        ),
        (
            "accepted",
            lambda d: d[0].update(mean_treatment=999),
            "accepted_extraction_rows_differ",
        ),
        (
            "trial_families",
            lambda d: d["rows"][0].update(mean_treatment=999),
            "family_resolution_replay",
        ),
        ("synthesis", lambda d: d.update(estimate=999), "synthesis_replay"),
        (
            "status",
            lambda d: d["counts"].update(unresolved=1),
            "status_count:unresolved",
        ),
        ("search", lambda d: d.update(hit_count=3), "incomplete_search_retrieval"),
        ("family_links", lambda d: d.clear(), "family_pair_coverage"),
        (
            "status",
            lambda d: d.update(errors=["unfinished"]),
            "unsupported_complete_status",
        ),
        ("status", lambda d: d.update(status="running"), "active_run"),
    ],
)
def test_inconsistent_artifacts_fail_closed(tmp_path, artifact, mutate, issue):
    original = finished_run(tmp_path)
    changed = copy.deepcopy(original[artifact])
    mutate(changed)
    atomic_json(tmp_path / (artifact + ".json"), changed)
    result = audit(tmp_path)
    assert not result["valid"]
    assert issue in result["issues"]


def test_deleted_evidence_and_path_identity_fail_closed(tmp_path):
    original = finished_run(tmp_path)
    (tmp_path / "sources/1/text.json").unlink()
    assert not audit(tmp_path)["valid"]
    atomic_json(tmp_path / "sources/1/text.json", original["sources/1/text"])
    original["accepted"][0]["record_id"] = "../outside"
    atomic_json(tmp_path / "accepted.json", original["accepted"])
    assert any("Unsafe source record identity" in x for x in audit(tmp_path)["issues"])


def test_roundoff_tolerance_does_not_accept_nonfinite_or_missing_fields():
    assert same({"x": [1.0]}, {"x": [1.0 + 1e-14]})
    assert not same(float("nan"), float("nan"))
    assert not same({"x": 1}, {"x": True})
    assert not same({"x": 1}, {})


def test_family_tier_audit_replays_every_feature_not_only_first_quote(tmp_path):
    from scripts.family_evidence_tiers import decide
    original = finished_run(tmp_path)
    protocol = original['protocol']; protocol['family_policy'] = 'family_evidence_tiers_v2'
    atomic_json(tmp_path / 'protocol.json', protocol)
    status = original['status']; status['protocol_sha256'] = digest(protocol)
    atomic_json(tmp_path / 'status.json', status)
    text = original['sources/1/text']['text']
    proposal = {'study_identity': 'distinct_randomizations', 'participant_reuse': 'theoretical_only',
                'features': [{'domain': d, 'evidence_a': text, 'evidence_b': text} for d in ['randomization', 'population']],
                'reason': 'Synthetic fixture', 'limitations': []}
    link = decide(proposal, (text, text), {'valid': True})
    link.update(report_a='1', report_b='2')
    atomic_json(tmp_path / 'family_links.json', [link])
    assert audit(tmp_path)['valid']
    link['evidence_tier_assessment']['features'][1]['evidence_b'] = 'Fabricated second-domain quotation'
    atomic_json(tmp_path / 'family_links.json', [link])
    assert 'family_evidence_tier_replay' in audit(tmp_path)['issues']

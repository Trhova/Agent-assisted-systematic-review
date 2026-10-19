import json

import pytest

from scripts.model_backend import atomic_json, digest
from scripts.rob2_draft import assess_run, evidence_errors


def proposal():
    return {
        **{
            f"domain_{i}": {
                "judgment": "Some concerns",
                "evidence_snippets": ["Exact source passage"],
            }
            for i in range(1, 6)
        },
        "overall_risk_of_bias": {"judgment": "High"},
    }


def test_risk_draft_requires_real_quotes_and_coherent_overall_rating():
    row = proposal()
    assert not evidence_errors(row, "Exact source passage")
    assert any("absent" in x for x in evidence_errors(row, "Different source"))
    row["overall_risk_of_bias"]["judgment"] = "Low"
    assert any("conflicts" in x for x in evidence_errors(row, "Exact source passage"))
    row["domain_1"]["evidence_snippets"] = ["Not reported"]
    assert not any(
        "Domain 1 evidence absent" in x
        for x in evidence_errors(row, "Exact source passage")
    )


@pytest.mark.parametrize("repair_valid", [False, True])
def test_outcome_specific_audit_does_not_change_numeric_results(tmp_path, monkeypatch, repair_valid):
    source = "Exact source passage"
    row = {
        "record_id": "trial",
        "study_id": "registry",
        "outcome": "ALT",
        "timepoint_reported": "12 weeks",
        "source_sha256": digest(source),
    }
    atomic_json(
        tmp_path / "status.json",
        {"status": "incomplete", "backend": "codex", "model": None},
    )
    atomic_json(
        tmp_path / "protocol.json",
        {"id": "hidden_benchmark_name", "eligibility": "parallel trials"},
    )
    atomic_json(tmp_path / "trial_families.json", {"rows": [row]})
    atomic_json(
        tmp_path / "sources/trial/text.json", {"text": source, "sha256": digest(source)}
    )
    atomic_json(tmp_path / "synthesis.json", {"estimate": 123.45})
    before = (tmp_path / "synthesis.json").read_bytes()

    checks = []

    def fake(prompt, schema, *args, **kwargs):
        assert "hidden_benchmark_name" not in prompt
        assert "123.45" not in prompt
        if "valid" in schema["properties"]:
            checks.append(prompt)
            if len(checks) == 2 and repair_valid:
                return {"valid": True, "problems": []}
            return {"valid": False, "problems": ["Unsupported assignment judgment"]}
        assert schema["properties"]["study_metadata"]["properties"]["outcome_assessed"][
            "enum"
        ] == ["ALT at 12 weeks"]
        assert schema["properties"]["overall_risk_of_bias"]["properties"][
            "confidence"
        ] == {"type": "null"}
        source_types = schema["properties"]["study_metadata"]["properties"]["sources_used"]["items"]["enum"]
        assert "other" in source_types  # Original preprints must be representable.
        assert "trial_registry" not in source_types  # Cited registries are not accessed sources.
        assert "preprint as other" in prompt
        return proposal()

    monkeypatch.setattr("scripts.rob2_draft.model_json", fake)
    result = assess_run(tmp_path)
    assert result["unverified"] == int(not repair_valid)
    assert result["source_checked"] == int(repair_valid)
    assert len(checks) == 2
    attempts = result["assessments"][0]["verification_attempts"]
    assert len(attempts) == 2
    assert attempts[0]["verification"]["valid"] is False
    assert (tmp_path / "synthesis.json").read_bytes() == before
    assert (
        json.loads((tmp_path / "rob2_draft.json").read_text())["assessments"][0][
            "status"
        ]
        == ("source_checked_draft" if repair_valid else "unverified_draft")
    )
    assert result["limitations"]


def test_risk_audit_cannot_overlap_numeric_runner(tmp_path):
    import fcntl

    import pytest

    work = tmp_path / "review" / "hash"
    work.mkdir(parents=True)
    atomic_json(work / "protocol.json", {"id": "review"})
    with (tmp_path / "review.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="active numerical"):
            assess_run(work)

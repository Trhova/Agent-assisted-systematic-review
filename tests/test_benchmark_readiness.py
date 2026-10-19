import hashlib

import pytest
import yaml

from scripts.benchmark_readiness import assessment
from scripts.model_backend import atomic_json, digest


def test_audit_separates_missing_search_exclusion_access_and_derivation(tmp_path):
    protocol = {
        "id": "case",
        "outcome": "FBG",
        "unit": "dimensionless",
        "value_type": "endpoint",
        "measure": "SMD",
        "model": "random",
    }
    ref = {
        "id": "case",
        "expected_record_ids": ["missing", "excluded", "inaccessible", "23899653"],
    }
    p, r, config, run = (
        tmp_path / "p.yaml",
        tmp_path / "r.json",
        tmp_path / "suite.yaml",
        tmp_path / "run",
    )
    p.write_text(yaml.safe_dump(protocol))
    atomic_json(r, ref)
    config.write_text(
        yaml.safe_dump(
            {
                "cases": [
                    {
                        "id": "case",
                        "protocol": str(p),
                        "reference": str(r),
                        "protocol_sha256": digest(protocol),
                        "reference_sha256": digest(ref),
                    }
                ]
            }
        )
    )
    for name, value in [
        ("protocol", protocol),
        ("status", {"status": "incomplete", "protocol_sha256": digest(protocol)}),
        ("search", {"records": [{"id": x} for x in ref["expected_record_ids"][1:]]}),
        (
            "screening",
            [{"id": "excluded", "decision": "exclude", "reason": "Wrong comparator"}],
        ),
        (
            "extractions",
            [
                {
                    "id": "23899653",
                    "status": "extracted",
                    "result": {
                        "eligibility": "include",
                        "missing": ["Endpoint SE only; SD unavailable"],
                    },
                }
            ],
        ),
    ]:
        atomic_json(run / (name + ".json"), value)
    atomic_json(run / "sources/23899653/text.json", {"text": "Primary table"})
    before = {
        str(f): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in run.rglob("*")
        if f.is_file()
    }
    result = assessment(config, {"case": str(run)})
    c = result["cases"][0]
    assert [a["category"] for a in c["next_actions"][:4]] == [
        "search_coverage",
        "eligibility_difference",
        "source_access",
        "supported_derivation_extension",
    ]
    assert c["source_coverage"]["present"] == 1
    assert c["action_count"] == 6
    assert not result["ready_for_broad_validation_run"]
    assert before == {
        str(f): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in run.rglob("*")
        if f.is_file()
    }
    atomic_json(run / "protocol.json", {})
    with pytest.raises(ValueError, match="artifact differs"):
        assessment(config, {"case": str(run)})

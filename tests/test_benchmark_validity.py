import json

import pytest

from scripts.autonomous_review import compare
from scripts.benchmark_suite import suite
from scripts.benchmark_validity import semantic_agreement, validate_target
from scripts.model_backend import atomic_json


def inputs():
    protocol = {
        "id": "case",
        "outcome": "ALT",
        "unit": "U/L",
        "value_type": "endpoint",
        "measure": "MD",
        "model": "fixed",
    }
    reference = dict(
        protocol, estimate=-2, ci_low=-3, ci_high=-1, k=2, absolute_tolerance=0.02
    )
    synthesis = dict(
        reference,
        effects=[dict(protocol, record_id="1"), dict(protocol, record_id="2")],
    )
    return protocol, reference, synthesis


@pytest.mark.parametrize("field", ["outcome", "unit", "value_type", "measure", "model"])
def test_semantic_mismatch_blocks_exact_numerical_match(tmp_path, field):
    protocol, reference, synthesis = inputs()
    synthesis["model"] = "random" if field == "model" else synthesis["model"]
    if field != "model":
        synthesis["effects"][1][field] = "incompatible"
    for name, value in [
        ("protocol", protocol),
        ("ref", reference),
        ("synthesis", synthesis),
        ("status", {"status": "complete"}),
    ]:
        atomic_json(tmp_path / (name + ".json"), value)
    compare(tmp_path, tmp_path / "ref.json")
    result = json.loads((tmp_path / "benchmark_comparison.json").read_text())
    assert result["numerically_matches"]
    assert not result["reproduced"]


def test_unknown_reference_estimand_is_not_agreement():
    p, r, s = inputs()
    assert semantic_agreement(p, r, s)["agrees"]
    del r["value_type"]
    assert semantic_agreement(p, r, s)["issues"] == [
        "value_type:unknown_protocol_or_reference"
    ]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True, "0.02"])
def test_invalid_tolerance_rejected(value):
    _, reference, _ = inputs()
    reference["absolute_tolerance"] = value
    with pytest.raises(ValueError):
        validate_target(reference)


@pytest.mark.parametrize("model", [None, "", "  "])
def test_new_suite_requires_explicit_model_before_any_artifact(tmp_path, model):
    with pytest.raises(ValueError, match="explicit nonempty model"):
        suite(tmp_path / "absent.yaml", tmp_path / "runs", model=model)
    assert not (tmp_path / "runs").exists()


def test_matching_numbers_without_provenance_cannot_pass(tmp_path):
    protocol, reference, synthesis = inputs()
    for name, value in [
        ("protocol", protocol),
        ("ref", reference),
        ("synthesis", synthesis),
        ("status", {"status": "complete"}),
    ]:
        atomic_json(tmp_path / (name + ".json"), value)
    compare(tmp_path, tmp_path / "ref.json")
    result = json.loads((tmp_path / "benchmark_comparison.json").read_text())
    assert result["numerically_matches"]
    assert not result["artifact_integrity"]["valid"]
    assert not result["reproduced"]

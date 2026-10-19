import copy
import hashlib

import pytest

from scripts.qualify_benchmark_method import POLICY, assess


@pytest.fixture
def manifest(tmp_path):
    text = "Risk ratio fixed Mantel-Haenszel normal confidence intervals without tau."
    source = tmp_path / "source.txt"
    source.write_text(text)
    values = {
        "measure": "RR",
        "model": "fixed",
        "weighting": "mantel_haenszel",
        "interval": "normal",
        "heterogeneity_estimator": "none",
    }
    return {
        "policy": POLICY,
        "candidate_id": "test",
        "declared_analysis": "complete mortality comparison",
        "assessment_mode": "agent_assisted_source_reading",
        "design": "independent_parallel_randomized",
        "sources": [
            {
                "id": "review",
                "path": str(source),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "role": "original_review",
                "url": "https://example.org/review",
            }
        ],
        "method": {
            k: {
                "value": v,
                "basis": "explicit_source",
                "evidence": [
                    {"source_id": "review", "quote": text, "locator": "Methods"}
                ],
            }
            for k, v in values.items()
        },
    }


def test_positive_is_preparation_not_execution(manifest):
    result = assess(manifest)
    assert result["primary_retrieval_ready"]
    assert not result["scientific_execution_authorized"]
    assert not result["reading_independently_verified"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("measure", "OR"),
        ("model", "random"),
        ("weighting", "inverse_variance"),
        ("interval", "hartung_knapp"),
    ],
)
def test_incompatible_exact_method_stops(manifest, field, value):
    manifest["method"][field]["value"] = value
    assert not assess(manifest)["primary_retrieval_ready"]


def test_software_default_is_not_source_method(manifest):
    manifest["method"]["weighting"]["basis"] = "software_default"
    assert not assess(manifest)["primary_retrieval_ready"]


def test_missing_and_wrong_quotes_stop(manifest):
    for evidence in (
        [],
        [{"source_id": "review", "quote": "not there", "locator": "Methods"}],
    ):
        changed = copy.deepcopy(manifest)
        changed["method"]["measure"]["evidence"] = evidence
        with pytest.raises(ValueError):
            assess(changed)


def test_mutated_source_stops(manifest):
    manifest["sources"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        assess(manifest)


@pytest.mark.parametrize(
    "design", ["mixed_randomized_observational", "cluster_randomized", "unknown"]
)
def test_design_must_qualify(manifest, design):
    manifest["design"] = design
    assert not assess(manifest)["primary_retrieval_ready"]

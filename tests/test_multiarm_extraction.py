import copy

import pytest
from jsonschema import Draft202012Validator

from scripts.multiarm import POLICY
from scripts.multiarm_extraction import SCHEMA, extract

SOURCE = "Randomized parallel groups A, B and C had no overlapping participants. Endpoint ALT at 12 weeks: A n=10 mean=20 SD=4; B n=12 mean=24 SD=5; C placebo n=11 mean=30 SD=6."
PROTOCOL = {
    "outcome": "ALT",
    "unit": "U/L",
    "value_type": "endpoint",
    "multiarm_policy": POLICY,
}


def proposal():
    return {
        "eligibility": "include",
        "reason": "Eligible randomized trial",
        "study_id": "trial",
        "outcome": "ALT",
        "unit": "U/L",
        "value_type": "endpoint",
        "timepoint_reported": "12 weeks",
        "timepoint_weeks": 12,
        "design": "parallel",
        "all_randomized_arms_enumerated": True,
        "disjointness_evidence": [
            "Randomized parallel groups A, B and C had no overlapping participants."
        ],
        "missing": [],
        "arms": [
            {
                "arm_id": name,
                "label": name,
                "role": role,
                "exclusion_reason": "",
                "n": n,
                "mean": mean,
                "sd": sd,
                "evidence": [SOURCE],
            }
            for name, role, n, mean, sd in [
                ("A", "treatment", 10, 20, 4),
                ("B", "treatment", 12, 24, 5),
                ("C", "control", 11, 30, 6),
            ]
        ],
    }


def run(p, valid=True):
    calls = []

    def call(prompt, schema):
        calls.append(prompt)
        value = p if len(calls) == 1 else {"valid": valid, "problems": []}
        Draft202012Validator(schema).validate(value)
        return copy.deepcopy(value)

    return extract(SOURCE, PROTOCOL, {}, call), calls


def test_verified_original_arms_then_deterministic_combination():
    result, calls = run(proposal())
    row = result["rows"][0]
    assert len(calls) == 2
    assert row["n_treatment"] == 22 and row["n_control"] == 11
    assert row["mean_treatment"] == pytest.approx(488 / 22)
    assert row["original_arms_independently_verified"]
    assert len(row["derivation"]["all_arms"]) == 3
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize(
    "failure", ["quote", "enumeration", "missing", "role", "verification"]
)
def test_unsupported_original_arm_evidence_never_pools(failure):
    p = proposal()
    if failure == "quote":
        p["arms"][0]["evidence"] = ["Invented support"]
    if failure == "enumeration":
        p["all_randomized_arms_enumerated"] = False
    if failure == "missing":
        p["missing"] = ["One eligible denominator unknown"]
    if failure == "role":
        p["arms"][0]["role"] = "unclear"
    result, calls = run(p, valid=failure != "verification")
    assert not result["rows"] and result["missing"]
    assert len(calls) == (2 if failure == "verification" else 1)


def test_extension_requires_explicit_new_protocol():
    with pytest.raises(ValueError, match="prespecified"):
        extract(SOURCE, {"value_type": "endpoint"}, {}, None)

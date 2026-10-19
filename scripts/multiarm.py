"""Prespecified combination of disjoint continuous-outcome study arms.

Cochrane Handbook 6.5.2.10: retain within-arm AND between-arm sums of squares.
This extension is opt-in and is not enabled for frozen historical benchmarks.
"""

from __future__ import annotations

import math

POLICY = "combine_all_eligible_disjoint_arms_v1"


def combine(arms):
    if not arms:
        raise ValueError("No arms supplied")
    if len({a["arm_id"] for a in arms}) != len(arms):
        raise ValueError("Repeated arm identity")
    for a in arms:
        if not a.get("independently_verified") or not a.get("evidence"):
            raise ValueError(
                "Original arm values must be source-verified before combination"
            )
        if isinstance(a["n"], bool) or not isinstance(a["n"], int) or a["n"] < 2:
            raise ValueError("Each analyzed arm N must be an integer >=2")
        if (
            any(
                isinstance(a[k], bool)
                or not isinstance(a[k], (float, int))
                or not math.isfinite(a[k])
                for k in ["mean", "sd"]
            )
            or a["sd"] < 0
        ):
            raise ValueError("Invalid reported mean/SD")
    total = sum(a["n"] for a in arms)
    mean = sum(a["n"] * a["mean"] for a in arms) / total
    ss = sum(
        (a["n"] - 1) * a["sd"] ** 2 + a["n"] * (a["mean"] - mean) ** 2 for a in arms
    )
    return {
        "n": total,
        "mean": mean,
        "sd": math.sqrt(ss / (total - 1)),
        "arm_ids": [a["arm_id"] for a in arms],
        "derivation": "within-arm plus between-arm sums of squares",
        "original_arms": arms,
    }


def comparison(arms, policy, disjointness_evidence):
    if policy != POLICY:
        raise ValueError("Explicit prespecified arm-combination policy required")
    if not disjointness_evidence:
        raise ValueError(
            "Disjoint randomized groups must be established from source evidence"
        )
    for key in ["study_id", "outcome", "unit", "value_type", "timepoint_reported"]:
        if len({a[key] for a in arms}) != 1:
            raise ValueError("Incompatible arm " + key)
    if len({a["arm_id"] for a in arms}) != len(arms):
        raise ValueError("An arm cannot contribute to both sides or appear twice")
    if any(a["role"] not in ["treatment", "control", "ineligible"] for a in arms):
        raise ValueError("Unresolved arm eligibility")
    if any(a["role"] == "ineligible" and not a.get("exclusion_reason") for a in arms):
        raise ValueError("Excluded arm requires a protocol-based reason")
    treatment = combine([a for a in arms if a["role"] == "treatment"])
    control = combine([a for a in arms if a["role"] == "control"])
    return {
        "study_id": arms[0]["study_id"],
        "outcome": arms[0]["outcome"],
        "unit": arms[0]["unit"],
        "value_type": arms[0]["value_type"],
        "timepoint_reported": arms[0]["timepoint_reported"],
        "n_treatment": treatment["n"],
        "mean_treatment": treatment["mean"],
        "sd_treatment": treatment["sd"],
        "n_control": control["n"],
        "mean_control": control["mean"],
        "sd_control": control["sd"],
        "derivation": {
            "policy": policy,
            "treatment": treatment,
            "control": control,
            "all_arms": arms,
            "disjointness_evidence": disjointness_evidence,
        },
    }

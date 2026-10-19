"""Auditable independent two-arm continuous-outcome synthesis.

Inverse-variance fixed effect and DerSimonian-Laird random effects, normal CIs.
No imputation of SDs, baseline/change correlations, or dependent comparisons.
"""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Any


def effect(row: dict[str, Any], measure: str = "MD") -> dict[str, Any]:
    n1, n0 = row["n_treatment"], row["n_control"]
    if any(isinstance(x, bool) or not isinstance(x, int) or x < 2 for x in (n1, n0)):
        raise ValueError("Arm sample sizes must be integers >=2")
    m1, m0, s1, s0 = [
        row[k] for k in ("mean_treatment", "mean_control", "sd_treatment", "sd_control")
    ]
    if (
        any(
            isinstance(x, bool)
            or not isinstance(x, (int, float))
            or not math.isfinite(x)
            for x in (m1, m0, s1, s0)
        )
        or min(s1, s0) < 0
    ):
        raise ValueError("Means/SDs must be finite; SDs nonnegative")
    y = m1 - m0
    v = s1 * s1 / n1 + s0 * s0 / n0
    if measure == "SMD":
        df = n1 + n0 - 2
        sp = math.sqrt(((n1 - 1) * s1 * s1 + (n0 - 1) * s0 * s0) / df)
        if not sp:
            raise ValueError("Zero pooled SD")
        # Hedges correction and RevMan variance (Deeks/Higgins, 2022, p. 3).
        j = 1 - 3 / (4 * df - 1)
        d = y / sp
        y = j * d
        v = (n1 + n0) / (n1 * n0) + y * y / (2 * (n1 + n0 - 3.94))
    elif measure != "MD":
        raise ValueError("Supported measures: MD, SMD")
    if v <= 0:
        raise ValueError("Nonpositive sampling variance")
    return {
        **row,
        "source_unit": row["unit"],
        "unit": "dimensionless" if measure == "SMD" else row["unit"],
        "effect": y,
        "variance": v,
        "measure": measure,
    }


def pool(
    rows: list[dict[str, Any]], model: str = "random", *, value_type_policy=None
) -> dict[str, Any]:
    if model not in ("fixed", "random"):
        raise ValueError("Unknown pooling model")
    if len(rows) < 2:
        raise ValueError("At least two independent studies required")
    ids = [r["study_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Dependent comparisons: repeated study_id")
    mixed_md = value_type_policy == "endpoint_or_change_md_v1"
    if mixed_md and any(
        r["measure"] != "MD" or r["value_type"] not in {"endpoint", "change"}
        for r in rows
    ):
        raise ValueError(
            "Endpoint/change pooling requires MD and known score definitions"
        )
    for key in ("outcome", "unit", "measure") + (() if mixed_md else ("value_type",)):
        if len({r[key] for r in rows}) != 1:
            raise ValueError(f"Incompatible {key}")
    if any(
        not math.isfinite(r["effect"])
        or not math.isfinite(r["variance"])
        or r["variance"] <= 0
        for r in rows
    ):
        raise ValueError("Invalid effect/variance")
    y = [r["effect"] for r in rows]
    w = [1 / r["variance"] for r in rows]
    sw = sum(w)
    fixed = sum(a * b for a, b in zip(w, y)) / sw
    q = sum(a * (b - fixed) ** 2 for a, b in zip(w, y))
    df = len(y) - 1
    c = sw - sum(a * a for a in w) / sw
    tau = max(0, (q - df) / c)
    weights = [1 / (r["variance"] + (tau if model == "random" else 0)) for r in rows]
    mean = sum(a * b for a, b in zip(weights, y)) / sum(weights)
    se = math.sqrt(1 / sum(weights))
    z = NormalDist().inv_cdf(0.975)
    return {
        "k": len(rows),
        "model": model,
        "tau2_estimator": "DerSimonian-Laird",
        "ci_method": "normal",
        "estimate": mean,
        "se": se,
        "ci_low": mean - z * se,
        "ci_high": mean + z * se,
        "Q": q,
        "I2": max(0, (q - df) / q) * 100 if q else 0,
        "tau2": tau,
        "studies": ids,
        "weights": [a / sum(weights) for a in weights],
    }


def synthesize(
    rows: list[dict[str, Any]], measure: str, model: str, *, value_type_policy=None
) -> dict[str, Any]:
    if measure == "RR":
        from scripts.binary_outcomes import synthesize as binary_synthesize
        return binary_synthesize(rows, model)
    effects = [effect(r, measure) for r in rows]
    result = pool(effects, model, value_type_policy=value_type_policy)
    result["effects"] = effects
    result["leave_one_out"] = (
        [
            {
                "omitted": r["study_id"],
                **pool(
                    effects[:i] + effects[i + 1 :],
                    model,
                    value_type_policy=value_type_policy,
                ),
            }
            for i, r in enumerate(effects)
        ]
        if len(rows) > 2
        else []
    )
    return result

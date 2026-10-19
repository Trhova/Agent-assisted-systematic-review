"""Fail-closed scientific comparison, separate from arithmetic agreement."""

import math

FIELDS = ("outcome", "unit", "value_type", "measure", "model")


def validate_target(reference):
    for key in ("estimate", "ci_low", "ci_high", "absolute_tolerance"):
        value = reference.get(key)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"Reference {key} must be finite numeric")
    if reference["absolute_tolerance"] < 0:
        raise ValueError("Reference absolute_tolerance must be nonnegative")
    if not reference["ci_low"] <= reference["estimate"] <= reference["ci_high"]:
        raise ValueError("Reference confidence interval must contain estimate")
    if type(reference.get("k")) is not int or reference["k"] < 2:
        raise ValueError("Reference k must be an integer >=2")


def semantic_agreement(protocol, reference, synthesis):
    issues = []
    effects = synthesis.get("effects", [])
    if not effects:
        issues.append("missing_effect_semantics")
    fields = FIELDS + (("intervention_route",) if "intervention_route" in protocol or "intervention_route" in reference else ())
    for key in fields:
        wanted, target = protocol.get(key), reference.get(key)
        if wanted is None or target is None:
            issues.append(f"{key}:unknown_protocol_or_reference")
        elif wanted != target:
            issues.append(f"{key}:protocol_reference_mismatch")
        observed = (
            [synthesis.get("model")]
            if key == "model"
            else [r.get(key) for r in effects]
        )
        allowed = {wanted}
        if (
            key == "value_type"
            and wanted == "endpoint_or_change_md_v1"
            and protocol.get("measure") == reference.get("measure") == "MD"
        ):
            allowed = {"endpoint", "change"}
        if any(v is None or v not in allowed for v in observed):
            issues.append(f"{key}:observed_protocol_mismatch")
    return {"agrees": not issues, "issues": issues}

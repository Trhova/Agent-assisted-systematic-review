"""Independent parallel binary risks: prespecified fixed Mantel-Haenszel RR.

Deeks/Higgins, Statistical algorithms in RevMan 5, pp. 2–3, 5–6.
Never treats a rate/hazard ratio as a risk ratio or imputes event counts.
"""
import copy
import math
from statistics import NormalDist

POLICY = "binary_rr_mh_fixed_v1"


def extraction_schema(base):
    schema = copy.deepcopy(base)
    row = schema["properties"]["rows"]["items"]
    for key in ("mean_treatment", "mean_control", "sd_treatment", "sd_control"):
        del row["properties"][key]
        row["required"].remove(key)
    for key in ("events_treatment", "events_control"):
        row["properties"][key] = {"type": ["integer", "null"]}
        row["required"].append(key)
    for arm in ("treatment", "control"):
        key = "event_components_" + arm
        row["properties"][key] = {"type": "array", "items": {"type": "integer"}}
        row["required"].append(key)
    row["properties"]["value_type"] = {"type": "string", "enum": [POLICY]}
    return schema


def counts(row):
    values = [row.get(k) for k in ("events_treatment", "n_treatment", "events_control", "n_control")]
    if any(type(v) is not int for v in values):
        raise ValueError("Binary counts and denominators must be explicit integers")
    a, n1, c, n0 = values
    if min(n1, n0) < 1 or not 0 <= a <= n1 or not 0 <= c <= n0:
        raise ValueError("Binary event counts outside denominator")
    for arm, count in (("treatment", a), ("control", c)):
        components = row.get("event_components_" + arm, [])
        if components and (any(type(x) is not int or x < 0 for x in components) or sum(components) != count):
            raise ValueError("Event components must be nonnegative integers summing to events")
    return a, n1, c, n0


def effect(row):
    a, n1, c, n0 = counts(row)
    if (a == c == 0) or (a == n1 and c == n0):
        return None  # Retained in the synthesis's explicit noninformative ledger.
    correction = 0.5 if min(a, n1-a, c, n0-c) == 0 else 0.0
    aa, cc, nn1, nn0 = a+correction, c+correction, n1+2*correction, n0+2*correction
    y = math.log((aa/nn1)/(cc/nn0))
    v = 1/aa + 1/cc - 1/nn1 - 1/nn0
    return {**row, "measure": "RR", "effect": y, "effect_scale": "log_risk_ratio",
            "variance": v, "source_unit": row["unit"],
            "binary_audit": {"continuity_correction_per_cell": correction,
                             "original_counts": [a, n1, c, n0],
                             "analysis_counts": [aa, nn1, cc, nn0], "policy": POLICY}}


def synthesize(rows, model, *, minimum=2):
    if model != "mantel_haenszel_fixed" or any(r.get("value_type") != POLICY for r in rows):
        raise ValueError("Binary synthesis requires explicit fixed MH RR policy")
    if len({r["study_id"] for r in rows}) != len(rows):
        raise ValueError("Dependent comparisons: repeated study_id")
    for key in ("outcome", "unit", "value_type"):
        if len({r[key] for r in rows}) != 1:
            raise ValueError("Incompatible " + key)
    effects, excluded = [], []
    for row in rows:
        e = effect(row)
        if e is None:
            excluded.append({"record_id": row.get("record_id"), "study_id": row["study_id"],
                             "reason": "Both arms zero events or both arms all events; undefined relative effect",
                             "original_counts": list(counts(row))})
        else:
            effects.append(e)
    if len(effects) < minimum:
        raise ValueError("At least two informative independent binary studies required")
    rr_numerator = rr_denominator = variance_numerator = 0.0
    weights = []
    for e in effects:
        a, n1, c, n0 = e["binary_audit"]["analysis_counts"]
        total = n1+n0
        rr_numerator += a*n0/total
        rr_denominator += c*n1/total
        variance_numerator += (n1*n0*(a+c)-a*c*total)/(total*total)
        weights.append(c*n1/total)
    estimate = rr_numerator/rr_denominator
    log_estimate = math.log(estimate)
    se = math.sqrt(variance_numerator/(rr_numerator*rr_denominator))
    z = NormalDist().inv_cdf(.975)
    q = sum((e["effect"]-log_estimate)**2/e["variance"] for e in effects)
    result = {"k": len(effects), "model": model, "measure": "RR", "effect_scale": "risk_ratio",
              "estimate": estimate, "log_estimate": log_estimate, "se": se, "se_scale": "log_risk_ratio",
              "ci_low": math.exp(log_estimate-z*se), "ci_high": math.exp(log_estimate+z*se),
              "Q": q, "I2": max(0, (q-len(effects)+1)/q)*100 if q else 0,
              "tau2": 0.0, "tau2_estimator": "not estimated; fixed effect",
              "ci_method": "normal on log RR; MH variance",
              "studies": [e["study_id"] for e in effects], "weights": [w/sum(weights) for w in weights],
              "effects": effects, "noninformative_studies": excluded,
              "zero_event_policy": POLICY, "leave_one_out": []}
    if minimum == 2 and len(effects) > 2:
        result["leave_one_out"] = [
            {"omitted": r["study_id"], **synthesize([e for e in rows if e["study_id"] != r["study_id"]], model, minimum=1)}
            for r in effects]
    return result

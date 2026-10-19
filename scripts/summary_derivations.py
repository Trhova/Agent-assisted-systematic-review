"""Explicit optional normal-distribution estimation from within-arm quartiles.

Luo et al., doi:10.1177/0962280216669183, Eq 11; Wan et al.,
doi:10.1186/1471-2288-14-135, Eq 16. Never an observed SD.
"""
from __future__ import annotations

import copy
import math
import re
from statistics import NormalDist

from scripts.model_backend import digest

POLICY = "luo_wan_quartiles_v1"
METHOD = {"mean": "Luo2018_Eq11", "sd": "Wan2014_Eq16", "distribution": "normal"}


def estimate(q1, median, q3, n):
    if type(n) is not int or n < 5:
        raise ValueError("Quartile estimation requires an evidenced analyzed n >= 5")
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in (q1, median, q3)):
        raise ValueError("Finite original quartiles required")
    if not q1 <= median <= q3 or q1 == q3:
        raise ValueError("Ordered nondegenerate quartiles required")
    weight = 0.7 + 0.39 / n
    return (weight * (q1 + q3) / 2 + (1 - weight) * median,
            (q3 - q1) / (2 * NormalDist().inv_cdf((0.75 * n - 0.125) / (n + 0.25))))


def extraction_schema(base, protocol):
    schema = copy.deepcopy(base)
    row = schema["properties"]["rows"]["items"]
    row["properties"]["outcome"] = {"type": "string", "enum": [protocol["outcome"]]}
    fields = {}
    for arm in ("treatment", "control"):
        fields["summary_type_" + arm] = {"type": "string", "enum": ["mean_SD", "median_IQR"]}
        for name in ("q1", "median", "q3"):
            fields[name + "_" + arm] = {"type": ["number", "null"]}
        for name in ("summary_evidence", "denominator_evidence"):
            fields[name + "_" + arm] = {"type": "array", "items": {"type": "string"}, "minItems": 1}
        fields["source_locator_" + arm] = {"type": "string"}
    row["properties"].update(fields)
    row["required"] += list(fields)
    return schema


def instructions():
    return ("Use reported unadjusted endpoint means and SDs when present (summary_type mean_SD, quartile fields null). "
            "Only under summary_policy luo_wan_quartiles_v1, if these are unavailable, extract explicitly reported within-arm endpoint median and first/third quartiles (summary_type median_IQR), with mean and SD fields NULL. Software estimates these deterministically; do not calculate them yourself. An IQR width alone, min/max range, SE, adjusted estimate or ambiguous brackets is insufficient. "
            "For each arm provide separate exact verbatim summary_evidence quotes identifying statistic types and values, denominator_evidence for outcome-specific analyzed n, and table/page source_locator. No inferred n or substitution of randomized for missing analyzed n. Retain source units. These estimates assume an approximately normal distribution and are not observed statistics. ")


def derive(row, source, protocol, source_sha256):
    if protocol.get("summary_policy") != POLICY or row["value_type"] != "endpoint":
        raise ValueError("Quartile estimation not prespecified for this endpoint")
    if row["summary_type_treatment"] != row["summary_type_control"]:
        raise ValueError("Mixed arm summary definitions require a separate policy")
    result = copy.deepcopy(row)
    audit = []
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    for arm in ("treatment", "control"):
        n = row["n_" + arm]
        if type(n) is not int or n < 2:
            raise ValueError("Evidenced analyzed denominator required")
        for name in ("summary_evidence", "denominator_evidence"):
            quotes = row[name + "_" + arm]
            if not quotes or any(not q.strip() or norm(q) not in norm(source) for q in quotes):
                raise ValueError("Summary or denominator quote absent from source")
        if not row["source_locator_" + arm].strip():
            raise ValueError("Source locator required")
        kind = row["summary_type_" + arm]
        original = {k: row[k + "_" + arm] for k in ("mean", "sd", "q1", "median", "q3", "n")}
        if kind == "median_IQR":
            if original["mean"] is not None or original["sd"] is not None:
                raise ValueError("Estimated means/SDs must not be extracted as reported")
            mean, sd = estimate(original["q1"], original["median"], original["q3"], n)
        elif kind == "mean_SD":
            if any(original[k] is not None for k in ("q1", "median", "q3")):
                raise ValueError("Reported mean/SD must not contain unused quartiles")
            mean, sd = original["mean"], original["sd"]
            if any(type(x) not in (int, float) or not math.isfinite(x) for x in (mean, sd)) or sd <= 0:
                raise ValueError("Finite reported mean and positive SD required")
        else:
            raise ValueError("Unsupported original summary")
        result["mean_" + arm], result["sd_" + arm] = mean, sd
        audit.append({"arm": arm, "original_type": kind, "original_statistics": original,
                      "unit": row["unit"], "source_locator": row["source_locator_" + arm],
                      "summary_evidence": row["summary_evidence_" + arm],
                      "denominator_evidence": row["denominator_evidence_" + arm],
                      "source_sha256": source_sha256, "estimated": kind == "median_IQR",
                      "method": METHOD if kind == "median_IQR" else "reported_mean_SD",
                      "derived_mean": mean, "derived_sd": sd,
                      "method_sha256": digest(METHOD),
                      "limitation": "Normal-distribution approximation; conventional effect variance ignores summary-estimation uncertainty" if kind == "median_IQR" else None})
    result["original_statistics_sha256"] = digest(row)
    result["summary_audit"] = audit
    return result


def derive_with_quote_repair(row, source, protocol, source_sha256, call):
    """One quote-only repair, with statistics immutable and rejected text retained."""
    import json

    fields = [prefix + arm for arm in ("treatment", "control")
              for prefix in ("summary_evidence_", "denominator_evidence_")]
    normalize = lambda s: re.sub(r"\s+", " ", s).strip()
    normalized = normalize(source)
    if any(not row.get(f) or any(not q.strip() or normalize(q) not in normalized for q in row[f]) for f in fields):
        schema = {"type": "object", "additionalProperties": False,
                  "properties": {f: {"type": "array", "items": {"type": "string"}} for f in fields}, "required": fields}
        repaired = call("Repair only the four source quotation fields for the proposed extraction. Return separate verbatim source snippets for each arm's summary type/values and outcome-specific analyzed denominator. Do not join nonadjacent text, add labels, change any numbers, infer missing data, or treat randomized n as analyzed without support. Empty lists if unsupported. An independent verifier will assess every statistic against the complete primary article.\nPROPOSED:\n" + json.dumps(row) + "\nPRIMARY ARTICLE:\n" + source, schema)
        row = copy.deepcopy(row)
        row["original_transformation_evidence"] = {f: row.get(f) for f in fields}
        row["discarded_transformation_evidence"] = {}
        for f in fields:
            row[f] = [q for q in repaired[f] if q.strip() and normalize(q) in normalized]
            row["discarded_transformation_evidence"][f] = [q for q in repaired[f] if q not in row[f]]
    return derive(row, source, protocol, source_sha256)

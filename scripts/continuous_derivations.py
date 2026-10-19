"""Opt-in, source-audited continuous statistics; no imputation or denominator inference."""

from __future__ import annotations

import copy
import json
import math
import re

from scripts.model_backend import digest

POLICY = "within_arm_se_to_sd_v1"
MIXED_MD = "endpoint_or_change_md_v1"


def allowed_value_types(protocol):
    if protocol.get("value_type") == MIXED_MD:
        if protocol.get("measure") != "MD":
            raise ValueError("Endpoint/change combination is supported only for MD")
        return {"endpoint", "change"}
    return {protocol.get("value_type")}


def extraction_schema(base, protocol=None):
    schema = copy.deepcopy(base)
    row = schema["properties"]["rows"]["items"]
    if protocol:
        row["properties"]["outcome"] = {"type": "string", "enum": [protocol["outcome"]]}
    fields = {}
    for arm in ("treatment", "control"):
        fields.update(
            {
                "dispersion_type_" + arm: {"type": "string", "enum": ["SD", "SE"]},
                "reported_dispersion_" + arm: {"type": "number"},
                "dispersion_scope_" + arm: {
                    "type": "string",
                    "enum": [
                        "unadjusted_arm_mean",
                        "individual_scores",
                        "unclear",
                        "adjusted_estimate",
                        "between_arm_difference",
                    ],
                },
                "dispersion_evidence_" + arm: {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
                "denominator_evidence_" + arm: {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
                "source_locator_" + arm: {"type": "string"},
            }
        )
    row["properties"].update(fields)
    row["required"] += list(fields)
    return schema


def derive(row, source, protocol, source_sha256):
    """Retain model-extracted originals and deterministic derivation provenance."""
    result = copy.deepcopy(row)

    def norm(s):
        return re.sub(r"\s+", " ", s).strip()

    if row["value_type"] not in allowed_value_types(protocol):
        raise ValueError("Unsupported score definition")
    audit = []
    for arm in ("treatment", "control"):
        kind = row["dispersion_type_" + arm]
        value = row["reported_dispersion_" + arm]
        n = row["n_" + arm]
        if (
            type(n) is not int
            or n < 2
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError("Invalid original dispersion or analyzed denominator")
        for prefix in ("dispersion_evidence_", "denominator_evidence_"):
            quotes = row[prefix + arm]
            if (
                not isinstance(quotes, list)
                or not quotes
                or any(not q.strip() or norm(q) not in norm(source) for q in quotes)
            ):
                raise ValueError("Transformation evidence absent from primary source")
        if not row["source_locator_" + arm].strip():
            raise ValueError("Missing table/page locator")
        if kind == "SE":
            if protocol.get("dispersion_policy") != POLICY:
                raise ValueError("SE conversion is not prespecified")
            if row["dispersion_scope_" + arm] != "unadjusted_arm_mean":
                raise ValueError("SE must describe an unadjusted within-arm mean")
            if row["sd_" + arm] is not None:
                raise ValueError(
                    "Extract original SE with null SD; derivation is deterministic"
                )
            sd = value * math.sqrt(n)
        elif kind == "SD":
            if (
                row["dispersion_scope_" + arm] != "individual_scores"
                or row["sd_" + arm] != value
            ):
                raise ValueError("Reported SD field or scope mismatch")
            sd = value
        else:
            raise ValueError("Unknown dispersion statistic")
        result["sd_" + arm] = sd
        audit.append(
            {
                "arm": arm,
                "original_type": kind,
                "original_value": value,
                "unit": row["unit"],
                "value_type": row["value_type"],
                "analyzed_n": n,
                "denominator_evidence": row["denominator_evidence_" + arm],
                "dispersion_evidence": row["dispersion_evidence_" + arm],
                "source_locator": row["source_locator_" + arm],
                "source_sha256": source_sha256,
                "derived_sd": sd,
                "transformation": "SD=SE*sqrt(analyzed_within_arm_n)"
                if kind == "SE"
                else "reported_SD",
            }
        )
    result["original_statistics_sha256"] = digest(row)
    result["dispersion_audit"] = audit
    return result


def derive_with_quote_repair(row, source, protocol, source_sha256, call):
    """One bounded repair of quote fields; never let repair alter statistics."""
    fields = [
        p + a
        for a in ("treatment", "control")
        for p in ("dispersion_evidence_", "denominator_evidence_")
    ]
    normalized = re.sub(r"\s+", " ", source).strip()
    if any(
        not row.get(f)
        or any(
            not q.strip() or re.sub(r"\s+", " ", q).strip() not in normalized
            for q in row[f]
        )
        for f in fields
    ):
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                f: {"type": "array", "items": {"type": "string"}} for f in fields
            },
            "required": fields,
        }
        repaired = call(
            "Repair only the four source quotation fields for this proposed extraction. Return exact source snippets (whitespace may differ), separately for each arm's dispersion type/value and outcome analyzed denominator. Do not prepend page labels or join nonadjacent text in one quote. Return empty lists if unsupported. Do not infer or change numbers, dispersion type, population or scope. A separate verifier will still check every statistic.\nPROPOSED:\n"
            + json.dumps(row)
            + "\nPRIMARY ARTICLE:\n"
            + source,
            schema,
        )
        row = copy.deepcopy(row)
        row["original_transformation_evidence"] = {f: row.get(f) for f in fields}
        row["discarded_transformation_evidence"] = {}
        for f in fields:
            # Match the ordinary quotation-repair policy: keep exact snippets,
            # retain rejected snippets for audit, then verify statistical meaning
            # independently against the complete source. Every field still needs
            # nonempty matched evidence; a matching fragment is not proof of n.
            row[f] = [
                q
                for q in repaired[f]
                if q.strip() and re.sub(r"\s+", " ", q).strip() in normalized
            ]
            row["discarded_transformation_evidence"][f] = [
                q for q in repaired[f] if q not in row[f]
            ]
    return derive(row, source, protocol, source_sha256)


def extraction_instructions(protocol):
    allowed_value_types(protocol)
    return (
        "Extract the prespecified score definition. For endpoint_or_change_md_v1 prefer endpoint means and dispersions; if unavailable use reported within-arm mean changes and their own dispersions. Never derive change SD from baseline/final SD or combine endpoint and change within a comparison. "
        "Extract original dispersion values and types SD or SE separately for each arm. SE is permitted only for an explicitly unadjusted within-arm mean with the outcome-specific analyzed n supported by source evidence. Never use an adjusted mean SE or between-group difference SE. For SE set sd_treatment/sd_control null: software derives SD deterministically. For SD copy the original into sd and reported_dispersion and set scope individual_scores. "
        "Use arrays of separate exact verbatim quotes, never concatenate nonadjacent passages in one string. Quote exact dispersion footnotes/headers and exact evidence for analyzed denominator applicability to this outcome/timepoint, and provide table/page locators. Conflicting denominators remain unresolved with no row. No guessed SDs, denominators, graph extraction or unit conversions. "
    )

"""Opt-in study-identity policy; positive reuse and unresolved identity still block."""
from itertools import combinations
import json

from scripts.family_adjudication import contains, VERIFY

POLICY = "family_evidence_tiers_v2"
TEXT = {"type": "string"}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["study_identity", "participant_reuse", "features", "reason", "limitations"],
    "properties": {
        "study_identity": {"type": "string", "enum": ["same_study", "distinct_randomizations", "unresolved"]},
        "participant_reuse": {"type": "string", "enum": ["documented", "conflicting_evidence", "theoretical_only", "not_indicated"]},
        "features": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "required": ["domain", "evidence_a", "evidence_b"],
            "properties": {"domain": {"type": "string", "enum": ["randomization", "registration", "population", "recruitment", "baseline", "intervention", "explicit_linkage"]}, "evidence_a": TEXT, "evidence_b": TEXT}}},
        "reason": TEXT, "limitations": {"type": "array", "items": TEXT},
    },
}
RULE = """Use supplied original sources only. Distinguish study identity from participant reuse.
Same-study companion reports are not separate randomized studies. Documented participant reuse,
conflicting cohort linkage or unestablished study identity remain blocked. Different registration
numbers alone never establish separate trials. A distinct-randomizations finding needs affirmative
separate randomization/cohort evidence plus another source-backed characteristic (population,
recruitment, intervention, baseline or explicit linkage). Common authors/sites/calendar dates
are investigation leads, not proof of duplication. Hypothetical later reenrollment, without
an affirmative reuse/linkage statement or conflicting cohort identity, is a residual limitation,
not by itself grounds to deny otherwise evidenced separate randomizations. Do not claim individual
participant disjointness when it is not demonstrated. Explicit reuse always overrides distinct
study identity. Quote one contiguous verbatim passage from EACH source for each feature.
Do not use remembered trials, published pooled answers, or absence of proof as proof of distinctness.
"""


def decide(proposal, sources, verification):
    """Deterministic evidence-tier gate; scientific entailment needs second review."""
    features = proposal["features"]
    valid_features = bool(features) and all(
        contains(sources[0], f["evidence_a"]) and contains(sources[1], f["evidence_b"])
        for f in features)
    domains = {f["domain"] for f in features}
    verified = valid_features and verification.get("valid") is True
    identity, reuse = proposal["study_identity"], proposal["participant_reuse"]
    relationship = "unclear"
    if verified and identity == "same_study":
        relationship = "same_trial"
    elif (verified and identity == "distinct_randomizations"
          and reuse in {"not_indicated", "theoretical_only"}
          and "randomization" in domains
          and domains.intersection({"population", "recruitment", "baseline", "intervention", "explicit_linkage"})):
        relationship = "distinct_trials"
    # Positive reuse is never merged/selected automatically, even if identity is same.
    if reuse in {"documented", "conflicting_evidence"}:
        relationship = "unclear"
    return {"relationship": relationship, "independently_verified": bool(verified and relationship != "unclear"),
            "evidence_a": features[0]["evidence_a"] if features else "",
            "evidence_b": features[0]["evidence_b"] if features else "",
            "reason": proposal["reason"] if relationship != "unclear" else "Evidence-tier gate withheld comparison: " + proposal["reason"],
            "policy": POLICY, "evidence_tier_assessment": proposal, "verification": verification,
            "source_features_valid": valid_features,
            "residual_limitations": proposal["limitations"] + (["Theoretical reenrollment is not ruled out; separate randomizations are not proof of participant-level disjointness."] if reuse == "theoretical_only" else [])}


def adjudicate(rows, documents, call, max_pairs=64):
    links = []
    for index, (a, b) in enumerate(combinations(rows, 2)):
        link = {"report_a": a["record_id"], "report_b": b["record_id"], "relationship": "unclear",
                "independently_verified": False, "evidence_a": "", "evidence_b": "", "policy": POLICY}
        sa, sb = documents.get(a["record_id"]), documents.get(b["record_id"])
        if index >= max_pairs or not sa or not sb or len(sa) + len(sb) > 420_000:
            link["reason"] = "Pair budget or original source availability insufficient"
            links.append(link)
            continue
        context = "\nREPORT A:\n" + sa + "\nREPORT B:\n" + sb
        try:
            proposal = call(RULE + context, SCHEMA)
            for _ in range(2):
                if all(contains(sa, f["evidence_a"]) and contains(sb, f["evidence_b"]) for f in proposal["features"]):
                    break
                proposal = call(RULE + "\nRepair non-verbatim feature quotes without strengthening the conclusion. Preserve punctuation/reading order.\nPREVIOUS:\n" + json.dumps(proposal) + context, SCHEMA)
            verification = call(RULE + "\nIndependently verify every claimed feature and conclusion. Reject unsupported distinct randomizations, missed affirmative reuse, or insufficient identity evidence. Verify that randomization passages support separate randomized cohorts when combined with other features; merely finding the word randomized is insufficient.\nPROPOSAL:\n" + json.dumps(proposal) + context, VERIFY)
            link.update(decide(proposal, (sa, sb), verification))
        except Exception as error:
            link["reason"] = str(error)
        links.append(link)
    return links

"""Evidence-linked, agent-assisted methods-first benchmark preparation.

This checks declared method compatibility, not the truth of an agent's reading.
It never authorizes scientific execution or treats software defaults as evidence.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

POLICY = "benchmark_methods_first_v1"
SUPPORTED = {
    ("RR", "fixed", "mantel_haenszel", "normal", "none"): "binary_rr_mh_fixed_v1",
    ("MD", "fixed", "inverse_variance", "normal", "none"): "continuous_fixed",
    ("SMD", "fixed", "inverse_variance", "normal", "none"): "continuous_fixed",
    (
        "MD",
        "random",
        "inverse_variance",
        "normal",
        "dersimonian_laird",
    ): "continuous_random",
    (
        "SMD",
        "random",
        "inverse_variance",
        "normal",
        "dersimonian_laird",
    ): "continuous_random",
}
FIELDS = ("measure", "model", "weighting", "interval", "heterogeneity_estimator")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assess(manifest):
    if manifest.get("policy") != POLICY:
        raise ValueError("Unsupported qualification policy")
    if not manifest.get("candidate_id") or not manifest.get("declared_analysis"):
        raise ValueError("Candidate identity and complete declared scope required")
    if manifest.get("assessment_mode") != "agent_assisted_source_reading":
        raise ValueError("Explicit reading trust level required")
    sources = {}
    for item in manifest["sources"]:
        path = Path(item["path"])
        if sha(path) != item["sha256"]:
            raise ValueError("Source checksum differs")
        if item.get("role") != "original_review" or not item.get("url"):
            raise ValueError("Original review source provenance required")
        sources[item["id"]] = path.read_text()
    claims = manifest["method"]
    problems = []
    for name in FIELDS:
        claim = claims[name]
        if claim.get("basis") != "explicit_source":
            problems.append(
                {
                    "field": name,
                    "kind": "not_established",
                    "detail": "Software name/default or numerical agreement does not identify the published method",
                }
            )
            continue
        evidence = claim.get("evidence", [])
        if not evidence:
            raise ValueError("Explicit method claim needs evidence")
        for anchor in evidence:
            text = sources.get(anchor.get("source_id"), "")
            quote = anchor.get("quote", "")
            if not quote.strip() or quote not in text or not anchor.get("locator"):
                raise ValueError("Method quotation/locator is not source anchored")
    key = tuple(claims[name].get("value") for name in FIELDS)
    supported = SUPPORTED.get(key)
    if not supported:
        problems.append(
            {
                "field": "method_combination",
                "kind": "unsupported_or_unknown",
                "detail": dict(zip(FIELDS, key)),
            }
        )
    if manifest.get("design") != "independent_parallel_randomized":
        problems.append(
            {
                "field": "design",
                "kind": "unsupported_or_unknown",
                "detail": manifest.get("design"),
            }
        )
    permitted = not problems
    return {
        "policy": POLICY,
        "candidate_id": manifest["candidate_id"],
        "declared_analysis": manifest["declared_analysis"],
        "assessment_mode": manifest["assessment_mode"],
        "reading_independently_verified": False,
        "method_supported": permitted,
        "engine_policy": supported if permitted else None,
        "next_step": "qualify_complete_primary_set"
        if permitted
        else "resolve_method_evidence_or_close_candidate",
        "primary_retrieval_ready": permitted,
        "scientific_execution_authorized": False,
        "remaining_gates": [
            "complete contributor and potentially eligible report inventory",
            "original primary access and outcome-specific inputs",
            "allocation/family/arm/time/units/denominator/integrity checks",
            "separately frozen scientific execution contract",
        ],
        "problems": problems,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if not getattr(sys, "_asr_frozen_code", None):
        raise SystemExit("Use scripts.run_frozen.command for pinned qualification")
    result = assess(json.loads(args.manifest.read_text()))
    result.update(manifest_sha256=sha(args.manifest), code_sha256=sys._asr_frozen_code)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()

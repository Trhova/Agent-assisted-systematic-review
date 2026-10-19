"""Read-only, post-hoc development audit. Never imported by review extraction."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml

from scripts.benchmark_validity import semantic_agreement
from scripts.model_backend import atomic_json, digest


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def assessment(config, run_map):
    spec = yaml.safe_load(Path(config).read_text())
    cases = []
    for case in spec["cases"]:
        run = Path(run_map[case["id"]])
        protocol = yaml.safe_load(Path(case["protocol"]).read_text())
        reference = read(Path(case["reference"]))
        if (
            digest(protocol) != case["protocol_sha256"]
            or digest(reference) != case["reference_sha256"]
        ):
            raise ValueError("Frozen benchmark input changed")
        status = read(run / "status.json")
        if (
            status["status"] == "running"
            or status["protocol_sha256"] != case["protocol_sha256"]
        ):
            raise ValueError("Run is active or belongs to another protocol")
        if read(run / "protocol.json") != protocol:
            raise ValueError("Run protocol artifact differs from frozen definition")
        searches = read(run / "search.json", {}).get("records", [])
        supplemental = read(run / "search_supplement.json", [])
        original = {r["id"] for r in searches}
        retrieved = original | {r["id"] for r in supplemental}
        screening = {r["id"]: r for r in read(run / "screening.json", [])}
        extractions = {r["id"]: r for r in read(run / "extractions.json", [])}
        synthesis = read(run / "synthesis.json", {})
        observed = {r["record_id"] for r in synthesis.get("effects", [])}
        reference_ids = reference.get(
            "expected_review_record_ids", reference["expected_record_ids"]
        )
        records, actions = [], []
        for rid in reference_ids:
            screen, extraction = screening.get(rid, {}), extractions.get(rid, {})
            source = run / "sources" / rid / "text.json"
            result = extraction.get("result", {})
            row = {
                "record_id": rid,
                "reference_outcome_contributor": rid
                in reference["expected_record_ids"],
                "in_original_search": rid in original,
                "retrieved": rid in retrieved,
                "screening": screen,
                "source_present": source.exists(),
                "source_artifact": str(source) if source.exists() else None,
                "source_artifact_sha256": hashlib.sha256(
                    source.read_bytes()
                ).hexdigest()
                if source.exists()
                else None,
                "extraction_status": extraction.get("status"),
                "eligibility": result.get("eligibility"),
                "extraction_reason": result.get("reason"),
                "missing_numeric_evidence": result.get("missing", []),
                "pooled": rid in observed,
            }
            records.append(row)

            def action(kind, reason, next_step, record_id=rid, queue=actions):
                queue.append(
                    {
                        "record_id": record_id,
                        "category": kind,
                        "reason": reason,
                        "next_action": next_step,
                    }
                )

            if rid not in retrieved:
                action(
                    "search_coverage",
                    "Absent from original and supplemental searches",
                    "Audit indexed terminology and freeze a separate development query; do not insert reference answers into extraction",
                )
            elif (
                screen.get("decision") == "exclude"
                or result.get("eligibility") == "exclude"
            ):
                action(
                    "eligibility_difference",
                    result.get("reason") or screen.get("reason"),
                    "Adjudicate intervention/comparator against review methods; retain original exclusion",
                )
            elif not source.exists():
                action(
                    "source_access",
                    extraction.get("status", "no accepted full text"),
                    "Obtain lawful original report; retry only a newly evidenced access route",
                )
            elif rid not in observed and rid in reference["expected_record_ids"]:
                missing_text = " ".join(result.get("missing", []))
                category = (
                    "supported_derivation_extension"
                    if (
                        re.search(r"\bSE\b", missing_text)
                        and re.search(r"\bSDs?\b", missing_text)
                    )
                    else "numeric_or_estimand_adjudication"
                )
                action(
                    category,
                    "; ".join(result.get("missing", []))
                    or "No accepted independent effect",
                    "Separately specify SD=SE*sqrt(analyzed arm n), verify endpoint denominator and unadjusted arm-mean SE, retain original SE and source provenance; never copy forest SD columns"
                    if category == "supported_derivation_extension"
                    else "Inspect primary table and analyzed denominator; adjudicate separately from published forest values",
                )
        semantics = semantic_agreement(protocol, reference, synthesis)
        if not semantics["agrees"]:
            actions.append(
                {
                    "record_id": None,
                    "category": "comparison_contract",
                    "reason": semantics["issues"],
                    "next_action": "Create separately versioned source-backed contract for reference estimand; missing value_type is unknown, not established incompatibility",
                }
            )
        if not status.get("model"):
            actions.append(
                {
                    "record_id": None,
                    "category": "reproducibility",
                    "reason": "Historical model identity was not pinned",
                    "next_action": "Keep historical result; require explicit model on a fresh prospectively frozen evaluation",
                }
            )
        cases.append(
            {
                "id": case["id"],
                "classification": "post_hoc_development_audit",
                "ready_for_independent_validation": False,
                "validation_gate_reason": "Historical evaluated development runs cannot serve as fresh prospective validation, regardless of repaired coverage",
                "protocol_agreement": {
                    "status": "not_established",
                    "semantic_contract": semantics,
                    "limitations": [
                        "Single bibliographic database is not historical multidatabase search equivalence",
                        protocol.get(
                            "search_date_note",
                            "Frozen placebo-only definition differs from included dietary-advice control",
                        ),
                    ],
                },
                "records": records,
                "queue_scope": "Reference review reports plus case-level scientific contracts; not the complete retained-candidate queue",
                "reference_report_count": len(records),
                "reference_outcome_count": len(reference["expected_record_ids"]),
                "search_coverage": {
                    "original": sum(r["in_original_search"] for r in records),
                    "total": sum(r["retrieved"] for r in records),
                },
                "source_coverage": {
                    "present": sum(r["source_present"] for r in records),
                    "note": "Presence does not establish numeric usability or eligibility",
                },
                "numeric_correctness": {
                    "status": "not_independently_adjudicated",
                    "reference_contributors_pooled": len(
                        observed & set(reference["expected_record_ids"])
                    ),
                    "extra_contributors": sorted(
                        observed - set(reference["expected_record_ids"])
                    ),
                },
                "reproducibility": {
                    "model": status.get("model"),
                    "code_sha256": status.get("code_sha256"),
                    "pending_segments": status.get("pending_segments"),
                    "historical_status": status["status"],
                },
                "next_actions": actions,
                "action_count": len(actions),
                "input_artifact_hashes": {
                    str(run / n): hashlib.sha256((run / n).read_bytes()).hexdigest()
                    for n in (
                        "status.json",
                        "protocol.json",
                        "search.json",
                        "screening.json",
                        "extractions.json",
                        "synthesis.json",
                    )
                    if (run / n).exists()
                },
            }
        )
    return {
        "schema_version": 1,
        "classification": "post_hoc_development_readiness_not_validation",
        "cases": cases,
        "action_count": sum(c["action_count"] for c in cases),
        "ready_for_broad_validation_run": False,
        "scope": "Diagnostic of historical development artifacts, not a general prospective launch validator",
        "leakage_boundary": "Reference identities are evaluator-only. This audit and its actions must not be supplied to screening/extraction models in held-out evaluation.",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--suite", type=Path, default=Path("benchmarks/suite.yaml"))
    p.add_argument(
        "--run-map", type=Path, default=Path("benchmarks/findings/final_run_map.json")
    )
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    atomic_json(args.output, assessment(args.suite, read(args.run_map)))

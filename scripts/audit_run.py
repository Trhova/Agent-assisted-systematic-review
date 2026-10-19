"""Read-only artifact consistency and deterministic replay; not a clinical re-review."""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
from itertools import combinations
from pathlib import Path

from scripts.meta_analysis import synthesize
from scripts.model_backend import atomic_json, digest
from scripts.trial_families import resolve


def same(a, b):
    """Permit only floating-point roundoff, never missing or extra fields."""
    if type(a) in (int, float) and type(b) in (int, float):
        return (
            math.isfinite(a)
            and math.isfinite(b)
            and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
        )
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def audit(work):
    from scripts.autonomous_review import unresolved_extraction, validate_evidence

    work = Path(work)
    issues, fingerprints, sources = [], {}, {}
    report = {
        "policy": "artifact_consistency_v1",
        "run": str(work),
        "valid": False,
        "issues": issues,
        "artifact_sha256": fingerprints,
        "limitations": [
            "Internal consistency and deterministic replay do not independently establish the scientific truth of model decisions.",
            "Hashes detect inconsistent artifacts; this is not a signed attestation against coordinated alteration.",
            "Replay uses the current audited implementation; historical method changes can require separate evaluation.",
        ],
    }

    def read(name):
        value = json.loads((work / name).read_text())
        fingerprints[str(name)] = digest(value)
        return value

    def check(ok, issue):
        if not ok:
            issues.append(issue)

    def ids(items):
        values = [str(r["id"]) for r in items]
        check(len(values) == len(set(values)), "duplicate_record_decisions")
        return set(values)

    def source(rid):
        # Record identities are path components, never filesystem paths.
        if not isinstance(rid, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]*", rid
        ):
            raise ValueError("Unsafe source record identity")
        if rid not in sources:
            document = read(Path("sources") / rid / "text.json")
            check(digest(document["text"]) == document["sha256"], f"source_hash:{rid}")
            sources[rid] = document
        return sources[rid]

    try:
        status, protocol = read("status.json"), read("protocol.json")
        report.update(
            run_status=status["status"],
            model=status.get("model"),
            backend=status.get("backend"),
            code_sha256=status.get("code_sha256"),
        )
        check(status["status"] != "running", "active_run")
        check(digest(protocol) == status["protocol_sha256"], "protocol_hash")
        code = status["code_sha256"]
        if not isinstance(code, str) or not re.fullmatch(r"[a-f0-9]{64}", code):
            raise ValueError("Invalid code snapshot identity")
        check(
            digest(read(Path("code_snapshots") / (code + ".json"))) == code,
            "code_snapshot_hash",
        )
        accepted, extracted = read("accepted.json"), read("extractions.json")
        families, links = read("trial_families.json"), read("family_links.json")
        screening = read("screening.json")
        search_result = read("search.json")
        search = search_result["records"]
        check(search_result["query"] == protocol["query"], "search_query_mismatch")
        check(len(search) >= search_result["hit_count"], "incomplete_search_retrieval")
        supplement = (
            read("search_supplement.json")
            if (work / "search_supplement.json").exists()
            else []
        )
        if protocol.get("bibliographic_supplement"):
            leads = read("frozen_bibliographic_supplement.json")
            check(
                digest(leads) == protocol["bibliographic_supplement"]["sha256"],
                "frozen_supplement_hash",
            )
            check(
                all(row in supplement for row in leads),
                "frozen_supplement_missing_from_search",
            )
        search_ids = ids(search) | ids(supplement)
        screened_ids, extracted_ids = ids(screening), ids(extracted)
        check(screened_ids <= search_ids, "screened_record_absent_from_search")
        candidates = {r["id"] for r in screening if r["decision"] != "exclude"}
        check(extracted_ids <= candidates, "extraction_without_screening_candidate")
        for item in extracted:
            if item.get("status") == "extracted":
                document = source(item["id"])
                check(
                    item.get("source_sha256") == document["sha256"],
                    f"extraction_source_hash:{item['id']}",
                )
        extracted_rows = [
            r
            for x in extracted
            if x.get("status") == "extracted"
            and x.get("result", {}).get("eligibility") == "include"
            for r in x["result"]["rows"]
            if r.get("validation_errors") == []
        ]
        check(same(accepted, extracted_rows), "accepted_extraction_rows_differ")
        for row in accepted:
            rid = row["record_id"]
            document = source(rid)
            check(row.get("validation_errors") == [], f"unvalidated_row:{rid}")
            check(row["source_sha256"] == document["sha256"], f"row_source_hash:{rid}")
            for error in validate_evidence(row, document["text"], protocol):
                issues.append(f"evidence:{rid}:{error}")
            # Replay supported transformations from preserved original arm inputs.
            original = copy.deepcopy(row)
            original["unit"] = row.get("reported_unit", row["unit"])
            for policy, key in (
                ("summary_policy", "summary_audit"),
                ("dispersion_policy", "dispersion_audit"),
            ):
                check(
                    not protocol.get(policy) or bool(row.get(key)),
                    f"missing_transformation_audit:{rid}:{key}",
                )
            for key, module in (
                ("summary_audit", "summary_derivations"),
                ("dispersion_audit", "continuous_derivations"),
            ):
                if key not in row:
                    continue
                from importlib import import_module

                for item in row[key]:
                    arm = item["arm"]
                    if key == "summary_audit":
                        for name, value in item["original_statistics"].items():
                            original[name + "_" + arm] = value
                    elif item["original_type"] == "SE":
                        original["sd_" + arm] = None
                derived = import_module("scripts." + module).derive(
                    original, document["text"], protocol, document["sha256"]
                )
                check(same(derived[key], row[key]), f"transformation_audit:{rid}")
                for arm in ("treatment", "control"):
                    for stat in ("mean", "sd"):
                        field = stat + "_" + arm
                        check(
                            same(derived[field], row[field]),
                            f"transformation_value:{rid}:{field}",
                        )
        from scripts.family_adjudication import contains

        expected_pairs = {
            frozenset((a["record_id"], b["record_id"]))
            for a, b in combinations(accepted, 2)
        }
        actual_pairs = [
            frozenset((link["report_a"], link["report_b"])) for link in links
        ]
        check(
            set(actual_pairs) == expected_pairs
            and len(actual_pairs) == len(expected_pairs),
            "family_pair_coverage",
        )
        for link in links:
            if protocol.get("family_policy") == "family_evidence_tiers_v2":
                from scripts.family_evidence_tiers import decide

                check(link.get("policy") == "family_evidence_tiers_v2", "family_policy_mismatch")
                if link.get("evidence_tier_assessment"):
                    replay = decide(link["evidence_tier_assessment"],
                                    (source(link["report_a"])["text"], source(link["report_b"])["text"]),
                                    link.get("verification", {}))
                    check(all(same(link.get(k), v) for k, v in replay.items()), "family_evidence_tier_replay")
                else:
                    check(link["relationship"] == "unclear", "missing_family_evidence_tier")
            if link["relationship"] != "unclear":
                for suffix in ("a", "b"):
                    check(
                        contains(
                            source(link["report_" + suffix])["text"],
                            link["evidence_" + suffix],
                        ),
                        "family_link_source_evidence",
                    )
        replay_families = resolve(accepted, links)
        check(same(families, replay_families), "family_resolution_replay")
        rows = replay_families["rows"]
        counts = status["counts"]
        observed = {
            "screened": len(screening),
            "fulltexts_attempted": len(extracted),
            "accepted_effects": len(accepted),
            "independent_effects": len(rows),
            "abstract_candidates": len(candidates),
            "unresolved": sum(unresolved_extraction(x) for x in extracted),
        }
        report["observed_counts"] = observed
        for key, value in observed.items():
            check(counts.get(key) == value, "status_count:" + key)
        complete = (
            screened_ids == search_ids
            and extracted_ids == candidates
            and not observed["unresolved"]
            and not status["errors"]
            and not families["unresolved"]
            and not status.get("pending_segments", 0)
            and len(rows) >= 2
            and not any(
                "Limited pilot:" in note for note in status.get("limitations", [])
            )
        )
        report["completion_supported"] = complete
        check(status["status"] != "complete" or complete, "unsupported_complete_status")
        if len(rows) >= 2:
            replay = synthesize(
                rows,
                protocol["measure"],
                protocol["model"],
                value_type_policy=protocol.get("value_type"),
            )
            stored = read("synthesis.json")
            check(same(stored, replay), "synthesis_replay")
            report["replayed_synthesis"] = {
                k: replay[k]
                for k in ("k", "estimate", "ci_low", "ci_high", "I2", "tau2")
            }
        else:
            check(
                not (work / "synthesis.json").exists(),
                "synthesis_with_insufficient_independent_rows",
            )
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        issues.append(f"artifact_error:{type(error).__name__}:{error}")
    report["valid"] = not issues
    report["auditor_sha256"] = digest(
        {p.name: p.read_text() for p in Path(__file__).parent.glob("*.py")}
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.run)
    if args.output:
        if args.output.resolve().is_relative_to(args.run.resolve()):
            parser.error("Audit output must be outside the preserved run")
        atomic_json(args.output, result)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 2)

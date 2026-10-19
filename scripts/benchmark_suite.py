"""Run frozen review protocols, then compare references in a separate evaluation phase."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
import time
from pathlib import Path

import yaml

from scripts.autonomous_review import compare
from scripts.model_backend import atomic_json, digest
from scripts.report_review import export


def validate_evaluation_pin(case):
    """Check evaluator assets before costly execution; never pass them to reviewers."""
    if "evaluation_contract" in case:
        from scripts.evaluate_contract import sha
        if sha(Path(case["evaluation_contract"])) != case.get("evaluation_contract_sha256"):
            raise ValueError("Frozen evaluation contract checksum differs")
    elif digest(json.loads(Path(case["reference"]).read_text())) != case["reference_sha256"]:
        raise ValueError("Frozen reference checksum differs")


def evaluate(case, run):
    if "evaluation_contract" in case:
        from scripts.evaluate_contract import evaluate as evaluate_inputs
        from scripts.evaluate_contract import sha
        contract = Path(case["evaluation_contract"])
        if sha(contract) != case.get("evaluation_contract_sha256"):
            raise ValueError("Frozen evaluation contract checksum differs")
        status = json.loads((run / "status.json").read_text())
        if status.get("protocol_sha256") != case["protocol_sha256"]:
            raise ValueError("Observed run does not match frozen protocol")
        result = evaluate_inputs(run, contract)
        return {"id": case["id"], "run": str(run), "comparison": result,
                "run_status": json.loads((run / "status.json").read_text())["status"],
                "reproduced": result["scoped_reproduction"]}
    status = json.loads((run / "status.json").read_text())
    if status.get("status") == "running":
        raise ValueError("Cannot evaluate an active review")
    if status.get("protocol_sha256") != case["protocol_sha256"]:
        raise ValueError("Observed run does not match frozen protocol")
    # Numerical comparison occurs only after scientific execution; pins are preflighted.
    reference = Path(case["reference"])
    if digest(json.loads(reference.read_text())) != case["reference_sha256"]:
        raise ValueError("Frozen reference checksum differs")
    with contextlib.redirect_stdout(io.StringIO()):
        compare(run, reference)
    export(run)
    comparison = json.loads((run / "benchmark_comparison.json").read_text())
    return {
        "id": case["id"],
        "run": str(run),
        "run_status": status["status"],
        "counts": status.get("counts", {}),
        "code_sha256": status.get("code_sha256"),
        "comparison": comparison,
        "reproduced": comparison["reproduced"],
    }


def suite(config, workdir, *, existing=None, backend="codex", model=None, max_rounds=8):
    if existing is None and (not isinstance(model, str) or not model.strip()):
        raise ValueError(
            "New benchmark execution requires an explicit nonempty model identity"
        )
    config, workdir = Path(config), Path(workdir)
    specification = yaml.safe_load(config.read_text())
    if existing is None:
        for key, actual in (
            ("prespecified_model", model),
            ("prespecified_backend", backend),
        ):
            if specification.get(key) is not None and specification[key] != actual:
                raise ValueError(
                    f"Execution differs from {key}; use a separately specified suite"
                )
    frozen_root = expected_code = None
    if existing is None:
        from scripts.run_frozen import bundle

        frozen_root, expected_code = bundle(
            Path(__file__).parent, Path("data/benchmarks/code_bundles")
        )
        if (
            specification.get("prespecified_code_sha256", expected_code)
            != expected_code
        ):
            raise ValueError("Execution differs from prespecified code checksum")
    cases = specification["cases"]
    if len({c["id"] for c in cases}) != len(cases) or not cases:
        raise ValueError("Benchmark suite must contain unique nonempty cases")
    if existing is not None and set(existing) != {c["id"] for c in cases}:
        raise ValueError("Existing run map must cover exactly the frozen cases")
    attempt = workdir / "suite_attempts" / str(time.time_ns())
    attempt.mkdir(parents=True)
    results = []
    for case in cases:
        try:
            protocol = yaml.safe_load(Path(case["protocol"]).read_text())
            if (
                protocol["id"] != case["id"]
                or digest(protocol) != case["protocol_sha256"]
            ):
                raise ValueError("Frozen protocol identity/checksum differs")
            validate_evaluation_pin(case)
            run = (
                Path(existing[case["id"]])
                if existing is not None
                else workdir / case["id"] / case["protocol_sha256"][:12]
            )
            exit_code = None
            if existing is None:
                from scripts.run_frozen import command as frozen_command

                command = frozen_command(
                    frozen_root,
                    expected_code,
                    "scripts.autonomous_review",
                    [
                        "run",
                        "--protocol",
                        case["protocol"],
                        "--workdir",
                        str(workdir),
                        "--backend",
                        backend,
                        "--max-rounds",
                        str(max_rounds),
                    ],
                )
                if model:
                    command += ["--model", model]
                previous_status_time = (
                    (run / "status.json").stat().st_mtime_ns
                    if (run / "status.json").exists()
                    else None
                )
                with (attempt / (case["id"] + ".log")).open("w") as log:
                    exit_code = subprocess.run(
                        command, stdout=log, stderr=subprocess.STDOUT, check=False
                    ).returncode
                if (
                    not (run / "status.json").exists()
                    or (run / "status.json").stat().st_mtime_ns == previous_status_time
                ):
                    raise RuntimeError(
                        "Review process did not write a fresh status; stale results were not evaluated"
                    )
                if exit_code not in (0, 2):
                    raise RuntimeError(
                        f"Review process exited {exit_code}; inspect preserved log"
                    )
            if existing is None:
                observed_code = json.loads((run / "status.json").read_text()).get(
                    "code_sha256"
                )
                if observed_code != expected_code:
                    raise RuntimeError(
                        "Review child code checksum differs; downstream evaluation withheld"
                    )
                from scripts.rob2_draft import assess_run

                assess_run(run, backend=backend, model=model)
            item = evaluate(case, run)
            if (run / "rob2_draft.json").exists():
                risk = json.loads((run / "rob2_draft.json").read_text())
                item["risk_of_bias_drafts"] = {
                    k: risk[k] for k in ("source_checked", "unverified", "limitations")
                }
            item["execution_exit_code"] = exit_code
            item["evaluation_only"] = existing is not None
        except Exception as error:  # noqa: BLE001 - preserve per-case failure receipts
            item = {"id": case["id"], "reproduced": False, "error": str(error)}
        results.append(item)
        atomic_json(attempt / "progress.json", {"cases": results})
    report = {
        "suite": specification["id"],
        "suite_sha256": digest(specification),
        "status": "reproduced"
        if all(r["reproduced"] for r in results)
        else "not_reproduced",
        "evaluation_only": existing is not None,
        "cases": results,
        "note": "Unit tests, cached development execution and secondary forest-plot calibration are not successful independent reproduction. Incomplete reviews cannot pass.",
    }
    atomic_json(attempt / "report.json", report)
    atomic_json(workdir / "suite_report.json", report)
    lines = [
        "# Frozen meta-analysis benchmark suite",
        "",
        "Status: **" + report["status"] + "**",
        "",
        "| Review | Run status | Screened | Effects | Unresolved | Reproduced |",
        "|---|---|---:|---:|---:|---|",
    ]
    for item in results:
        counts = item.get("counts", {})
        lines.append(
            f"| {item['id']} | {item.get('run_status', 'evaluation error')} | {counts.get('screened', '—')} | {counts.get('independent_effects', '—')} | {counts.get('unresolved', '—')} | {item['reproduced']} |"
        )
    lines += [
        "",
        report["note"],
        "",
        "Full source provenance, errors, code hashes and reference comparisons are in `suite_report.json` and each run's `review_export/`.",
    ]
    (workdir / "suite_report.md").write_text("\n".join(lines) + "\n")
    return report


if __name__ == "__main__":
    # Freeze the entire CLI, including subsequent RoB and evaluator imports.
    if not getattr(sys, "_asr_frozen_code", None):
        from scripts.run_frozen import bundle, command

        root, identity = bundle(
            Path(__file__).parent, Path("data/benchmarks/code_bundles")
        )
        raise SystemExit(
            subprocess.run(
                command(root, identity, "scripts.benchmark_suite", sys.argv[1:]),
                check=False,
            ).returncode
        )
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, default=Path("benchmarks/suite.yaml"))
    parser.add_argument("--workdir", type=Path, default=Path("data/benchmarks/suite"))
    parser.add_argument(
        "--existing-runs",
        type=Path,
        help="Evaluate a JSON map of case IDs to finished run directories, without running models",
    )
    parser.add_argument("--backend", choices=["codex", "openai"], default="codex")
    parser.add_argument("--model")
    parser.add_argument("--max-rounds", type=int, default=8)
    args = parser.parse_args()
    if args.max_rounds < 1:
        parser.error("max-rounds must be positive")
    report = suite(
        args.suite,
        args.workdir,
        existing=json.loads(args.existing_runs.read_text())
        if args.existing_runs
        else None,
        backend=args.backend,
        model=args.model,
        max_rounds=args.max_rounds,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "cases": len(report["cases"]),
                "report": str(args.workdir / "suite_report.md"),
            }
        )
    )
    raise SystemExit(0 if report["status"] == "reproduced" else 2)

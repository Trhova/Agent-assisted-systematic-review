"""Execute repeatable read-only development audits and isolated corruption checks."""

import argparse
import contextlib
import io
import json
import shutil
from pathlib import Path

from scripts.audit_run import audit
from scripts.autonomous_review import compare
from scripts.model_backend import atomic_json, digest


def execute(config, output):
    specification = json.loads(Path(config).read_text())
    output = Path(output)
    # A fresh directory preserves every earlier observation, including failures.
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "specification_sha256": digest(specification),
        "cases": {},
        "corruptions": {},
        "model_execution": False,
    }
    for name, path in specification["cases"].items():
        result = audit(path)
        report["cases"][name] = result
        atomic_json(output / (name + ".json"), result)
    parent = specification["corruption_parent"]
    original = Path(specification["cases"][parent])
    baseline = report["cases"][parent]
    if not baseline["valid"]:
        raise ValueError(
            "Corruption experiment requires an internally consistent baseline"
        )
    for kind in specification["corruptions"]:
        run = output / "corruptions" / kind
        for relative in baseline["artifact_sha256"]:
            target = run / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original / relative, target)
        if kind == "synthesis_estimate":
            filename, field = "synthesis.json", "estimate"
            data = json.loads((run / filename).read_text())
            data[field] += 0.01
        elif kind == "source_text":
            filename = next(
                p for p in baseline["artifact_sha256"] if p.startswith("sources/")
            )
            data = json.loads((run / filename).read_text())
            data["text"] += "\nAltered after extraction."
        elif kind == "family_rows":
            filename = "trial_families.json"
            data = json.loads((run / filename).read_text())
            data["rows"][0]["n_treatment"] += 1
        elif kind == "false_completion":
            filename = "status.json"
            data = json.loads((run / filename).read_text())
            data["status"] = "complete"
        elif kind == "quartile_derivation":
            filename = "accepted.json"
            data = json.loads((run / filename).read_text())
            row = next(
                r
                for r in data
                if any(a["estimated"] for a in r.get("summary_audit", []))
            )
            row["summary_audit"][0]["derived_sd"] += 1
        else:
            raise ValueError("Unspecified corruption")
        atomic_json(run / filename, data)
        result = audit(run)
        with contextlib.redirect_stdout(io.StringIO()):
            compare(run, Path(specification["reference"]))
        comparison = json.loads((run / "benchmark_comparison.json").read_text())
        report["corruptions"][kind] = {
            "audit": result,
            "reproduced": comparison["reproduced"],
            "numerically_matches": comparison.get("numerically_matches"),
        }
    report["originals_unchanged"] = all(
        audit(specification["cases"][name])["artifact_sha256"]
        == result["artifact_sha256"]
        for name, result in report["cases"].items()
    )
    report["passed"] = (
        all(r["valid"] for r in report["cases"].values())
        and all(
            not r["audit"]["valid"] and not r["reproduced"]
            for r in report["corruptions"].values()
        )
        and report["originals_unchanged"]
    )
    atomic_json(output / "report.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.config, args.output)
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "cases": len(result["cases"]),
                "corruptions": len(result["corruptions"]),
                "originals_unchanged": result["originals_unchanged"],
            }
        )
    )
    raise SystemExit(0 if result["passed"] else 2)

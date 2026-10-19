"""Replay an order-dependent family conflict against two immutable code bundles.

Synthetic integration counterexample, motivated by primary-source subgroup
reporting found during Zheng2023 qualification. This is not a clinical pool.
Run: .venv/bin/python -m benchmarks.audits.family_link_order_v1
"""
import importlib.util
import itertools
import json
from pathlib import Path


def main():
    output = Path("data/benchmarks/family_link_order_v1")
    output.mkdir(parents=True, exist_ok=False)
    versions = {
        "before": "6ca781dc3ed77318e5d719baa70217e688acedd54ed4cb7ff83be2ea743e7081",
        "after": "c605db2e4c1794930779a6130f6f14a534b81207b51e05f753446512b2b8de83",
    }
    rows = [{"record_id": x, "study_id": x, "mean_treatment": 1,
             "outcome": "synthetic"} for x in "abc"]
    links = [
        dict(report_a=a, report_b=b, relationship=relationship,
             evidence_a="Synthetic verified quotation A",
             evidence_b="Synthetic verified quotation B", independently_verified=True)
        for a, b, relationship in [("a", "c", "distinct_trials"),
                                    ("a", "b", "same_trial"),
                                    ("b", "c", "same_trial")]
    ]
    receipt = {"kind": "synthetic integration counterexample, not clinical validation",
               "code_snapshots": versions, "runs": {}}
    for version, identity in versions.items():
        path = Path("data/benchmarks/code_bundles") / identity / "scripts/trial_families.py"
        spec = importlib.util.spec_from_file_location(version, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        results = []
        for order in itertools.permutations(range(3)):
            result = module.resolve(rows, [links[i] for i in order])
            results.append({"order": order, "result": result})
        receipt["runs"][version] = results
    receipt["accepted_conflicting_orders"] = {
        version: sum(bool(r["result"]["rows"]) for r in results)
        for version, results in receipt["runs"].items()
    }
    (output / "results.json").write_text(json.dumps(receipt, indent=2) + "\n")
    assert receipt["accepted_conflicting_orders"] == {"before": 4, "after": 0}
    print(json.dumps(receipt["accepted_conflicting_orders"]))


if __name__ == "__main__":
    main()

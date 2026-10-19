"""Secondary-source numerical check; never an autonomous reproduction benchmark."""

import argparse
import json
from pathlib import Path

from scripts.meta_analysis import synthesize
from scripts.model_backend import atomic_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fixture = json.loads(args.forest.read_text())
    rows = [
        {
            **r,
            "outcome": "published_figure",
            "unit": fixture.get("unit", "source units"),
            "value_type": "endpoint",
        }
        for r in fixture["rows"]
    ]
    result = synthesize(rows, fixture["measure"], fixture["model"])
    result["evidence_level"] = fixture["evidence_level"]
    result["source"] = fixture["source"]
    atomic_json(args.output, result)
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("evidence_level", "estimate", "ci_low", "ci_high", "I2", "k")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

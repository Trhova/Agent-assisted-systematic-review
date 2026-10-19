"""Link derivative reports without discarding their unresolved information."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts.model_backend import atomic_json, digest
from scripts.report_type_evidence import annotation


def norm(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def validate_link(assessment, primary):
    if assessment["proposal"]["classification"] != "secondary_synopsis":
        raise ValueError("Explicit secondary synopsis required")
    title = norm(primary["title"])
    if len(title) < 30 or title not in norm(
        assessment["proposal"]["primary_report_link_quote"]
    ):
        raise ValueError("Linked original report title not established")


def link(config, output):
    config = json.loads(Path(config).read_text())
    if config.get("policy") != "secondary_report_linkage_v1":
        raise ValueError("Unsupported linkage policy")
    output = Path(output)
    if output.exists():
        raise ValueError("Use isolated new output")
    run = Path(config["source_run"])
    for name, expected in config["input_sha256"].items():
        if digest(json.loads((run / name).read_text())) != expected:
            raise ValueError("Frozen review input differs")
    records = {
        r["id"]: r for r in json.loads((run / "search.json").read_text())["records"]
    }
    accepted = json.loads((run / "trial_families.json").read_text())["rows"]
    primary_id = config["primary_record_id"]
    if primary_id not in {r["record_id"] for r in accepted}:
        raise ValueError("Linked primary is not a retained independent input")
    directory = Path(config["assessment_directory"])
    note = annotation(directory)
    assessment = json.loads((directory / "assessment.json").read_text())
    if digest(assessment) != config["assessment_sha256"]:
        raise ValueError("Frozen role assessment differs")
    if note["record_id"] not in records or note["record_id"] == primary_id:
        raise ValueError("Secondary identity absent or self-linked")
    validate_link(assessment, records[primary_id])
    report = {
        "policy": config["policy"],
        "secondary_record_id": note["record_id"],
        "primary_record_id": primary_id,
        "relation": "editorial_synopsis_of",
        "evidence": note,
        "secondary_report_retained": True,
        "fulltext_access_resolved": False,
        "eligibility_changed": False,
        "completion_changed": False,
        "synthesis_changed": False,
        "limitation": "Bibliographic linkage is not proof the inaccessible secondary text contains no additional information. Other unlinked reports are not necessarily independent missing studies.",
    }
    from scripts.outcome_availability import build

    missing = {
        r["record_id"]
        for r in build(run)["records"]
        if r["category"] == "missing_fulltext_access"
    }
    linked_missing = missing & {note["record_id"]}
    report["report_access_counts"] = {
        "unresolved_fulltext_reports": len(missing),
        "unresolved_linked_secondary_reports": len(linked_missing),
        "unresolved_unlinked_reports": len(missing - linked_missing),
        "missing_independent_studies": None,
    }
    output.mkdir(parents=True)
    atomic_json(output / "config.json", config)
    atomic_json(output / "linkage.json", report)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    print(json.dumps(link(a.config, a.output), indent=2))

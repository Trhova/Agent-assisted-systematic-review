"""Human-readable audit export from actual run artifacts; no model inference."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from scripts.model_backend import atomic_json


def read(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def export(work, output=None):
    work = Path(work)
    output = Path(output) if output else work / "review_export"
    output.mkdir(parents=True, exist_ok=True)
    status = read(work / "status.json", {})
    if status.get("status") == "running":
        raise ValueError("Final audit export requires a finished run")
    from scripts.outcome_availability import build as availability_report

    availability = availability_report(work)
    atomic_json(output / "availability.json", availability)
    atomic_json(output / "continuation_queue.json", availability["continuation_queue"])
    records = {
        r["id"]: r for r in read(work / "search.json", {"records": []})["records"]
    }
    records.update({r["id"]: r for r in read(work / "search_supplement.json", [])})
    screening = {r["id"]: r for r in read(work / "screening.json", [])}
    extraction = {r["id"]: r for r in read(work / "extractions.json", [])}
    accepted = read(work / "accepted.json", [])
    families = read(work / "trial_families.json", {"rows": accepted, "unresolved": []})
    independent = {r["record_id"]: r for r in families["rows"]}
    risk_report = read(work / "rob2_draft.json", {})
    risk_by_record = {r["record_id"]: r for r in risk_report.get("assessments", [])}
    headers = [
        "record_id",
        "title",
        "abstract_decision",
        "abstract_reason",
        "fulltext_status",
        "eligibility",
        "fulltext_reason",
        "numeric_status",
        "rob2_draft_status",
        "rob2_draft_overall",
        "publication_integrity_flags",
        "missing",
        "validation_errors",
        "retrieval_details",
        "public_copy_search",
        "source_format",
        "source_acquisition_method",
        "raw_pdf_sha256",
        "raw_html_sha256",
        "supplement_status",
        "source_url",
        "source_sha256",
    ]
    with (output / "decisions.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for rid, r in records.items():
            s = screening.get(rid, {})
            x = extraction.get(rid, {})
            result = x.get("result", {})
            source_folder = work / "sources" / rid
            source = read(source_folder / "text.json", {})
            unavailable = read(source_folder / "unavailable.json", {})
            discovery = read(source_folder / "discovery.json", {})
            web = read(source_folder / "web_discovery.json", {})
            failures = [str(e) for e in unavailable.get("errors", [])]
            failures += [e.get("error", "") for e in discovery.get("errors", [])]
            for journal in [
                discovery,
                read(source_folder / "web_candidate_downloads" / "discovery.json", {}),
            ]:
                failures += [
                    c.get("error", c.get("status", ""))
                    for c in journal.get("candidates", [])
                    if c.get("status") not in {"accepted", "accepted_html"}
                ]
            row = {
                "record_id": rid,
                "title": r["title"],
                "abstract_decision": s.get("decision", "not_screened"),
                "abstract_reason": s.get("reason", ""),
                "fulltext_status": x.get("status", "not_requested"),
                "eligibility": result.get("eligibility", ""),
                "fulltext_reason": result.get("reason", ""),
                "numeric_status": "independent_effect"
                if rid in independent
                else "not_pooled",
                "publication_integrity_flags": "; ".join(
                    x.get("publication_integrity_flags", [])
                ),
                "missing": "; ".join(result.get("missing", [])),
                "validation_errors": "; ".join(
                    e
                    for rr in result.get("rows", [])
                    for e in rr.get("validation_errors", [])
                ),
                "retrieval_details": "; ".join(dict.fromkeys(failures)),
                "public_copy_search": web.get("reason", ""),
                "rob2_draft_status": risk_by_record.get(rid, {}).get("status", ""),
                "rob2_draft_overall": risk_by_record.get(rid, {})
                .get("assessment", {})
                .get("overall_risk_of_bias", {})
                .get("judgment", ""),
                "source_format": source.get("format", ""),
                "source_acquisition_method": source.get("acquisition_method", ""),
                "raw_pdf_sha256": source.get("pdf_sha256", ""),
                "raw_html_sha256": source.get("html_sha256", ""),
                "supplement_status": json.dumps(
                    source.get("supplements", {}).get("attachments", [])
                ),
                "source_url": source.get("url", ""),
                "source_sha256": source.get("sha256", ""),
            }
            # Keep imported titles/reasons as spreadsheet text, not formulas.
            writer.writerow(
                {
                    k: (
                        "'" + v
                        if isinstance(v, str) and v.startswith(("=", "+", "-", "@"))
                        else v
                    )
                    for k, v in row.items()
                }
            )
    full_counts = Counter(x.get("status") for x in extraction.values())
    eligible_counts = Counter(
        x.get("result", {}).get("eligibility", "unresolved")
        for x in extraction.values()
    )
    lines = [
        "# Review execution audit",
        "",
        f"Evidence status: **{status.get('status', 'unknown')}**.",
        "An incomplete evidence set is not a completed review or clinical conclusion.",
        "",
        f"Protocol hash: `{status.get('protocol_sha256', 'unknown')}`",
        f"Code hash: `{status.get('code_sha256', 'unknown')}`",
        "",
        "## Report flow",
        "",
        f"- Bibliographic records: {len(records)}",
        f"- Abstract exclusions: {sum(s.get('decision') == 'exclude' for s in screening.values())}",
        f"- Full-text attempts: {len(extraction)}",
        f"- Full-text status: {dict(full_counts)}",
        f"- Eligibility decisions: {dict(eligible_counts)}",
        f"- Independently usable comparisons: {len(families['rows'])}",
        "",
        "Counts refer to reports until trial-family adjudication establishes participant independence.",
        "",
        "## Usable comparisons",
        "",
        "| Report | Trial identity | Outcome | Analyzed N, treatment/control | Binary events, treatment/control |",
        "|---|---|---|---|---|",
    ]
    for r in families["rows"]:
        lines.append(
            f"| {cell(r['record_id'])} | {cell(r['study_id'])} | {cell(r['outcome'])} | {r['n_treatment']}/{r['n_control']} | {r.get('events_treatment', '—')}/{r.get('events_control', '—')} |"
        )
    syn = read(work / "synthesis.json", None)
    if syn:
        lines += [
            "",
            "## Provisional synthesis"
            if status.get("status") != "complete"
            else "## Synthesis",
            "",
            f"{syn.get('measure', '')} {syn['model']} model, k={syn['k']}: {syn['estimate']:.6g}, 95% CI [{syn['ci_low']:.6g}, {syn['ci_high']:.6g}].",
            f"I²={syn['I2']:.3g}%; τ²={syn['tau2']:.6g}. Estimator and individual effects remain in `synthesis.json`.",
        ]
    else:
        lines += ["", "No valid pooled estimate is available."]
    estimated = [r for r in families["rows"] if any(a.get("estimated") for a in r.get("summary_audit", []))]
    if estimated:
        lines += ["", "## Estimated arm summaries", "",
                  "The following comparisons use estimated means/SDs from reported quartiles: " + ", ".join(cell(r["record_id"]) for r in estimated) + ".",
                  "They assume an approximately normal distribution. Conventional sampling variances omit summary-estimation uncertainty. Original quartiles, analyzed n, method and source evidence remain in each row's summary_audit."]
    sensitivity = read(work / "reported_statistics_sensitivity.json", None)
    if sensitivity:
        lines += ["", "## Reported-statistics-only sensitivity", "", sensitivity["note"]]
        ss = sensitivity.get("synthesis")
        lines += ([f"k={ss['k']}: {ss['estimate']:.6g}, 95% CI [{ss['ci_low']:.6g}, {ss['ci_high']:.6g}]."]
                  if ss else ["Fewer than two reported-statistics comparisons; no sensitivity pool."])
    lines += [
        "",
        "## Evidence gaps",
        "",
        "See `decisions.csv` for every exclusion, missing source, unavailable measurement and failed validation.",
        "See `availability.json` for source-linked uncertainty categories and accepted limitations; `continuation_queue.json` suggests next evidence checks without changing decisions.",
        f"Unresolved participant-dependence issues: {len(families['unresolved'])}.",
        "Source documents, raw model responses and run attempts remain in the run directory; this report does not replace those artifacts.",
    ]
    if risk_report:
        lines += [
            "",
            "## Automated risk-of-bias drafts",
            "",
            "These outcome-specific drafts use the project's abbreviated RoB2 template. Source checks and model agreement are not expert validation. Ratings do not change the pooled effects or benchmark comparisons.",
            "",
            "| Report | Outcome/timepoint | Draft overall | Source-check status |",
            "|---|---|---|---|",
        ]
        for r in risk_report.get("assessments", []):
            judgment = (
                r.get("assessment", {})
                .get("overall_risk_of_bias", {})
                .get("judgment", "Unavailable")
            )
            lines.append(
                f"| {cell(r['record_id'])} | {cell(r['outcome'])}, {cell(r['timepoint'])} | {cell(judgment)} | {cell(r['status'])} |"
            )
        lines += [
            "",
            "Complete signaling answers, evidence, failed checks and limitations are in `rob2_draft.json`.",
        ]
    (output / "review.md").write_text("\n".join(lines) + "\n")
    names = [
        "protocol.json",
        "status.json",
        "search.json",
        "search_supplement.json",
        "screening.json",
        "extractions.json",
        "accepted.json",
        "trial_families.json",
        "family_links.json",
        "synthesis.json",
        "reported_statistics_sensitivity.json",
        "frozen_bibliographic_supplement.json",
        "rob2_draft.json",
    ]
    atomic_json(
        output / "manifest.json",
        {
            "source_run": str(work.resolve()),
            "exporter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "files": {
                name: hashlib.sha256((work / name).read_bytes()).hexdigest()
                for name in names
                if (work / name).exists()
            },
        },
    )
    return output


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    print(export(a.run, a.output))

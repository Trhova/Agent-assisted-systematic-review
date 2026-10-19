"""Read-only availability ledger and continuation hints; never an adjudicator.

Text cues route existing uncertainty to a useful next step. They do not prove a
trial error, establish an unreported outcome, or change any inclusion decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from scripts.model_backend import atomic_json, digest

POLICY = "outcome_availability_v2"
CUES = {
    "target_timing": r"timepoint|follow.up|horizon|scheduled|assessment time|endpoint timing",
    "units": r"\bunits?\b|mmol|mg/dl|measurement scale",
    "denominators": r"denominator|analy[sz]ed.{0,20}(?:sample|number|\bn\b)|sample size|group sizes|participants.{0,20}(?:missing|unknown)",
    "dispersion": r"\bsd\b|\bse\b|standard deviation|standard error|dispersion|correlation|quartile|\biqr\b",
    "outcome_definition": r"outcome|endpoint|composite|change.score",
    "independence": r"overlap|same trial|trial family|independen|duplicate",
    "intervention_route": r"administration route|intervention.route|intravenous subgroup",
}
ACTIONS = {
    "target_timing": "Inspect original methods, registry or protocol for the outcome observation horizon; treatment duration is not follow-up.",
    "units": "Inspect the original table, scale definition and permitted unit conversion; do not guess a unit.",
    "denominators": "Inspect outcome-specific analyzed arm counts and attrition; do not infer unidentified denominators.",
    "dispersion": "Inspect original table legends or supplements for SD/SE/change dispersion and the prespecified transformation policy.",
    "outcome_definition": "Compare the reported outcome/estimand with the frozen protocol; do not substitute a different outcome.",
    "independence": "Inspect registry/cohort links and existing family adjudication before adding another effect.",
    "intervention_route": "Inspect primary intervention methods for the specified route; another drug's route cannot establish the target intervention's route.",
}


def read(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def normalized(text):
    return " ".join(str(text).split())


def build(run):
    run = Path(run)
    status = read(run / "status.json", {})
    if status.get("status") not in {"complete", "incomplete", "failed"}:
        raise ValueError("Availability reporting requires a finished run")
    tracked = {}

    def artifact(name, default):
        path = run / name
        if path.exists():
            tracked[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return read(path, default)

    status = artifact("status.json", {})
    protocol = artifact("protocol.json", {})
    extractions = artifact("extractions.json", [])
    accepted = artifact("accepted.json", [])
    families = artifact("trial_families.json", {"rows": accepted, "unresolved": []})
    links = artifact("family_links.json", [])
    synthesis = artifact("synthesis.json", None)
    family_blockers = []
    for index, unresolved in enumerate(families.get("unresolved", [])):
        reports = sorted(set(str(r) for r in unresolved.get("reports", [])))
        if any(not re.fullmatch(r"[A-Za-z0-9_.-]+", r) or r in {".", ".."} for r in reports):
            raise ValueError("Unsafe family record identity")
        evidence = []
        for j, link in enumerate(links):
            if not {link.get("report_a"), link.get("report_b")} <= set(reports):
                continue
            anchors = []
            for side in ("a", "b"):
                rid = link["report_" + side]
                name = f"sources/{rid}/text.json"
                source = artifact(name, {})
                quote = link.get("evidence_" + side, "")
                valid = bool(source.get("text") and source.get("sha256") == digest(source["text"]))
                anchors.append({"record_id": rid, "quote": quote, "source_artifact": name,
                                "source_sha256": source.get("sha256"), "text_hash_valid": valid,
                                "matches_source_text": bool(valid and quote.strip() and normalized(quote) in normalized(source["text"]))})
            evidence.append({"locator": f"family_links.json#/{j}", "relationship": link.get("relationship"),
                             "reason": link.get("reason"), "verification": link.get("verification"),
                             "independently_verified": link.get("independently_verified", False), "anchors": anchors})
        family_blockers.append({"reports": reports, "locator": f"trial_families.json#/unresolved/{index}",
                                "reason": unresolved.get("reason", ""), "pair_assessments": evidence,
                                "action": "Inspect both original recruitment/eligibility protocols for shared participants or re-enrollment; unresolved overlap is not demonstrated overlap. Do not add either effect without resolving the stored family decision.",
                                "automatic_scientific_action_authorized": False})
        if any("model call failed" in str(a.get("reason", "")).lower() for a in evidence):
            family_blockers[-1]["action"] = "Inspect preserved model-call failure receipts and reconcile execution state; after backend recovery retry only failed requests under the frozen contract. A failed call is not a scientific overlap finding."
    usable = {r["record_id"] for r in families["rows"]}
    accepted_ids = {r["record_id"] for r in accepted}
    items, queue, image_queue = [], [], []
    for index, item in enumerate(extractions):
        rid = str(item["id"])
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", rid) or rid in {".", ".."}:
            raise ValueError("Unsafe record identity")
        result = item.get("result", {})
        rows = result.get("rows", [])
        reasons = [{"locator": f"extractions.json#/{index}/result/reason", "text": result.get("reason", "")}]
        reasons += [{"locator": f"extractions.json#/{index}/result/missing/{j}", "text": str(t)}
                    for j, t in enumerate(result.get("missing", []))]
        reasons += [{"locator": f"extractions.json#/{index}/result/rows/{j}/validation_errors/{k}", "text": str(t)}
                    for j, r in enumerate(rows) for k, t in enumerate(r.get("validation_errors", []))]
        reasons = [r for r in reasons if r["text"]]
        blockers = [b for b in family_blockers if rid in b["reports"]]
        for blocker in blockers:
            reasons.append({"locator": blocker["locator"], "text": blocker["reason"]})
            reasons += [{"locator": a["locator"] + "/reason", "text": a["reason"]}
                        for a in blocker["pair_assessments"] if a.get("reason")]
        cues = sorted(k for k, pattern in CUES.items()
                      if any(re.search(pattern, r["text"], re.I) for r in reasons))
        if blockers and "independence" not in cues:
            cues.append("independence")
        source_name = f"sources/{rid}/text.json"
        source = artifact(source_name, {})
        source_valid = bool(source.get("text") and source.get("sha256") == digest(source["text"]))
        if source_valid and source.get('primary_image_queue'):
            from scripts.primary_image_queue import build as primary_images
            iq=primary_images(run/'sources'/rid,source)
            image_queue.append({'record_id':rid,'queue':iq,'automatic_numeric_admission':False})
        quotes = [str(q) for r in rows for q in r.get("evidence", [])]
        quotes += [q for r in reasons for q in re.findall(r'["“]([^"”]{15,})["”]', r["text"])]
        anchors = [{"quote": q, "matches_source_text": source_valid and normalized(q) in normalized(source.get("text", ""))}
                   for q in dict.fromkeys(quotes)]
        limitations = list(dict.fromkeys(str(t) for r in rows for t in r.get("limitations", [])))
        limitations += list(dict.fromkeys(str(t) for link in links
                                         if rid in {link.get("report_a"), link.get("report_b")}
                                         for t in link.get("residual_limitations", [])))
        if rid in usable:
            category = "accepted_with_reported_limitations" if limitations else "accepted"
        elif rid in accepted_ids:
            category = "accepted_not_independent"
        elif item.get("status") == "missing_fulltext":
            category = "missing_fulltext_access"
        elif result.get("eligibility") == "exclude":
            outcome_exclusion = re.search(
                r"different outcome|outcome.specific scope|(?:outcome|endpoint).{0,35}(?:not reported|not measured|unavailable)|not reported as a measured outcome",
                result.get("reason", ""), re.I,
            )
            category = "reported_different_or_unavailable_outcome" if outcome_exclusion else "reported_other_exclusion"
        else:
            category = "unresolved_target_inputs"
        entry = {"record_id": rid, "category": category,
                 "stored_eligibility": result.get("eligibility"), "stored_fulltext_status": item.get("status"),
                 "independent_effect": rid in usable, "routing_cues": cues,
                 "reasons": reasons, "reported_limitations": limitations,
                 "family_blocker_locators": [b["locator"] for b in blockers],
                 "source": {"artifact": source_name, "url": source.get("url"),
                            "sha256": source.get("sha256"), "text_hash_valid": source_valid},
                 "evidence_anchors": anchors,
                 "support_status": "Exact quote matches are source anchors only; no new claim-level adjudication. Unmatched or absent quotes do not prove the source lacks an outcome."}
        items.append(entry)
        if category in {"missing_fulltext_access", "unresolved_target_inputs", "accepted_not_independent"}:
            tasks = (["Find a genuinely new lawful original-source route; inspect preserved acquisition failures before retrying."]
                     if category == "missing_fulltext_access" else
                     list(dict.fromkeys(b["action"] for b in blockers)) or [ACTIONS["independence"]] if category == "accepted_not_independent" else
                     [ACTIONS[k] for k in cues] or ["Inspect the preserved extraction reasons and primary evidence; unresolved is not proof of a trial error."])
            queue.append({"record_id": rid, "category": category, "actions": tasks,
                          "evidence_locator": f"availability.json#/records/{len(items)-1}",
                          "automatic_scientific_action_authorized": False})
    return {"policy": POLICY, "source_run": str(run.resolve()),
            "run_status_unchanged": status.get("status"), "model": status.get("model"),
            "run_code_sha256": status.get("code_sha256"), "protocol_outcome": protocol.get("outcome"),
            "synthesis_unchanged": synthesis, "counts": dict(Counter(r["category"] for r in items)),
            "records": items, "continuation_queue": queue, "input_sha256": tracked,
            "family_continuation_queue": family_blockers,
            "primary_image_inspection_queue": image_queue,
            "reporter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "limitations": ["Deterministic text cues organize stored reports; they do not establish missingness, eligibility, trial errors or causality.",
                            "Reported outcome exclusions remain reported decisions, even when a quotation matches; scientific support requires claim-level adjudication.",
                            "Accepted data may retain limitations without becoming unresolved. No inclusion, completion or numerical gates are changed."]}


def export(run, output, report_roles=(), companion_assessments=()):
    run, output = Path(run).resolve(), Path(output).resolve()
    if output == run or run.is_relative_to(output):
        raise ValueError("Output must not replace the source run or its ancestor")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Availability output must be empty")
    report = build(run)
    if report_roles:
        from scripts.report_type_evidence import annotation

        annotations = [annotation(path) for path in report_roles]
        known = {r["record_id"] for r in report["records"]}
        if any(a["record_id"] not in known for a in annotations):
            raise ValueError("Report-role annotation is absent from this review")
        report["supplementary_report_role_evidence"] = annotations
        for item in report["continuation_queue"]:
            matches = [a for a in annotations if a["record_id"] == item["record_id"]]
            if matches:
                item["supplementary_report_role_evidence"] = matches
                item["actions"].insert(0, "Inspect newly verified publisher report-role evidence for separately versioned report eligibility adjudication; do not conflate report exclusion with trial exclusion or full-text access.")
    if companion_assessments:
        from scripts.companion_denominators import annotation as companion_annotation
        notes = [companion_annotation(path) for path in companion_assessments]
        known = {r["record_id"] for r in report["records"]}
        if any(n["record_id"] not in known for n in notes):
            raise ValueError("Companion assessment target absent from source run")
        for note in notes:
            target = run / "sources" / note["record_id"] / "text.json"
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != note["target_source_file_sha256"]:
                raise ValueError("Companion assessment target source differs")
        report["companion_denominator_assessments"] = notes
        for item in report["records"] + report["continuation_queue"]:
            matches = [n for n in notes if n["record_id"] == item["record_id"]]
            if matches:
                item["companion_denominator_evidence"] = matches
                if "actions" in item:
                    item["actions"].insert(0, "Inspect completed primary-companion denominator assessment and its remaining blockers before another retrieval or numerical continuation; same-trial identity alone does not supply outcome N.")
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / "availability.json", report)
    atomic_json(output / "continuation_queue.json", report["continuation_queue"])
    lines = ["# Outcome availability", "", "Stored decisions and numerical results are unchanged. Categories and next steps are reporting aids, not new adjudications.", "",
             "| Report | Availability | Routing cues | Matched source quotes |", "|---|---|---|---:|"]
    for r in report["records"]:
        lines.append(f"| {r['record_id']} | {r['category']} | {', '.join(r['routing_cues'])} | {sum(a['matches_source_text'] for a in r['evidence_anchors'])} |")
    lines += ["", "Exact reasons, source hashes, quote-match results and limitations are in availability.json. Matched text does not independently establish a clinical claim.", "", "## Suggested continuation", ""]
    for q in report["continuation_queue"]:
        lines.append(f"- {q['record_id']}: " + " ".join(q["actions"]))
    if report["family_continuation_queue"]:
        lines += ["", "## Trial-family blockers", "", "Unresolved overlap is uncertainty, not a finding of shared participants.", ""]
        for blocker in report["family_continuation_queue"]:
            lines.append("- Reports " + ", ".join(blocker["reports"]) + ": " + blocker["reason"] + " " + blocker["action"])
            for pair in blocker["pair_assessments"]:
                lines.append("  - Stored assessment (" + pair["locator"] + "): " + str(pair["reason"]))
    (output / "availability.md").write_text("\n".join(lines) + "\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--report-role", action="append", default=[])
    p.add_argument("--companion-assessment", action="append", default=[])
    a = p.parse_args()
    export(a.run, a.output, a.report_role, a.companion_assessment)

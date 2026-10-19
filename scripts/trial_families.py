"""Conservative dependence resolution for independently verified extracted rows.

Never chooses between discordant reports, splits a shared control, or merges
studies from similar titles alone. Registry aliases normalize exact identifiers;
report-family assertions must carry independently verified evidence.
"""

from __future__ import annotations

import re
from collections import defaultdict

from scripts.model_backend import digest


def registry_id(value):
    value = re.sub(r"[\s_-]", "", value).upper()
    if re.fullmatch(r"(?:NCT\d{8}|ISRCTN\d{8}|IRCT\d+[A-Z]\d+|ACTRN\d{14})", value):
        return value
    return None


def row_signature(row):
    keys = (
        "outcome",
        "unit",
        "value_type",
        "timepoint_reported",
        "n_treatment",
        "n_control",
        "mean_treatment",
        "mean_control",
        "sd_treatment",
        "sd_control",
        "events_treatment",
        "events_control",
        "treatment",
        "control",
    )
    return digest({k: row.get(k) for k in keys})


def resolve(rows, verified_links=()):
    """Return pooled-eligible rows and an explicit unresolved-dependence ledger.

    A verified link must identify both source reports and have nonempty source
    quotations. This function validates structure, not scientific truth: the
    caller is responsible for source checking and independent adjudication.
    """
    parents = {r["record_id"]: r["record_id"] for r in rows}

    def root(x):
        while parents[x] != x:
            x = parents[x]
        return x

    def union(a, b):
        parents[root(b)] = root(a)

    registry_groups = defaultdict(list)
    study_groups = defaultdict(list)
    for row in rows:
        registry = registry_id(row["study_id"])
        study_groups[row["study_id"]].append(row["record_id"])
        if registry:
            registry_groups[registry].append(row["record_id"])
    for group in list(registry_groups.values()) + list(study_groups.values()):
        for rid in group[1:]:
            union(group[0], rid)
    unresolved = []
    # Build the complete equivalence relation before checking distinctness.
    # Otherwise a distinct assertion preceding a later transitive same-trial
    # link can be silently accepted, making eligibility depend on link order.
    verified_links = list(verified_links)
    for link in verified_links:
        a, b = link["report_a"], link["report_b"]
        if a not in parents or b not in parents:
            raise ValueError("Family link references absent report")
        if link["relationship"] != "unclear" and (
            not link.get("evidence_a")
            or not link.get("evidence_b")
            or not link.get("independently_verified")
        ):
            raise ValueError("Unverified family assertion")
        if link["relationship"] == "same_trial":
            union(a, b)
        elif link["relationship"] not in {"unclear", "distinct_trials"}:
            raise ValueError("Unknown trial relationship")
    for link in verified_links:
        a, b = link["report_a"], link["report_b"]
        if link["relationship"] == "unclear":
            unresolved.append(
                {"reports": [a, b], "reason": "Potential trial overlap unresolved"}
            )
        elif link["relationship"] == "distinct_trials" and root(a) == root(b):
            unresolved.append(
                {
                    "reports": [a, b],
                    "reason": "Source distinctness conflicts with shared trial identity",
                }
            )
    groups = defaultdict(list)
    for row in rows:
        groups[root(row["record_id"])].append(row)
    accepted, families = [], []
    for group in groups.values():
        ids = [r["record_id"] for r in group]
        entry = {"reports": ids, "study_ids": sorted({r["study_id"] for r in group})}
        if len(group) == 1:
            entry["status"] = "single_report"
            accepted.append(group[0])
        elif len({row_signature(r) for r in group}) == 1:
            # Exact repeat reporting only; preserve every source identity.
            chosen = dict(sorted(group, key=lambda r: r["record_id"])[0])
            chosen["duplicate_report_ids"] = sorted(ids)
            accepted.append(chosen)
            entry["status"] = "identical_comparison_deduplicated"
        else:
            entry["status"] = "unresolved_different_comparisons"
            unresolved.append(
                {
                    "reports": ids,
                    "reason": "Same trial has discordant or multiple comparisons; no automatic choice",
                }
            )
        families.append(entry)
    if unresolved:
        involved = {rid for u in unresolved for rid in u["reports"]}
        accepted = [
            r
            for r in accepted
            if r["record_id"] not in involved
            and not involved.intersection(r.get("duplicate_report_ids", []))
        ]
    return {
        "rows": accepted,
        "families": families,
        "unresolved": unresolved,
        "limitation": "Different report identities without registry or verified linkage are not proven independent.",
    }


def shared_control_guard(comparisons):
    """Gate a multiarm extraction before pooling; no arbitrary active-arm choice."""
    seen = set()
    for row in comparisons:
        key = (row["study_id"], row.get("control_arm_id"))
        if not key[1]:
            raise ValueError(
                "Multiarm comparisons require explicit source-supported control_arm_id"
            )
        if key in seen:
            raise ValueError(
                "Shared control detected; prespecified combination or dependence model required"
            )
        seen.add(key)
    return comparisons

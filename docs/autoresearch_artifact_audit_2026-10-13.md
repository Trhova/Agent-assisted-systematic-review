# Artifact consistency research cycle, 13 October 2026

The benchmark evaluator now independently checks saved review artifacts before permitting reproduction. A real counterexample confirmed the gap: changing only the isolated Rawat IV run's status to `complete`, while leaving its unresolved candidate intact, made the previous frozen comparator report reproduction. The new comparator rejects that same copy with `unsupported_complete_status`. No original run was altered.

Implementation: `scripts/audit_run.py` provides a read-only audit; `scripts/autonomous_review.py` integrates it into comparison. It checks protocol/code/source hashes, search and screening coverage, extracted-to-accepted row consistency, optional SE/quartile transformations, source-backed family links and complete pair coverage, deterministic family resolution, counts/completion, and replay of the entire synthesis including weights and leave-one-out results. Numeric replay permits only 1e-12 absolute/relative roundoff; scientific tolerances remain separately frozen. Missing artifacts fail closed. The audit includes hashes of every artifact read and the auditor's code identity.

## Executed observations

| Preserved run | Artifact consistency | Independent effects | Unresolved extraction records | Completion supported |
|---|---|---:|---:|---|
| Ma aligned reproduction | Pass | 1 | 14 | No |
| Li aligned reproduction | Pass | 4 | 23 | No |
| Rawat all-routes, final repair | Pass | 3 | 2 | No |
| Rawat published IV subgroup | Pass | 3 | 1 | No |

The counts of unresolved extraction records include irrelevant-but-unresolved candidates, not just missing reference contributors. Li's pooled estimate replays as −0.4004663531; Rawat's three-effect estimate replays as −0.2957338720. Ma still has too few validated effects to pool. These are consistency observations, not new scientific reproductions.

Five isolated corruption experiments changed a pooled estimate by 0.01, source text, a resolved family denominator, completion status, or quartile-derived SD audit. **All five remained numerical matches to the Rawat subgroup target, but all five failed the new artifact gate.** The false-completion experiment was also executed with the prior immutable comparator: old `reproduced=true`, current `reproduced=false`. The original artifact fingerprints were identical before and after the experiments.

Full observations: `benchmarks/findings/artifact_consistency_v1.json`; explicit old/new counterexample: `benchmarks/findings/artifact_consistency_legacy_counterexample_v1.json`. All isolated inputs and comparator outputs remain under `data/benchmarks/artifact_consistency_v1`. The earlier `artifact_audit_rawat_iv_v1.json` is the initial development audit, superseded by the complete cohort finding, and retained.

## Reproduce

```bash
.venv/bin/python -m scripts.audit_run \
  data/benchmarks/rawat2021_iv_v1/rawat2021_iv_covid_hospital_stay_v1/64f1fbb555e4 \
  --output /tmp/rawat-artifact-audit.json

.venv/bin/python -m scripts.audit_benchmarks \
  --config benchmarks/audits/artifact_consistency_v1.json \
  --output data/benchmarks/artifact_consistency_v1_repeat
```

The experiment runner requires a fresh output directory and makes independent copies. The standalone audit refuses to write inside the preserved run. No model calls are needed. The old/new counterexample's exact command is retained in its finding.

Validation: **179 tests passed**, selected fatal-error/import lint and `git diff --check` passed; protocol/reference hashes for all seven distinct configured suite cases verified. Current auditor/runtime code identity: `7b45a15f3701a94c3c11584827962486e577680ebaf796384d2d2011a90c5eb5`. Observed numerical runs retain their original code identities and explicit `gpt-6-astra`/Codex model identity. Worker: Astra medium. No model execution or new literature acquisition occurred in this bounded cycle.

This checks internal consistency, not independent clinical truth, statistical-model suitability, expert RoB judgments, search completeness across databases, or model training contamination. Hashes are not signed attestations against coordinated alteration. Replay uses current supported methods, so a future method change needs separately versioned interpretation rather than silently overwriting historical results. Original missing-source and ambiguous-primary-data limitations remain unchanged.

Next research priority: qualify an additional published review/outcome using methodological fit and full contributor accessibility, freeze a compatible development protocol/model/source manifest/tolerances before model execution, then execute the actual workflow. Require at least two independently accessible primary trials; reject unsupported study designs and unidentified statistics at qualification. Do not select by likely numerical agreement, retry unchanged access failures, or count another Rawat subgroup as an independent review.

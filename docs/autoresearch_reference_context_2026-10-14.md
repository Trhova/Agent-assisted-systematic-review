# Original supplement context and typed verification — 14 October 2026

The separately frozen v2 source-verification run completed two fresh evaluator-only image requests. All three selected published rows passed seven explicit checks: cells, trial identity, arms, mortality timepoint, population against the frozen scientific contract, source locator and outcome. The new receipt is valid; the original v1 false receipt remains immutable. This establishes model-checked published transcription/mapping, not equality with primary results or independent human expertise.

The read-only evaluator consequently reports contributor agreement=true and **input agreement=false**. ORCHID's published25/242 versus25/237 remains different from primary mortality25/241 versus25/236. Scoped reproduction remainsfalse. No scientific extraction or pooled analysis was rerun; RR0.877845177[0.578064555,1.333090133] is unchanged.

## Evidence and gates

The original supplementaryDOCX was already lawfully preserved inside the EuropePMC supplementaryZIP. A new generic ordered-context extractor retains paragraph/table blocks and embedded-image member hashes. FigureS15's originalimage is `word/document.xml` bodyblock385, captionblock386–387; TableS10 captionblock445 and tableblock446. Visible rows are Dubée2021, Self2020 and Ulrich2020. The new mapping uses these author labels instead of trial-name-only locators. Complete original supplement context was supplied, not a rewritten caption or manually invented coordinates.

`reference_source_verification_v2` requires every semantic axis to be supported; unclear or unsupported on any axis blocks even when integers match. Typed blocking problems also block. Nonblocking observations can retain primary-versus-published value differences, follow-up limitations or scope notes only when all axes remain supported. The new schema was frozen before the fresh requests; no v1 output was reclassified retrospectively.

The verifier retained HYCOVID's three ambulatory participants, TEACH's day30/late-follow-up and missing-outcome limits, ORCHID's missing vital status, and secondary mortality versus day14 primary efficacy distinctions. Population support concerns the original frozen predominantly-hospitalized whole-cohort contract, not an inpatient-only effect. It also recorded an additional review-versus-primary dose-description observation, preserved in raw verification output rather than used to change inputs.

Both requests usedgpt-6-astra in separate isolated conversations; same-model correlated errors remain possible. The blind request sees original image/review/supplement, without manual proposed cells or accepted extracted rows. The second sees source context and proposals. Published targets never enter scientific screening/extraction. Exact quotes, image assets, submission modality and successful response artifacts are checked in receipt replay.

## Actual execution and preservation

- Model-run artifacts: `data/benchmarks/hcq_reference_verification_v2`.
- LauncherPID22199; finished20:31:22UTC, exit0; two fresh adapter response receipts, no automatic retry/recovery, no runner remains. CLI-internal transport attempts are not counted as separate adapter invocations.
- Model-run code `3279431af16d7be33c3f471a391ee3a335bb6f62f93152cd01ac862e46462036`; explicitgpt-6-astra/codex; workerMedium, nested effort backend-default/unpinned.
- Frozen read-only evaluator under `evaluation`: code `93d1fcf32f17538c156a9ab3df4f724230ab8c25588b9a59184438c73b6c579c`, exit0. It replays the actual source-verification receipt before granting reference trust. All163original HCQ run files unchanged.
- All27v1 verification/evaluation files and all21source-manifest pins remain unchanged. `preservation_audit.json` records these checks.
-300tests pass, F/E9 lint and whitespace checks pass. Tests explicitly cover each semantic axis in unsupported and unclear states, altered reference cells despite otherwise positive verification, and observations that cannot override blocking evidence.

## Concrete original-source acquisition improvement

During context preparation, a generic parser defect was demonstrated: `supplements.parse_attachment` inserted spaces between Word formatting runs. That can split a caption like S15 or a number like242 into separated tokens. The repair concatenates text runs as encoded in the source, preserving explicit tabs/line breaks and paragraph/cell boundaries. Newly parsed DOCX attachments record `parser_policy=docx_inline_text_v2`. Existing cached source documents are not silently rewritten or invalidated; fresh/versioned source preparation is required to adopt the repair.

A separately frozen real-source validation under `data/benchmarks/docx_parser_validation_v2` parsed the exact same original supplement through the preserved old code and the new code. Both executions exited0 and the original DOCX hash stayed unchanged. Old output lacked the exact Fig.S15 caption; repaired output contains it. A controlled regression additionally splits242 across formatting runs and confirms that it remains242, while explicit tabs/newlines and cell boundaries remain visible. This is a reusable source-ingestion fix, not an inference that prior accepted numerical inputs were wrong.

The initial helper output with run-inserted spaces is retained beside the corrected ordered output; only corrected context was included in the frozen v2 manifest. No raw original was overwritten.

## Next work and scope

Prioritize original-source/estimand autonomy now. Next concrete step is to connect the ordered DOCX/image-locator evidence to the general supplement-acquisition manifest and source-upgrade path, so ordinary primary-report ingestion supplies contextual evidence without manual research preparation. Exercise it on an original primary-study attachment with versioned source outputs, preserving caches and acquisition failure history. Avoid another unchanged evaluator or numerical rerun.

This remains a post-hoc developer-assisted published-subgroup evaluation, not complete-review reproduction or prospective validation. Source discovery/access and review-question qualification still require broader testing; Alabed/Popp unresolved evidence remains unchanged. The overall project objective is incomplete.

# Bounded original-primary image inspection — 15 October 2026

Implemented a document-order image-inspection queue in normal supplement ingestion, connected it to outcome-availability continuation output, and actually inspected the first original Johnston supplement image. The two isolated gpt-6-astra calls completed successfully. The checked visual observation identifies an overall FluPRO symptom graph across study days and HCQ/HCQ-Az/placebo labels, but **no explicit analyzed within-arm N or means with SDs**. No graph marks were digitized or statistics inferred.

This is source-inspection progress, not numerical input acceptance. Johnston remains household-randomized, and no quantitative use was contemplated. No systematic-review screening, effect extraction or pooling was rerun. Existing benchmark results and access gaps remain unchanged.

## Functional workflow

`scripts.primary_image_queue.build` derives stable item identities from raw DOCX hash, embedded member, relationship and original block locator. It validates raw/context/image hashes and safe paths, preserving adjacent text as unassigned context. Normal `supplements.augment` now includes this queue in the source document. `outcome_availability` exposes validated primary-image queues alongside other continuation needs, with automatic numeric admission disabled.

`scripts.inspect_primary_image` executes one frozen first-pending document-order task, with one image-reading request and one separate pixel-backed verification. Each permits one adapter invocation; no outer retry. Its successor source contains a hash-bound receipt and durable checked, irrelevant, unreadable, relevance-unclear or unverified status. Queue rebuilding preserves completed states instead of selecting them again automatically. A new justified manifest is required to move to another pending task or revisit evidence.

Visual observations are explicitly pixel-derived. They are not inserted as verbatim article quotations or merged into raw primary text. Neither positive verification nor reported visibility of numeric fields can set numerical_admission=true. Any later quantitative use needs a separately supported outcome/design/evidence contract with valid units, denominators, timing and statistical inputs.

## Actual original evidence and execution

Source: Johnston2021, PMID33681731/PMC7912360, original `mmc1.docx`, prepared by the previous primary-supplement upgrade. First selected image is `word/document.xml body block27`; its preceding text identifies SupplementalFigure1A, but adjacency alone is not interpreted as caption ownership.

- Artifacts: `data/benchmarks/johnston_primary_image_inspection_v1`.
- Frozen code `9f6f796109156cde447f6c0e3de12b646dd0b3e3f30c25244ea88d11efa60102`.
- LauncherPID6032; completed00:35:25UTC, exit0; no runner remains.
- Explicitgpt-6-astra/codex; workerMedium, nested effort backend-default/unpinned. Two fresh adapter calls; CLI-internal transport attempts are not separately counted.
- Original PNG SHA256 `bd50d96ca185e80b6a0b7280f72d3ed407a554aa73bc6d5da518b26b2d4727bd`.
- Status `source_checked_visual_observation`; verifier valid with no problems. It explicitly retains unknown box/whisker/point definitions and same-model correlated-error limitations.
-12queueitems before; first item durably checked and11remain pending. None is numerically admitted. No further image calls launched.

The actual receipt audit verifies both request/schema/image/submission/terminal-response chains and checks saved observations against the returned parsed responses. All24source/policy pins remain unchanged. Successor raw primary text and text hash are exactly unchanged. The normal queue consumer rebuilds the checked status and does not reselect that image. Source lineage and successor file hashes are recorded separately; the inherited prior source-upgrade manifest remains parent-stage history, not a claim that successor metadata has its old hash.

`consumer_audit.json`, `source_successor_manifest.json`, actual request/response artifacts, before/after queues and successor source metadata preserve these observations. Published review targets were never supplied.

## Tests and limitations

315tests pass; F/E9 lint and whitespace checks pass. Tests cover image/raw/context tampering, source-only context interpretation, durable checked/irrelevant/unreadable/unclear outcomes, no automatic repeated calls, unchanged raw text and numerical-admission refusal even when a controlled inspector claims N/mean/SD are visible. Outcome-availability integration is tested with source-stage fixtures; the actual original image execution and consumer replay are separately documented above.

Two calls from the same model provide procedural separation, not independent human expertise. A source-checked description does not establish exact statistical transcription, outcome eligibility or trial independence. The remaining11Johnston images should not be processed merely to accumulate activity; this inspected plot and the trial design do not support the current numerical comparison.

Next scientific-source step: apply the bounded queue to a genuinely relevant original parallel-trial image with explicitly reported outcome data, and specify/test image-grounded evidence admission before any statistical extraction. Preserve pixel/member locators and actual units/denominators; do not replace missing statistics with graph digitization or infer cluster corrections. Broader autonomous review completion and several-review validation remain unfinished.

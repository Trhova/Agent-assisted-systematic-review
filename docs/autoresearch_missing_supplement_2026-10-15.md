# Recovered primary supplement — 15 October 2026

The previously inaccessible original supplement for Hariri 2015, PMID26577825, DOI10.1007/s12263-015-0503-1, was recovered from the publisher and consumed by normal supplement ingestion. It supplies general characteristics with mean±SE and group N=20, **not end-of-treatment fasting glucose values**. The trial remains eligible but unresolved for the Li fasting-glucose contract. No outcome denominator, SD or mean was inferred from general characteristics; no numerical analysis was rerun.

This is real source-access progress on a documented unresolved record, not another known-input image calibration. It does not reduce the six named original Ma/Li full-text gaps, and it does not reproduce the complete Li review.

## Selection and actual source

Petare's original Table2 image was inspected first because the preserved Perez run lacked final active-arm SDs. The image actually lacks those endpoint columns; its nearby graph is heart rate, not VO2max. Image reading cannot recover unprinted values. The original PDF/hash/page render and finding are preserved in `data/benchmarks/petare2016_source_qualification_v1`. Rawat's route/dispersion ambiguities likewise were not reclassified without new evidence.

Hariri explicitly links a missing DOCX. Earlier direct PMC and Europe PMC archive responses were not valid DOCX/ZIP files. The new route binds the verified primary DOI and exact linked filename to the [original publisher asset](https://static-content.springer.com/esm/art%3A10.1007%2Fs12263-015-0503-1/MediaObjects/12263_2015_503_MOESM1_ESM.docx). HTTP200 was received at 04:34:39UTC; 15,211bytes, SHA256 `e77b7b2b710e60f50878662845ebd2d203874a4f37f9b1036245f9e6ea9a79bd`. An initial incorrect candidate hostname failed DNS and is recorded separately; it was not an HTTP response or source. The [primary article](https://pmc.ncbi.nlm.nih.gov/articles/PMC4648806/) identifies the supplement as baseline characteristics.

## Reusable implementation and execution

`scripts/supplements.py` now has a bounded Springer fallback after failed primary/archive routes. It requires verified DOI metadata matching the bibliographic DOI and an exact primary-linked MOESM filename with matching journal/year/article identifiers. It does not admit arbitrary similarly named assets. This deliberately narrow first implementation supports matching 10.1007/s identifiers; it does not claim all publisher coverage. Existing request/time bounds apply, and all failed attempts remain visible.

`scripts/upgrade_publisher_supplement.py` accepts a successful URL/hash-bound retrieval receipt and replays the recovered bytes through normal `augment()` in cache-only mode into a fresh source directory. Actual frozen replay parsed the DOCX and exposed its ordered content in normal source text. **All61 original source files remained unchanged.** No network or model calls occurred during that replay.

`scripts/reassess_source.py` executes a bounded single-record continuation with the unchanged scientific outcome contract and upgraded full primary source. It uses the existing extraction schema plus explicit SE-policy fields where applicable, a separate source-verification request, preserved raw receipts and ordinary availability export. It never promotes proposed rows into accepted inputs or pools them; any numerical candidates require normal derivation, integrity and family validation in a subsequent review continuation. The previous review remains untouched.

Actual code `02abb7dbd81b0f34d4faeb1d1f57d5a8b436a1c4f08a6ea5cef30e65e51df145`; launcher PID29816 / child29817 completed04:39:31UTC, exit0. Explicit `gpt-6-astra` via authenticated Codex; worker Medium, nested effort backend-default/unpinned. Two fresh adapter invocations, one attempt each, no retry. The original Li protocol, model, code, upgraded source and recovery policy were pinned before execution; no benchmark target or previous extracted cells were supplied.

Actual output: eligibility include, zero rows; missing FBG endpoint means/dispersions and outcome-specific analyzed N. The verifier returned valid/no problems. All72 continuation input pins and both successful request/response chains passed the later audit. Three of four quoted anchors match strict whitespace-normalized source. The general completion sentence has a formatting mismatch around parsed inline text; its exact source context and failed initial all-anchor assertion remain in the audit. This is explicitly **not** a claim that every quotation was mechanically verified. It changes no numeric decision and does not justify using overall completion N as outcome N. Same-model verification can share errors.

## Validation and limits

**357 tests pass**, including13 new acquisition tests covering mismatched article/year/journal, unverified DOI, failed or mismatched receipts, missing pins, preserved original files, refused output reuse and actual normal-consumer fallback. Focused new-file lint, fatal-error lint for the modified ingestion module and whitespace checks pass. No live runner remains.

Artifacts: `data/benchmarks/hariri2015_supplement_recovery_v1` contains raw bytes/receipts, immutable upgrade and reassessment manifests, exact frozen commands, upgraded source, extraction/verification/availability outputs, and `final_audit.json`. No old sources or scientific observations were overwritten.

The next scientific action is a source-linked companion-report search for IRCT201405265062N8, preserving the already known PMID26261453/26577825 family. Do not retry this now-recovered supplement or treat its general-characteristic SEs as glucose data. Any companion must match the actual trial and outcome and must not become an extra independent study. Other original access and estimand limitations remain; the full autonomous-review objective is incomplete.

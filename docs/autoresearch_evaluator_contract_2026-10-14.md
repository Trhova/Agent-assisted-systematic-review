# Evidence-aware evaluator contract — 14 October 2026

Implemented `evaluator_input_contract_v2` and executed it on the preserved HCQ hospital-mortality development run. The original scientific run, reference and historical comparator are unchanged. This cycle made no model calls, extraction calls or numerical reruns.

| Claim | New evaluation |
|---|---|
| Numerical/semantic agreement | True |
| Report coverage agreement | True |
| Trial/arm/time mapping structure | Complete; developer-transcribed, not independently verified |
| Reference-cell trust | Manual transcription, unverified |
| Observed input comparison | Two ORCHID denominator differences |
| Independently verified input agreement | Unknown |
| Independently verified contributor agreement | Unknown |
| Scoped reproduction under new contract | False |
| Whole-review reproduction | Not established |
| Prospective validation | Not established |

The source-first result remains RR0.877845177[0.578064555,1.333090133] from three independent trials. ORCHID primary denominators241/236 differ from manually transcribed published242/237. These are observed differences in transcribed cells, not newly independent validation of the review figure. Pooled agreement alone cannot establish exact-input reproduction. The original comparator's `reproduced=true` is preserved and reported explicitly alongside the separately versioned decision.

## Implemented behavior

`scripts/evaluate_contract.py` reads only finished, hash-pinned artifacts; checks binary reference semantics and evidence hashes; requires unique report/trial mappings; checks accepted study identity, arm labels, outcome timepoint and reference locators; replays existing artifact checks; and snapshots all source-run files before/after. Missing reference cells produce `not_assessed`, not agreement. Missing or mismatched mappings prevent verified agreement. Duplicate mappings and changed source pins fail closed.

Manual reference cells never become independently verified merely because their source hash is valid. An optional independent verification receipt must bind the exact cell reference and mapping digest, identify the reviewer/method/locator and affirm validity. The evaluator validates this supplied attestation, not the reviewer's real independence or accuracy; that limitation remains explicit. This cycle supplied no such receipt. This policy currently supports one binary outcome/comparison per independent trial; it does not silently resolve repeated arms or multiple reports.

`benchmark_suite.evaluate` supports an explicit hash-pinned `evaluation_contract` opt-in. Its new branch performs the same read-only evaluation without overwriting the old comparison or export. Existing cases without this field retain historical behavior. Both standalone and integrated suite paths were actually exercised against the original HCQ run, each exit0, each preserving all163 files.

Policy: `protocol/extensions/evaluator_input_contract_v2.md`. This is an evaluation/reporting extension, not a change to statistical estimators, eligibility, accepted inputs or clinical interpretation. It does not claim full-review/prospective success even if a development subgroup passes all supported checks.

## Frozen execution and validation

Artifacts: `data/benchmarks/hcq_evaluator_contract_v2` contains the contract, preregistration, standalone evaluation/execution receipt and integrated suite-path evaluation/receipt.

- Evaluator code: `220d0800c5956d9657f2f6dfee159dfa697cec58465ac12f707d77b0cc7772e0`.
- Contract: `b3838d4f7a1ff15aa30f4b7b2c7df3371837d9f6412a42d80920ce15996e4058`.
- Preserved scientific code: `b895c2ec7b167ff92a14b0486f212f2d282a353efd23ab160b5a718af6d93dd5`; modelgpt-6-astra, nested effort originally unpinned.
- Standalone evaluation PID14343; completed2026-10-14T16:31:25.399138+00:00, exit0. No runner remains.
-275tests pass; F/E9 lint and whitespace checks pass. Tests cover missing/manual/unverified cells, positive cells with negative integrity/semantic/coverage gates, unknown comparator fields, duplicate families, mutated sources, missing pins, wrong contract checksum and missing/misaligned study/arm/time/locator mapping.

Re-evaluate only into a new output directory using the pinned code bundle and `scripts.evaluate_contract RUN CONTRACT --output NEW_PATH`. Do not overwrite the preserved evaluation or invoke a new scientific benchmark merely to inspect this result.

## Remaining work

The comparator now exposes its evidence limits instead of collapsing different claims into pooled agreement. Reference-cell and trial mapping accuracy still requires independent source-backed verification; the supplied-attestation interface is not an autonomous verification engine. Next concrete improvement: a bounded evaluator-only reference transcription/verification workflow with exact source locators and independent reviewer receipts, using the preserved forest image without exposing targets to screening/extraction. Failures or ambiguous image readings must remain unverified. Broader review autonomy still depends on source discovery/access, estimand qualification and validation beyond familiar developer-assisted subgroups. Existing Alabed/Popp access limitations remain unchanged; overall project objective is incomplete.

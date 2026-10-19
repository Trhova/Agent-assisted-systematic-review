# Operating workflows

These are routes through existing implementations, not permission to overwrite prior runs. Inspect the selected script's `--help` and its manifest loader before preparing a fresh manifest; historical example manifests are evidence, not templates to execute unchanged. Commands below use `.venv/bin/python` from the repository root. Model execution requires an explicitly verified available model; current development used `gpt-6-astra`/`codex`. Record nested reasoning effort separately if unpinned. No extra approvals are required for already-authorized local work; genuinely missing scientific information becomes an unresolved decision.

## 1. Qualify and freeze an analysis

Inputs: published methods and exact selected analysis, bibliographic search contract, original primary reports and attachments, supported design/estimator, source inventory. Resolve comparator, population, dose/arm selection, follow-up window, endpoint/change and randomized unit before freezing. A subgroup is allowed but must remain visibly a subgroup; do not retrospectively narrow eligibility to make it complete. Report publication cutoff is distinct from trial dates and current registry availability.

Output: versioned protocol, source manifest, explicit model/backend, estimator and tolerance, family assumptions, maximum rounds/calls, non-Python schema/prompt/method hashes, evaluator-only reference contract, empty isolated destination. Pin manuscript/PDF page derivations and any image/context chain. Missing reference cells remain unverified, never equal by default.

Freeze Python with `scripts.run_frozen.bundle(Path('scripts'), bundle_root)`. Record returned root and digest before launch. Execute every dependent CLI using `scripts.run_frozen.command(root, digest, module, argv)`; a plain nested `python -m` can import mutable repository code. Use `scripts.benchmark_suite --suite ... --workdir NEW --backend codex --model EXPLICIT --max-rounds N` via that frozen command. Set suite `prespecified_code_sha256` when applicable. Check actual child identity before dependent work. Preserve stdout, launch PID, child PID and terminal receipt. Example of a real successful freeze: `data/benchmarks/hcq_hospital_mortality_v1/launch.py` (inspect only; do not rerun its destination).

Stop: unsupported allocation/statistic, incomplete critical primary inputs, uncertain duplicate submission or pin mismatch. Work on another independent step; never force pooling.

## 2. Recover and upgrade original sources

Inputs: record identity, DOI/registration, prior attempted URLs/errors, source-specific unresolved reason. Try genuinely new lawful primary routes within a stated attempt/time budget. Preserve response URL/status/time/body hash even on failure; do not call a challenge page a source. Do not use secondary numerical values as primary evidence.

Use `scripts.import_source_pdf --pdf ... --receipt ... --record RECORD_JSON --destination NEW [--pages FIRST LAST]` for a receipt-backed original. A collection import must link downloaded hash → exact original article page range → derived PDF hash; other articles must not enter extraction. Use `scripts.upgrade_publisher_supplement MANIFEST --output NEW` for cache-only, pinned attachment augmentation. Original DOCX/image context is exposed by normal supplement ingestion; untranscribed image markers require actual pixel inspection, not fabricated quotations.

Outputs: raw acquisition receipts, identity verification, immutable original, versioned `text.json`, attachment/derivation context and upgrade manifest. Existing sources/caches remain unchanged. `data/benchmarks/hariri2015_supplement_recovery_v1` is an actual negative-outcome replay: attachment recovered, no target FBG data. Recovery success does not mean numerical eligibility.

## 3. Repair an exact-source failure

Inputs: failed request/response, exact source and protocol hashes, original proposed row, deterministic anchor failures. Diagnose whether reading order, glyphs or wrong evidence caused the failure. Existing `continuous_derivations.derive_with_quote_repair` and `scripts.repair_source_candidate MANIFEST --output NEW` keep numerical fields fixed; inspect applicability first. The latter's exercised use is a continuous source-candidate continuation, not a universal trial-family solver. `family_quote_repair` is restricted to a positive prior scientific verification blocked by quotations; it cannot overturn an adverse scientific verdict.

Freeze a new repair policy/manifest. Quote-only request may replace evidence arrays, not N/means/SD/arms/time/population. Keep original and rejected evidence. Require exact source matches and a fresh complete semantic/statistical verifier before normal admission. A correctly matched table row still needs population/time/dispersion context. Examples: `soy_companion_anchor_repair_v1`, `li_soy_fixed_input_addendum_v2`. Do not remove unmatched evidence merely to make a check pass.

Outputs: before/after evidence, fixed-field comparison, actual verification receipt, ordinary validation result; source-only success is not permission to pool. Stop on unsupported fields or unresolved scientific disagreement.

## 4. Adjudicate reports, families and denominators

Inputs: complete original reports/registry, exact outcome contract, explicit discrepancies. `scripts.companion_denominators MANIFEST --output NEW` separates supported family linkage from transfer of outcome-analyzed N. Registry target N, randomized N, baseline table N and attendance total cannot silently become analyzed arm N. Resolve conflicting populations/flows with primary evidence or retain nulls.

Use existing family-adjudication evidence tiers and transitive family resolver: distinct randomization evidence can support separate studies; shared sites/authors alone do not prove reused participants, but affirmative overlap must block double counting. Assess a new family against every contributing study, not only the most similar one. Companion reports cannot become extra independent effects. An updated-evidence addendum is not a historical-search reproduction.

Output: source-linked decision, exact quotations, unresolved conflicts, separate family/N verdicts and request provenance. Import validated result into normal queue with `scripts.outcome_availability --run PRESERVED --output NEW --companion-assessment ASSESSMENT_ROOT`. The import checks target source identity and does not change eligibility/synthesis. Actual example: `data/benchmarks/mohamadshahi_companions_v1/export_receipt.json`.

## 5. Recover interrupted calls

Inputs: immutable failed attempt, submission intent, terminal receipt, request/model/schema identity, verified successful cache, single-operator reconciliation. Use `scripts.continue_model_requests --manifest ... --output NEW` via frozen execution. Its shared ledger protects participating continuations, not unrelated runners; ensure source review/RoB is inactive. Terminal429/503 may permit bounded continuation after recorded Retry-After/cooldown; an earlier transient log does not override a final permanent failure. Retry-After may be a date or delay; do not timestamp it from request start. Timeout/no terminal receipt is uncertain, not proof of no submission. Scientific rejection/schema failure is not a transport retry.

Outputs: classified decision, cache-import/continuation receipt, adapter-invocation budget and residual uncertainty. CLI internal transport retries may exceed adapter counts. Never claim an exact remote-request limit without evidence. Preserve old failures and never rerun unchanged missing-source attempts.

## 6. Audit, compare and hand off

Run `scripts.audit_run RUN --output NEW_JSON` through a frozen command. It replays arithmetic and internal consistency; it is not independent clinical review. Check actual request provenance separately when the analysis requires it. Use the versioned input evaluator and source-verification contract for published cell/arm/time mappings; targets stay out of scientific extraction. Exact source transcription can be correct while primary-versus-reference inputs differ.

Required output distinctions: searched/assessed reports, unresolved reports and possible missing studies, independent accepted effects, input agreement, numerical tolerance, explained discrepancy, execution integrity, RoB verification, development/prospective scope. Inspect specific unresolved reasons instead of equating every gap to a missing trial. Write the release judgment separately from unchanged historical comparator results. See `docs/agent_assisted_release.md`.

Fresh auditable smoke exercise: freeze an auditor, audit preserved HCQ and Alabed into a new directory, compare all source-run file hashes before/after, then retain both the current auditor identity and original execution identity. No model calls or scientific rerun is required. A valid audit does not erase Alabed's historical code-pin deviation or access gaps.

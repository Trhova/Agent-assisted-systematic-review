# Original-image input admission — 15 October 2026

This cycle implements an opt-in route from original table pixels to binary input validation. It uses ORCHID's original Table 2, full original-report page 7 / provider-collection page 14. The mortality subsection prints outcome-specific denominators separately from randomized column headings. This is a meaningful image-reading calibration, but the paper was already text-accessible and its cells were known to the developer. It is post-hoc development, not recovery of a previously missing trial, a held-out benchmark, or complete autonomous review validation. No published-review answers or previous extracted cells were included in either request.

Asemi was rejected as a clean positive control because its existing integrity notice withholds the trial. Johnston's household allocation and graph lacking explicit supported inputs are unsuitable for independent-person quantitative admission. ORCHID was selected for explicit primary cells, parallel individual randomization and the material outcome-denominator distinction, not numerical agreement.

## Implemented behavior

`scripts/primary_image_inputs.py` freezes the primary source, original PDF/collection, rendered full page, exact methods context, outcome contract, explicit model and code. The source-only reader returns printed counts, outcome-specific denominators, visual locators and exact methods evidence. A separate same-model verifier must support all nine axes: cells, denominators, arms, outcome, timepoint, population, individual parallel design, source identity and locator. Unclear axes, null/noninteger/impossible counts, absent quotations or receipt failures block admission. Same-model verification is procedural separation; correlated errors remain possible.

The consumer re-renders original PDF pixels and the corresponding collection page, checks source/context hashes, reconstructs exact prompts and schemas, validates successful response/image receipts and binds every admitted row field. `autonomous_review.validate_evidence` accepts this evidence modality only under its separately specified policy and exact original outcome contract. It does not bypass eligibility, integrity, family independence or pooling checks. Image wording is labelled visual observation, not invented textual quotation.

V1 (`data/benchmarks/orchid_image_input_v1`) completed at 02:38:56 UTC, exit 0, admission false. Both readings supported the same printed values and semantic axes, but exact design quotation matching failed: the preserved cached PDF parser interleaves the left and right columns. The failed receipt remains immutable. Its consumer audit attempt found no admitted row and is explicitly recorded as not performed, not a successful test.

V2 adds a source-context projection whose complete methods pages reproduce exactly from the pinned original PDF using the recorded pypdf version and page locators. It preserves old cached text and requires exact quotation matching against the newly supplied original context. This repairs the demonstrated parsing issue without relaxing the quote gate. V2 code: `e041ca38addaf1dd347078d2dfbc858ffe95aebe0b48075ed77978cfc760ec4d`; V1 code: `dca4518a597ce498a62cd0783b25062348db969061b98db237d7f50dc7564870`.

The explicit model is `gpt-6-astra` through the existing authenticated Codex backend. Worker reasoning is Medium; nested backend reasoning is default/unpinned. Each version permits two adapter invocations, one attempt per request, no outer retry. Existing [official CLI image-input documentation](https://learn.chatgpt.com/docs/developer-commands?surface=cli) and actual image request receipts support the modality; no model substitution occurred.

## Actual result and validation

V2 completed at 02:41:54 UTC, exit 0; launcher PID 3648 / child 3649 exited. Both fresh requests supported **25/241 hydroxychloroquine versus 25/236 placebo**, all-cause all-location death at 28 days after randomization. All nine axes were supported; exact original methods quotation and request receipts passed. The normal input validator returned no errors. No pooled estimate was calculated, no old accepted row was replaced, and trial eligibility/family/integrity clearance was not implied.

The frozen-code consumer replay accepted the original row and rejected five alterations: either randomized header N substituted for outcome N, an altered event count, an altered row timepoint and an altered contract timepoint. Both request/image/response chains were revalidated and all ten source/policy pins remained unchanged. Four fresh adapter invocations total across V1 and V2; no retries or numerical reruns. The prior V1 consumer audit did not run because its admission failed; this is retained as `consumer_attempt.json`.

**344 tests pass.** Focused lint passes for the new implementation/tests, fatal-error lint for the modified main consumer, and whitespace checks pass. A broad all-rules lint invocation also exposed 185 existing repository issues; this cycle does not claim a globally clean all-rules lint result.

Artifacts: `data/benchmarks/orchid_image_input_v1` (preserved false admission) and `data/benchmarks/orchid_image_input_v2` (successful admission, exact launch command, source manifest, raw model receipts, consumer audit). Read-only replay, using the recorded frozen implementation:

```sh
.venv/bin/python data/benchmarks/orchid_image_input_v2/validate_consumption.py
```

New execution uses `scripts.primary_image_inputs MANIFEST --output NEW_DIRECTORY` through `scripts.run_frozen.command` with the manifest's exact bundle/hash. The runner rejects a nonmatching unfrozen invocation and an existing output directory; do not use a repeat launch as a status check.

## Limits and next work

This is a manually qualified source/contract and a working admission consumer, not automatic review-level selection or a new synthesis. The image pipeline does not yet autonomously decide which unresolved report/image is most relevant and invoke admission within a finished review continuation. That targeted selection/integration is the next useful autonomy step; more readings of irrelevant Johnston graphs would not help. Existing ORCHID primary-versus-review denominator disagreement, Alabed five report-access gaps and Popp three unresolved records remain unchanged.

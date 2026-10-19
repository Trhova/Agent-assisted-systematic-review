# Blinded published-source verification — 14 October 2026

Implemented and actually executed a bounded evaluator-only image workflow on the preserved HCQ forest. Two fresh gpt-6-astra requests completed successfully; no scientific extraction or numerical analysis was rerun. The blind first reading recovered all five published study rows, including Self2020/ORCHID25/242 versus25/237. The second source-reading request supported all three selected cell sets, trial identities and mortality horizons, but returned cautions in its problems field. The frozen conservative policy therefore produced **valid=false**, which remains preserved.

The cautions concerned the known primary-versus-published ORCHID denominator discrepancy, mortality being a secondary outcome at28–30days rather than the day14 primary efficacy outcome, and proposed locators using trial names instead of visible author labels. The verifier also noted that the full supplement caption/TableS10 was not supplied as text. None is silently converted into a successful overall receipt. The actual verification output separately records cells_match_source=true and mapping_supported=true for all three rows; these component findings do not override its invalid receipt.

## Actual execution

- Artifacts: `data/benchmarks/hcq_reference_verification_v1`.
- LauncherPID29841;18:30:56–18:31:59UTC; exit0; no runner remains.
- Frozen model-run code `e3163a24f11bf3e7095114bf81e38a47c43202ecdcac3859338b98cfec7fbea2`.
- Explicit modelgpt-6-astra/codex; workerMedium, nested effort backend-default/unpinned. Two adapter invocations, max_attempts1 each, no outer recovery. Internal CLI transport requests are not counted as separate adapter invocations.
- ImageSHA256 `40b91cc3ba66c73d5618e51d61acd38f2e2d5c00ca008772301c91812e54e71e`; both submission receipts record image/png and this exact hash.
- Exact source chain: original EuropePMC supplementaryZIP→`mmc1.docx`→`word/media/image15.png`. Byte equality was checked at both archive levels. No fabricated PDFpage, crop coordinates or rendered transformation; full embedded PNG retained.
- Blind call receives original image and review text only. It does not receive manual proposed cells or accepted extracted numerical results. Separate verifier receives image, blind reading, proposed published cells/mapping and original primary texts. Published benchmark answers never enter scientific screening/extraction.

Two requests from the same model are procedurally separate, not independent human expertise; correlated errors remain possible. Image recognition and source quotations are evidence checks, not proof of correctness.

## Reusable implementation

`model_backend.model_json(images=...)` supports opt-in PNG attachments with version3 content-addressed identity, preserved input bytes and submission-modality receipt. Existing text request identities remain unchanged. Isolated Codex receives copied image files through --image. Cache verification checks exact image hashes and matching submission and successful response receipts, in addition to schema/request identity. No image is accepted by a backend path that cannot consume it.

`scripts/verify_reference_source.py` implements one blind reading and one separate verification with no automatic repair loop. It checks row coverage/uniqueness, exact four-cell comparison, source-supported mapping flags, locators and a verbatim mapping quotation present in supplied original text. Null/ambiguous/mismatched evidence fails closed. `protocol/extensions/reference_source_verification_v1.md` records the frozen policy.

`scripts/validate_reference_receipt.py` replays the decision against actual model request/response artifacts, exact image/source bindings and reference/mapping digests. It catches a forged decision or changed output instead of trusting an attestation alone. The opt-in evaluator now performs that replay for declared model receipts, including invalid receipts. An invalid source-verification verdict is different from a corrupted receipt: this receipt's integrity checks pass while its scientific verification remains false.

Official image-input documentation was checked at [OpenAI developer commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli), alongside local `codex exec --help` confirmation of --image.

## Preserved evaluation and tests

A separately frozen read-only successor in `evaluation_v3` consumed the actual negative receipt and manifest. Evaluator code `4d6a1a27c0bb48daaca1ba2768d325c0b732aecefad1796cd32356624b596e15`; exit0. It validated two actual response receipts and preserved all163original HCQ run files. All source-model manifest pins remained unchanged. Numerical/report coverage remain true, observed ORCHID denominator differences remain, verified overall input/contributor agreement stays unknown, and scoped reproduction remains false. Original scientific result and historical comparator outputs are untouched.

283tests pass; F/E9 lint and whitespace checks pass. New tests exercise actual image attachment plumbing with controlled adapter responses, image/hash/submission tampering, blind-request target separation, forged verification decisions, duplicate/missing/illegible rows, null cells and altered reference cells despite a positive verifier. Controlled tests are distinguished from the two actual authenticated source-reading calls.

## Next concrete step and limits

Supply the original supplement caption and sensitivity-table context with exact archive/text locators, and correct the proposed image locators to Dubée2021/Ulrich2020/Self2020 in a separately versioned successor contract. Before another execution, specify distinct blocking problems versus nonblocking source discrepancies in the generic verifier schema; do not retroactively reinterpret this receipt or tune accepted cells. This would address a demonstrated reporting/adjudication ambiguity while preserving the current conservative failure. No unchanged numerical rerun is needed.

This is evaluator-only, developer-assisted historical subgroup validation. It does not establish whole-review reproduction or prospective validation. Source discovery/access and published-estimand qualification still require further autonomous workflow work; Alabed/Popp unresolved evidence remains unchanged. The overall project goal is incomplete.

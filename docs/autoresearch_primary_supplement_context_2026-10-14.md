# Primary-study supplement context integration — 14 October 2026,22:27UTC cycle

Normal primary-supplement ingestion now exposes ordered DOCX/table/image context to the document text used by scientific extraction. The versioned source-upgrade CLI was actually exercised on Johnston2021, PMID33681731/PMC7912360, using its original `mmc1.docx` from the preserved article-specific HTTP200 supplementary archive. The replay produced68orderedblocks,8tables and12distinct embeddedimages. Every block locator appears in ordinary consumer text; all image/raw/context hashes match.

This is a source-autonomy improvement, not a new scientific reproduction. No model calls, network requests or numerical reruns occurred. Johnston's household randomization and missing supported hospitalization cluster-adjustment inputs remain unresolved for the quantitative engine; richer source representation does not invent those inputs.

## Implemented path

`scripts.supplements.augment` now invokes ordered context extraction for DOCX attachments on both direct and original-archive routes. It appends locatable paragraphs and table cells to `document.text`, records image relationship IDs/member names/hashes, and writes content-addressed original image assets plus a structured context manifest. Images are explicitly marked pixels-preserved/not-transcribed. Adjacency is preserved without assigning nearby text as a caption. This prevents unused-sidecar-only output while retaining a truthful boundary: textual extraction can see where image evidence exists, but cannot silently treat unread pixels as numerical data.

`scripts.docx_evidence` now bounds compressed/uncompressed bytes and archive member count; rejects duplicate members/relationships, entities, unsafe relative/absolute/backslash paths and missing relationships; and records external images without fetching them. Assets use content-derived filenames. It preserves table rows/cells, inline formatting text, tabs/breaks and paragraph order. The parser policy, original DOCX hash and each relationship/member locator remain explicit.

`scripts.upgrade_supplement_source` copies a pinned original source into a new output, checks original JATS PMID/PMCID and text hash, imports the preserved article-specific archive only when URL/status/hash match its original receipt, then calls normal augmentation with network disabled. It retains source snapshots, original receipt and cache provenance. A previous augmented source is rebuilt from its retained primary snapshot only in the new destination. Existing output reuse is rejected; old cached sources are never rewritten. The source-stage status upgraded is distinct from scientific review completion.

Original reviewed-source figures or target values were not imported. The actual original source link was `https://pmc.ncbi.nlm.nih.gov/articles/PMC7912360/bin/mmc1.docx`; the retained archive is `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7912360/supplementaryFiles`.

## Actual attempts and provenance

The first frozen attempt, `data/benchmarks/johnston_context_upgrade_v1`, failed before destination creation because the XML guard rejected the original JATS external DOCTYPE. This is a demonstrated compatibility defect, not an inaccessible source. Its code/receipt/log remain preserved.

A separately frozen successor allows a normal external JATS DOCTYPE without fetching/resolving its external DTD; entity declarations remain forbidden. The same original source then passed normal augmentation:

- `data/benchmarks/johnston_context_upgrade_v1_retry1`.
- Code `fb1b72ce279a8560953014323877ec8468eea3b8455a2a5cfa2ba2a98c9ca5af`.
- ExecutionPID17180, completed22:32:07UTC, exit0; no active runner.
- Original archiveSHA256 `8fd42e7584ffbfb09880d6b2998c036a4d367a17da006a1d2e124ffbf6fe7ce0`.
- DOCXmember `mmc1.docx`, SHA256 `53f8835bcb96f5caefab909a181fb6d3f89c2d15560516c34e833aa3d8077f9e`.
- ContextSHA256 `ea8ca0bb340f14d15c2e7fa6a6410a17b738ae883e3f46db26444df94653d157`.
-7pinnedoriginal/source-policy files unchanged; source text grows to68,954characters only in the successor directory. Output/source hashes are in `source_upgrade_manifest.json`; independent checks in `context_audit.json` and `preservation_audit.json`.

The source upgrade uses preserved bibliographic acquisition and originals; the helper did not perform a new download or claim the import receipt was a new network response. Direct URL cache absence is retained before the validated archive fallback. No prior scientific effect/completion decision changed.

## Validation and next step

309tests pass; F/E9 lint and whitespace checks pass. Tests cover normal direct/archive augmentation, image asset/context hashes, actual consumer text, unsafe archive paths, external images, duplicate/oversized ZIPs, immutable source upgrades, wrong primary identity, existing-destination refusal and benign external JATS DOCTYPE versus forbidden entity declarations. Controlled tests forbid network calls; the actual frozen replay ran cache-only.

Policy: `protocol/extensions/primary_supplement_context_upgrade_v1.md`. Reproducible CLI is `scripts.upgrade_supplement_source MANIFEST --output NEW_DIRECTORY`, run from a hash-pinned bundle. Preserve existing success/failure outputs. Any subsequent scientific use must pin the upgraded source hash under a new execution contract.

Next focus should remain original-source/estimand autonomy: connect explicitly untranscribed primary image markers to a bounded source-inspection queue and validate image-evidence admission on a method-compatible original outcome. Do not rerun Johnston as an independent-person trial or assume an ICC. An image workflow must retain original-pixel locators and uncertainty rather than fabricate textual quotations. The current pipeline exposes the evidence but does not yet autonomously transcribe all embedded images.

This is engineering plus real primary-source replay, not evidence of whole-review or prospective validation. Earlier benchmark results and Alabed/Popp access limitations remain unchanged; overall project objective incomplete.

# Autonomous meta-analysis implementation and benchmark results

The supported workflow now runs unattended through search, screening, lawful public-source acquisition, source-backed extraction, trial-family checks, synthesis, draft risk-of-bias assessment and reference comparison. **Neither historical review was reproduced.** Both real evaluations finished with incomplete evidence, not a credential failure or an unfinished processing queue. No review, acquisition or model process is intentionally left running.

These are reference-separated **development benchmarks**, with warm caches from earlier autonomous runs. They are not held-out validation. The original evaluator-assisted first pass is preserved separately. Frozen operational protocols also have documented differences from the published reviews; these results do not isolate extraction accuracy from search, eligibility, estimand and source-access differences.

## Observed results

| Frozen case | Screened records | Full-text attempts | Documents parsed | Independent effects | Unresolved records | Historical reproduction |
|---|---:|---:|---:|---:|---:|---|
| Ma 2013, NAFLD ALT | 972 | 90 | 30 | 2 | 64 | No; reference k=4 |
| Li 2016, T2D fasting glucose | 2,180 | 49 | 31 | 2 | 28 | No; reference k=9 |

Documents include ineligible reports and conference collections; they are not counts of included trials. Missing full-text candidates are not assumed to be eligible studies. Both final queues have zero pending segments.

| Case | Incomplete primary-source estimate (95% CI) | Published target (95% CI) |
|---|---|---|
| Ma, fixed-effect endpoint MD | −9.80064 U/L (−20.23712, 0.63584), k=2 | −23.71 (−33.46, −13.95), k=4 |
| Li, random-effects endpoint SMD | −0.589659 (−0.905940, −0.273378), k=2 | −0.61 (−0.92, −0.30), k=9 |

The similar Li point estimates are not reproduction: only one observed contributor belongs to the nine-report reference set. A separate replay of published forest-plot inputs reproduces their rounded arithmetic, but it is secondary-source calibration, not independent extraction or evidence that those inputs are correct.

Published reviews: [Ma 2013](https://www.wjgnet.com/1007-9327/full/v19/i40/6911.htm) and [Li 2016](https://pubmed.ncbi.nlm.nih.gov/27368052/). Exact observations and comparisons: [`benchmarks/findings/final_suite.json`](../benchmarks/findings/final_suite.json).

## What was implemented and exercised

The new suite verifies frozen protocol and reference hashes. Review and risk-of-bias models do not receive reference answers; comparison occurs after execution. It supports the existing authenticated Codex CLI and an explicitly configured Responses API backend. No API credits were purchased.

Source discovery uses indexed public links, bibliographic/DOI services and a bounded isolated web-search fallback. Accepted PDFs, JATS and scholarly HTML require source-identity checks. Retrieval has finite request/byte/time budgets, durable failure records, rate-limit handling and transient-error backoff. The current PMC Cloud route verifies article identity, versions and object checksums. Linked PDF/DOCX/text supplements preserve raw hashes and unavailable/unsupported formats; actual remaining supplement attempts failed rather than becoming invented measurements.

Collections are segmented without character truncation, retaining page/region and text-hash provenance. The real 556-page collection and newly recovered 429-page EASD collection were processed. A nonzero PDF page origin exposed and then verified a geometry correction. Small proceedings also resolve their constituent leads rather than becoming one pooled trial. Ambiguous or unindexed leads remain unresolved.

Trial-family checks require source evidence and a separate model verification before pooling. The optional multiarm extension combines verified disjoint arms without duplicating a control; its real-source component was exercised separately and remains disabled in these frozen benchmarks. The runner supports reported endpoint means/SDs in independent parallel comparisons, with fixed MD or Hedges SMD/DL random-effects synthesis. It does not silently substitute SEs, convert medians, impute unavailable reports or mix score definitions.

Restarts preserve prior failures, code snapshots and model request/response artifacts. A validated continuation helper copies complete raw search provenance and input caches, excluding accepted effects and reference outputs. Cached screening cannot be relabeled as a different protocol/backend/model. Numerical reruns clear stale synthesis and risk-audit summaries while archiving them.

## Risk-of-bias drafts

All four final outcome-specific drafts passed exact-source and separate model checks. Aller, Malaguarnera and the kefir trial were drafted as “Some concerns”; Firouzi was drafted as “High”. These are **automated drafts, not expert-validated RoB2 assessments**. They use the repository's abbreviated template, assess assignment to intervention and do not alter any inclusion decision, pooled value or weight.

The audit retains earlier failed quotations and differing draft judgments. An additional reading-order view of the same verified PDF improved quotation fidelity without modifying the numerical source. The legacy confidence field is explicitly null because no probability calibration exists. Assets and requests are versioned under each run. The audit does not independently retrieve trial protocols/registries and does not implement GRADE. The separate policies are [`rob2_draft_v1`](../protocol/extensions/rob2_draft_v1.yaml) and [`rob2_draft_v2`](../protocol/extensions/rob2_draft_v2.yaml).

The [Cochrane handbook](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-08) explains why risk-of-bias assessment is specific to a result and effect of interest. Model agreement does not replace that methodological judgment.

## Why reproduction remains unresolved

- **Unavailable original reports.** Ma's Vajro report, PMID 21505361, remains unavailable through the attempted lawful routes. Five retained reports in Li's twelve-report review set remain inaccessible: PMIDs 21700013, 22129852, 24706266, 25196301 and 25300285. The decision exports also retain all non-reference source gaps and failed URLs. Further progress on these gaps requires additional lawful source access or supplied originals, not more speculative extraction.
- **Estimand/reporting differences.** Wong's primary report gives ALT changes, while its secondary report supplies medians/IQRs; neither provides the endpoint means/SDs required by the frozen Ma protocol. Shavakhi has inconsistent analyzed-arm reporting. These were not silently repaired or substituted.
- **Query and comparator differences.** The frozen Li query omits yeast terminology and missed the brewer's-yeast report. Its placebo-only rule excluded Bayat's dietary-advice control, although the historical review included it. The original failures remain frozen; a changed search or estimand would be a separately specified sensitivity analysis, not a repaired claim of original reproduction.
- **Apparent reference extraction discrepancy.** Asemi Table 3 and Mazloom Table 2 label dispersion as SE, while Li's forest plot uses identical numbers in SD columns. This requires scientific adjudication; matching an apparent error is not correctness. See the [source-level audit](../benchmarks/findings/li2016_dispersion_audit.json), [Asemi primary report](https://magistralbr.caldic.com/storage/product-files/1151404700.pdf) and [Mazloom primary report](https://pmc.ncbi.nlm.nih.gov/articles/PMC3642943/).

The current system is an executable, tested autonomous workflow for its supported scope, not a validated universal production-review system. One bibliographic database, unpinned default model execution, inaccessible reports, limited design/measurement support and unknown model-training contamination prevent stronger claims. A fresh, explicitly pinned, prospectively specified evaluation with sufficient lawful primary sources is needed for that claim.

## Validation and reproducibility

107 tests passed. Selected static checks passed on 52 changed Python files; `git diff --check` passed. Real authenticated model execution, source acquisition, full collection scans, supplementary-access failures, family adjudication, the multiarm component and the integrated suite were exercised. Unit fixtures are not presented as reproduction evidence.

Both final numerical runs used immutable code hash `720874f2e39f0baddd04c1cf71834a857f8940f96b226c9b610faa23598b7834`. Protocol hashes remain Ma `b81b1cbd59757af13ef764883bd468b9807cef7688ba6b12afe09553c3f21a35` and Li `08f8481c02f3e2496af3894aaf596169e069fd99dce8878b9ac69bc48b0b3b3d`. The final suite exits 2 because reproduction failed; this is an expected scientific result, not an execution crash.

Run a fresh suite:

```bash
.venv/bin/python -m scripts.benchmark_suite --workdir data/benchmarks/new_suite --model MODEL_ID --max-rounds 8
```

Use an available explicit `--model` and a fresh work directory for a separately pinned evaluation. Re-evaluate the saved completed runs without model calls:

```bash
.venv/bin/python -m scripts.benchmark_suite --existing-runs benchmarks/findings/final_run_map.json --workdir data/benchmarks/final_evaluation
```

Full local audits: [Ma](../data/benchmarks/final_suite_v1/ma2013_nafld_alt/b81b1cbd5975/review_export/review.md) and [Li](../data/benchmarks/final_suite_v1/li2016_t2d_fbg/08f8481c02f3/review_export/review.md). Raw searches, source files, failed responses, model artifacts and prior attempts remain under ignored `data/benchmarks`; they are not redistributed with the tracked code. The original 2014–2024 project scope and original data are preserved. All changes remain reviewable and uncommitted in the existing checkout.

Scientific readiness was reassessed on 2026-10-13 in [the separate readiness audit](benchmark_readiness.md); original benchmark observations above remain historical and unchanged.

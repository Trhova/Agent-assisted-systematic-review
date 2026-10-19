# Scientific evaluation readiness, 2026-10-13

Neither original development benchmark reproduced its historical review. The new read-only evaluator produces `benchmarks/findings/readiness_v1.json` without changing protocols, targets, source evidence or historical observations. Its 16 actions cover the reference-review reports and two case-level contracts per case; this is not the whole retained-candidate backlog. No new model execution or broad benchmark was launched.

## What the audit separates

| Case | Original search coverage of review reports | Available source texts | Reference outcome contributors pooled | Actions |
|---|---:|---:|---:|---:|
| Ma 2013 | 4/4 | 3/4 | 2/4 | 4 |
| Li 2016 | 11/12 | 5/12 | 1/9 | 12 |

Li's twelve review reports are not twelve independent FBG trials. The nine outcome contributors are separately identified. Source presence does not establish eligibility, numeric usability or extraction correctness. The accepted kefir contributor is outside the frozen nine-report target; similar pooled values cannot establish reproduction.

The comparison code now separates arithmetic matching from semantic agreement. Outcome, unit, effect measure, endpoint/change definition and model must agree among protocol, reference and every observed effect. Missing reference `value_type` is an **unknown adjudicated comparison contract**, not proof that all inputs differ. Consequently these unchanged historical references cannot earn a scientific-reproduction pass until a separately evidenced versioned contract exists. Finite targets, nonnegative finite tolerance and valid reference interval/count are required. New suite execution requires an explicit model identity; old unpinned runs remain evaluable historical development evidence.

## Evidence and next actions

- **Lawful source access:** Ma PMID 21505361; Li PMIDs 21700013, 22129852, 24706266, 25196301 and 25300285. Obtain original reports through an actually new lawful route or supplied copies. Repeating failed URLs supplies no evidence. The full retained queue remains in each original run.
- **Search coverage:** PMID 24319552 is absent. The frozen Li query omits yeast terminology. Audit the query against the [published Li review](https://pubmed.ncbi.nlm.nih.gov/27368052/) in a separate development definition. Do not inject the known answer set into a supposedly independent search evaluation.
- **Eligibility differences:** PMID 26955460 was excluded for a dietary-advice comparator; PMID 23967428 was excluded because its primary report describes inactivated yeast. These are not retrieval failures. Widening placebo eligibility or treating nonliving yeast as a probiotic needs an explicit separately justified question, not numerical target matching.
- **Endpoint/change:** Wong, PMID 23396737, reports change statistics in its primary Table 2 and no usable endpoint mean/SD pair under the frozen Ma definition. The [Ma review](https://www.wjgnet.com/1007-9327/full/v19/i40/6911.htm) does not supply an adjudicated endpoint-only contract. A future change-score analysis must be separately specified; do not silently mix it into the endpoint SMD analysis or infer missing change SDs.
- **Supported derivation extension:** Asemi PMID 23899653 Table 3 explicitly labels SE and gives n=27 per arm ([primary PDF](https://magistralbr.caldic.com/storage/product-files/1151404700.pdf)); Mazloom PMID 23645956 Table 2 labels SE, and Table 1 labels placebo n=18 and treatment n=16 ([primary report](https://pmc.ncbi.nlm.nih.gov/articles/PMC3642943/)). Cached primary XML/table text was directly inspected for Mazloom because the live PMC page returned a browser challenge. These reports are not unusable in principle. [Cochrane Handbook 6.5.2.2](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06) supports SD=SE×sqrt(n) for an unadjusted within-arm mean SE with the correct analyzed arm denominator. A future explicit extension must retain original SE, transformation, denominator evidence, table locator and source hash, and check denominator applicability to the endpoint. This is deterministic derivation, not imputation. It remains prohibited by the original reported-SD-only extraction protocol. The published forest's identical SE-as-SD inputs remain a separate reference discrepancy; reproducing that mistake is not correctness.
- **Ambiguous originals outside the reference-only queue:** Shavakhi and the Mohamadshahi reports retain conflicting or unspecified analyzed-arm denominators in the original extraction audit. A rule allowing SE conversion does not resolve these. Preserve unresolved status until source-backed denominator resolution exists.

No revised pooled sensitivity is ready: access gaps and the comparative contract are still unresolved. The supported derivation extension is a concrete engineering next stage, but a post-hoc development study using these familiar papers cannot become a fresh held-out validation.

## Prospective evaluation path

Use an access-qualified, prospectively frozen primary-report corpus for a first bounded validation of the supported parallel continuous-outcome workflow. Before model execution, an evaluator independent of extraction must lock the question, outcome/timing, comparator, endpoint/change convention, source-unit conversion and optional SE transformation rules; lawful primary files and identities; a pinned model; code and protocol hashes; tolerances and failure categories. Require at least two independent usable trials per quantitative case, and enough distinct cases to exercise planned coverage rather than announcing general validation from one pair. Inventory the actual lawful reports before choosing a sample size or launch budget; there is currently no verified held-out corpus to launch.

Build source-backed numeric gold independently with adjudicated arm denominators and trial-family membership, keep it outside model context, and score eligibility, retrieval, arm values, transformations, source citations and pooled arithmetic separately. Record every unavailable/ambiguous report in an access ledger rather than counting it as an extraction error. An access-qualified corpus estimates performance conditional on accessible reports; it cannot support an unrestricted literature-retrieval claim. Evaluate search separately on prospectively frozen questions with all denominators reported. Training-data contamination remains unknown even with this separation. Neither unit tests nor published-forest replay establishes independent reproduction.

Regenerate the offline audit:

```bash
.venv/bin/python -m scripts.benchmark_readiness --output benchmarks/findings/readiness_v1.json
```

For any future new benchmark execution pass a verified available explicit `--model MODEL_ID`. This is a gate, not a recommendation to rerun the unchanged failed suite.

## Verification

The full local suite passed 123 tests. After formatting the new modules, their 16 focused tests passed; the new modules/tests passed full Ruff checks, and selected correctness lint passed across all seven changed Python files. Whitespace checks passed. Recomputing the real-case read-only diagnostic produced byte-identical JSON. Frozen protocol/reference checksums match the original suite; the twelve historical run inputs hashed by this diagnostic were unchanged on recheck. No source, status, accepted-effect or synthesis artifact was rewritten. Readiness Booleans are explicitly historical-development restrictions, not a general prospective launch validator.

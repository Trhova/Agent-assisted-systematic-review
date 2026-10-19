# Autonomous development execution, 13 October 2026

The system recovered **all three primary-trial effects in [Rawat 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8552785/)'s published intravenous-vitamin-C hospital-stay subgroup**. The estimate is **SMD −0.295734 (95% CI −1.389273 to 0.797805)**, versus the published **−0.30 (−1.39 to 0.80)**. Coverage is 3/3, with no missing or extra pooled trials; protocol/reference/effect semantics, including intravenous route, agree. The frozen absolute tolerance was 0.02.

The overall benchmark deliberately remains **not reproduced / incomplete**: a fourth, newly retrieved candidate has an unresolved administration route. Numerical agreement is not silently promoted to a complete-review claim. This is a post-hoc development evaluation of a published subgroup, selected after inspecting the broader case, not a held-out success or reproduction of every outcome in the full review.

## Actual runs

| Execution | Screened | Full texts attempted | Independent effects | Unresolved | Observation |
|---|---:|---:|---:|---:|---|
| Rawat all-routes initial | 230 | 8 | 3 | 3 | Conversion worked; PDF quotation and completion-status issues retained |
| Rawat all-routes, quote/status repair | 230 | 8 | 3 | 2 | Quote repair abstained on interleaved denominator narrative |
| Rawat all-routes, column-view repair | 230 | 8 | 3 | 2 | Denominator legible; undefined ± dispersion correctly rejected |
| Published Rawat IV subgroup, fresh execution | 231 | 12 | 3 | 1 | All published subgroup effects recovered; extra candidate route unresolved |

All executions used explicit `gpt-6-astra` through the existing authenticated Codex backend, with three-round bounds. Each protocol, target, model and code identity was recorded before its execution. Original failed protocols/runs and earlier Ma/Li artifacts are unchanged. The fresh IV run reused only an identical-query raw bibliographic snapshot and primary sources; screening, extraction, verification and RoB model calls were fresh.

IV run: `data/benchmarks/rawat2021_iv_v1/rawat2021_iv_covid_hospital_stay_v1/64f1fbb555e4`. Frozen numerical code: `e58c5409fb65a07c2aaf9f65b738819e3b66f56e872786d26954ca4f8524b745`. Full comparisons are in `benchmarks/findings/rawat2021_iv_v1_suite.json`; primary values, source hashes and transformations are in `benchmarks/findings/rawat2021_iv_primary_audit_v1.json`.

## Primary numerical evidence

| Trial PMID | Analyzed n, treatment/control | Treatment mean / SD | Control mean / SD | Source statistic |
|---|---:|---:|---:|---|
| Kumari 33409026 | 75 / 75 | 8.1 / 1.8 | 10.7 / 2.2 | Reported mean/SD, days |
| Zhang 33420963 | 27 / 29 | 35.0 / 17.0 | 32.8 / 17.0 | Reported mean/SD, days |
| Siahkali 33573699 | 30 / 30 | 9.213 / 3.892101 | 7.5695 / 6.227362 | Estimated from explicit median/Q1/Q3, days |

Siahkali reports treatment median 8.5, Q1 7, Q3 12; control median 6.5, Q1 4, Q3 12. The optional Luo mean / Wan SD estimator preserves these originals, denominator evidence, units, exact quotations, source locator/hash, transformation identity and estimated flags. It assumes an approximately normal distribution. Conventional Hedges-g variance does not include the additional uncertainty from estimating arm summaries. The review's forest rounds intermediate estimates; this execution retains full precision.

The prespecified reported-statistics-only sensitivity excludes Siahkali: **k=2, SMD −0.593593 (−1.979596 to 0.792410)**. It is exported separately and is not compared as the complete published target. Both analyses' intervals cross zero; this does not establish equivalence or clinical effectiveness. The main analysis has I² 94.154% and DL τ² 0.877040.

## Evidence-backed discrepancies

The broader all-routes target is −0.23 (−1.04 to 0.58), k=4. All four reference full texts were obtained. Hakamifard's publisher PDF defines hospitalization until discharge/death and establishes 38/34 analyzed participants, but its hospital-stay `±` values are not labeled SD or SE. SD labels on baseline tables do not resolve another outcome's statistic. Independent verification rejected the values; the published review's interpretation was not substituted for primary evidence.

The additional quercetin/vitamin-C/bromelain report, PMID 34803451, has ambiguous total-hospitalization follow-up, conflicting enrollment/completer counts and min/max ranges. Its primary methods and NCT04377789 registry do not explicitly identify the vitamin-C administration route. It was initially described as oral from context; that description was corrected and is not used as an exclusion. The IV protocol's frozen explanatory version note retains the earlier label for audit; the operative rule and actual model decision require primary route evidence.

This report was published in August 2021 but its MED entry was created on 22 November and Europe PMC first indexed it on 30 November, after the review's 18 September cutoff. That supports a historical MED-availability explanation, not certainty about the review's other databases. The current-index query retains it. See `benchmarks/findings/rawat2021_additional_report_index_history.json`.

## Engineering delivered and checked

- Optional source-audited quartile estimation; reported-only sensitivity and visible estimated-statistic reporting.
- Frozen bibliographic-only hand-search leads, passed through ordinary source/eligibility checks.
- Bounded quote-only repair with original/rejected text retained, never altered numerical values.
- Completion classification based on actually validated required inputs; contextual missing-statistic notes remain in the audit.
- General mixed-layout PDF column regions with original text/PDF retained, source hashes and page bounding boxes. No trial-specific table coordinates.
- Route agreement across protocol, reference and effects; enforcement of suite model/backend pins.
- Bounded RoB draft revision after failed independent verification, followed by an independent recheck. The Li continuation now has 4 source-checked drafts, 0 unverified; synthesis, trial families and benchmark comparison are byte-identical to the prior run. The fresh Rawat IV run has 3 source-checked drafts, 0 unverified. These are not expert-validated RoB2 judgments and never alter pooling.

Validation: **166 tests passed**, selected fatal-error/import-order checks passed, eight frozen case protocol/reference hashes verified, and primary-source hash/model-identity checks passed. Reference paths and numerical tolerance fields were absent from extraction requests. These checks do not rule out model training-data familiarity. The exact initial/repair observations remain separate, including failures.

## Reproduce and inspect

```bash
.venv/bin/python -m scripts.benchmark_suite \
  --suite benchmarks/suite_rawat2021_iv_v1.yaml \
  --workdir data/benchmarks/rawat2021_iv_v1 \
  --backend codex --model gpt-6-astra --max-rounds 3
```

This resumes auditable caches and archives previous compiled outputs; use a fresh work directory for new independent execution. Exit 2 is intentional for this unresolved evidence set. Inspect `status.json`, `benchmark_comparison.json`, `reported_statistics_sensitivity.json` and `review_export/review.md`; exact source/model artifacts remain in the run directory. The broader comparison uses `benchmarks/suite_rawat2021_v1.yaml` and `data/benchmarks/rawat2021_v1_repair2`.

Remaining limits are concrete: the original six inaccessible Ma/Li reports and their other reported-data/estimand problems; Hakamifard's unidentified dispersion; the additional candidate's unconfirmed route and outcomes; single-database accessible search plus disclosed hand-search leads; abbreviated, non-expert-validated RoB drafts; no GRADE or held-out validation. No source/model process remains intentionally running. No external messages, purchases, automation, commits or changes to other projects were made.

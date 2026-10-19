# Hospital-treatment mortality development evaluation — 14 October 2026

The frozen autonomous review screened 94 records, accepted three independent randomized trials, and completed with zero unresolved records. Fixed Mantel–Haenszel RR was **0.877845177 (95% CI 0.578064555–1.333090133), I²=0**. This agrees with the published rounded sensitivity result 0.88 [0.58, 1.33], but exact input reproduction fails for two ORCHID denominators. The suite completed14:54:42UTC, exit0, with3 source-checked RoB drafts and0 unverified. Its configured comparator reports reproduced=true; this means coverage/semantic/rounded-target agreement within the frozen subgroup contract, not exact input agreement or whole-review reproduction.

This is a developer-assisted, post-hoc development evaluation of the published peer-reviewed, predominantly hospital-treated mortality sensitivity in [PMC8403035](https://pmc.ncbi.nlm.nih.gov/articles/PMC8403035/), not the complete 14-trial review, a pure inpatient effect, or held-out prospective validation. Source qualification and manual acquisition preceded protocol freeze. Published answers were evaluator-only, excluded from model screening/extraction requests. No model request cache was seeded.

## Primary inputs and discrepancies

| Trial | Primary treatment | Primary placebo | Mortality horizon |
|---|---:|---:|---|
| HYCOVID, PMID33813110 | 6/124 | 11/123 | Day 28 |
| TEACH, PMID33134417 | 7/67 | 6/61 | Day 30 |
| ORCHID, PMID33165621 | 25/241 | 25/236 | Day 28 |

The primary ORCHID mortality analysis excludes one participant per arm whose vital status was unknown. The published forest uses randomized denominators 242/237. A separately executed read-only cell audit reports both differences; no primary input was changed to match the review. Reference cells were manually transcribed from the preserved supplementary Figure S15 and are not independently model-validated. Numerical tolerance alone cannot establish extraction agreement.

HYCOVID includes three ambulatory participants among 250 randomized; the frozen protocol explicitly accepts predominantly hospital-recruited whole cohorts and does not manufacture an inpatient-only subset. HYCOVID consent withdrawals and ambiguities in follow-up ascertainment remain in extraction limitations. TEACH retains its explicit reported ITT denominators while documenting 14/11 participants lost to follow-up and four follow-ups outside the protocol window; unobserved outcomes were not asserted to be survival. The common estimand is reported all-cause mortality at 28–30 days, not one identical visit in every trial.

## Candidate qualification and reusable engineering

The earlier outpatient candidate was not pooled. The original Johnston supplement was recovered once from Europe PMC: hospitalization listings lack household linkage, and GEE footnotes concern demographic/risk features rather than an adjusted hospitalization estimate. No supported hospitalization effect/SE or correction inputs were established; no ICC was assumed. These findings are preserved in `data/benchmarks/johnston_supplement_qualification_v1`.

The hospital comparison was chosen for accessible original reports, independent parallel designs and compatible published fixed-MH methods. The initial publication-type search missed TEACH and was preserved without model execution; the separately frozen text-based placebo/blinding search includes all three contributors. The peer-reviewed cutoff excludes the broader review's preprint contributors. This restriction and mixed HYCOVID population are explicit scope limitations, not undisclosed exclusions to improve agreement.

ORCHID was recovered from a public healthcare-provider PDF collection. The new generic `import_source_pdf --pages FIRST LAST` route preserves the downloaded collection and HTTP receipt, then links its hash to exact original-article pages 8–19 and the derived PDF hash. Only those original pages enter extraction; preceding unrelated articles do not. A test exposed initially missing derivation metadata; the unused failed import and correction receipt remain preserved. Corrected `ORCHID_primary_v2` is the only imported execution source. TEACH/HYCOVID full primary JATS was available; some supplements failed and remain explicit limitations.

The new `benchmark_input_audit` compares source-accepted binary cells with separately evidenced published cells, rejects ambiguous duplicate mappings and invalid counts, checks semantics/evidence hashes, and writes outside the original run. Its real execution found the ORCHID differences despite rounded pooled agreement. It does not change eligibility, completion or numerical decisions.

## Frozen execution and reproducibility

- Run: `data/benchmarks/hcq_hospital_mortality_v1/hcq_hospital_mortality_development_v1/b37d49d057fc`.
- Protocol: `benchmarks/protocols/hcq_hospital_mortality_v1.yaml`; digest `b37d49d057fcf90165cb3465e466d457481dc1859c570b077dd70eaa7b802392`.
- Scientific/suite code: `b895c2ec7b167ff92a14b0486f212f2d282a353efd23ab160b5a718af6d93dd5`.
- Launch: `.venv/bin/python data/benchmarks/hcq_hospital_mortality_v1/launch.py`; existing directory is preserved, not an invitation to rerun.
- Launcher PID7784, suite7785; started14:43:35UTC; review finished14:51:13UTC. Explicit backend `codex`, model `gpt-6-astra`; worker Medium, nested reasoning effort backend-default/unpinned.
- Two bounded rounds, cache-only source acquisition, no web discovery, no outer recovery/rerun. Source manifest, protocol, model, estimator, target/tolerance and non-Python RoB assets were pinned before launch.
- Separate post-run audit outputs and frozen auditor identity: `data/benchmarks/hcq_hospital_mortality_input_audit_v1/{execution_receipt,artifact_audit,cell_audit_verified,verified_execution_receipt,final_provenance_audit}.json`.
- Validation: 255 tests pass; F/E9 lint and whitespace checks pass. Artifact audit valid with exact synthesis replay; cell agreement false for the documented two denominator differences.

The result establishes a functioning supported binary review path on one complete published quantitative subgroup, with original-source qualification assistance. Single-database search, source-access work, post-hoc benchmark familiarity, incomplete supplements and outcome follow-up limitations prevent a general autonomous whole-review claim. Alabed's five report-access gaps and Popp's three unresolved records remain unchanged.

## Final execution audit and next work

All54 pinned original inputs/assets remain unchanged. All28 successful request directories passed identity/schema/response-provenance verification:22 review and6 RoB adapter receipts, no imported model cache and no outer retry. CLI-internal transport requests are not counted as adapter invocations. The separate final input auditor code is `c4aae673bb1980412d600441ed64bbcd3280ed2e978bc2970a9232dd40cab18b`; its audit preserved125 non-RoB run files byte-for-byte. This post-run audit code is distinct from the frozen scientific run. All execution processes exited.

The largest remaining autonomy limitation is obtaining and qualifying original sources and identifying the published estimand without developer intervention. This cycle improved reusable collection import, but initial source discovery and case scope still required manual research. A useful next implementation is integrating evidenced per-trial reference-cell reconciliation into separately versioned evaluator contracts so configured pooled agreement cannot be summarized as unqualified reproduction when inputs disagree. Preserve this original comparator/result; add prospective input criteria only in a new evaluation version. No additional numerical rerun is needed to establish the ORCHID discrepancy. Subsequent scientific validation should broaden beyond familiar manually qualified subgroups, with access and scope qualification recorded before execution.

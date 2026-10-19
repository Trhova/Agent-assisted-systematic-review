# Binary-outcome extension and Popp2021 development evaluation

The migraine-severity candidate did not qualify: Gonçalves2016 reports endpoint SDs and change means without change SDs; the second primary report was inaccessible through the checked publisher route. Substituting endpoints or assuming a baseline–follow-up correlation would change the published question. Raw responses remain in `data/benchmarks/puliappadamb2022_qualification_v1`.

A different, method-compatible case was qualified: Popp2021, *Colchicine for the treatment of COVID-19*, DOI10.1002/14651858.CD015045, hospitalized all-cause mortality up to28 days. The complete published quantitative contributor set is GRECCO19 (PMID32579195) and RECOVERY (PMID34672950). Lopes (PMID33542047) reports discharge-only mortality and belongs to a separate reference outcome. Primary JATS/texts are accessible for all three. This is one complete quantitative outcome, not reproduction of every outcome or every search database in the Cochrane review.

The source-led contract preserves the review's21-day/discharge and28-day follow-up difference. GRECCO19 reports three deaths after intubation plus one sudden ward death in mutually exclusive control groups. The generic event-partition policy requires explicit source support, exact retained components and independent verification. RECOVERY supplies explicit ITT outcome-table denominators and incomplete follow-up; the latter remains a limitation, without inventing missing events or switching to an unidentified denominator. Its reported rate ratio is not substituted for the risk ratio computed from binary counts.

The reference's main mortality analysis uses fixed Mantel–Haenszel RR, with a separately reported random-effects sensitivity. Fixed MH was selected before execution; no result-driven model switch is allowed. `protocol/extensions/binary_rr_mh_fixed_v1.md` specifies scope, zero-cell handling and limitations, citing current Cochrane guidance and its linked RevMan statistical algorithms. `scripts/binary_outcomes.py` implements explicit event counts, log-scale individual effects, RR-scale pooling, original/corrected count audit, noninformative-study ledger and heterogeneity. Extraction, validation, family signatures, synthesis, report export and evaluator input audit support the new rows. Continuous protocols are unchanged.

Validation before launch:193 tests pass; selected fatal/import lint passes. Meaningful new tests cover hand-calculated stratified MH results, reciprocal treatment direction, malformed counts, zero-cell handling, noninformative studies, preserved partitions, schema validation, family signatures and unsupported estimators. These are software checks, not evidence of scientific reproduction.

Prespecified artifacts: `benchmarks/protocols/popp2021_hospital_mortality_v1.yaml`, `benchmarks/suite_popp2021_v1.yaml`, source manifest and bibliographic-only preprint/final lead under `benchmarks/sources/`. Raw qualification files and retrieval failures remain under `data/benchmarks/popp2021_qualification_v1`; failed HTTP bodies are not valid primary documents. The final RECOVERY companion report is explicitly allowed for the original cohort, linked to its18May2021 preprint; its actual final publication date is preserved.

Execution launched02:28UTC14October2026, PID18704, explicit `gpt-6-astra`, backend `codex`, three bounded rounds. Worker Astra medium; nested reasoning effort backend-default/unpinned. Code `fb3dd76fca92bc1767cd9da6d4e3ae4ff2840ede9f4f2e0ee703961ffbbda2bd`, protocol `d2cc93475219520b598aac86f7dca809b98468d32ba2518ec2db5215e2b35d95`. Primary caches only were seeded; fresh decisions and extraction do not receive reference numerical targets. Preregistration, launch and raw artifacts are under `data/benchmarks/popp2021_v1`.

```bash
.venv/bin/python -m scripts.benchmark_suite --suite benchmarks/suite_popp2021_v1.yaml --workdir data/benchmarks/popp2021_v1 --backend codex --model gpt-6-astra --max-rounds 3
```

This command identifies the actual run; do not submit it again while the runner is active. Preserve the current run for continuation and use an isolated new version for changed scientific contracts.

The frozen reference contains a DOI suffix typo. `benchmarks/findings/popp2021_reference_citation_erratum_v1.json` records the correct DOI without modifying the frozen reference or numerical target. The run status also retains a legacy continuous-outcome limitation sentence; binary execution is established by its protocol, schemas and actual effect artifacts, not that stale description.

Execution finished; suite PID18704 has exited.132 records were screened,9 full texts attempted,2 independent effects accepted,4 records unresolved. Fourteen review model requests and four RoB requests used explicit Astra. The two RoB drafts are source-checked, with zero unverified drafts; this is not expert RoB validation or GRADE.

| Primary trial | Colchicine deaths/N | Control deaths/N |
|---|---:|---:|
| GRECCO19 |1/55|4/50|
| RECOVERY |1173/5610|1190/5730|

Total11,445 participants. Fixed MH RR **1.004034533** (95%CI **0.934579543–1.078651198**), I²45.264%. The original trial count, numerical estimate/interval and protocol/reference/effect semantics agree with the published main mortality comparison (rounded1.00[0.93,1.08]). Both primary source checks passed, families are independent, and no additional trial was pooled. The conclusion agrees: this analysis does not establish a mortality benefit. Follow-up differences and RECOVERY missing-outcome uncertainty remain material limitations.

**Overall benchmark remains not reproduced:** Lopes has no established scheduled21–28-day mortality assessment; three abstract-free letters (PMIDs32445400,32337546,33769172) could not be fully classified through the runtime's acquisition routes. The strict completion gate remains false despite complete published quantitative contributor coverage. This is stronger than arithmetic calibration, because model extraction recovered primary counts independently, but is still incomplete autonomous review execution. No gate was relaxed.

Artifact-consistency audit passes with zero issues; independent evaluator-only rational-arithmetic replay matches the pooled RR exactly (`benchmarks/findings/popp2021_binary_replay_v1.json`; CI uses1.96 rather than the runtime's exact normal quantile). All11 configured protocol/reference pairs still verify, and whitespace checks pass. Actual review export, source quotes, count components, family decisions, synthesis and comparison are in the run directory. `suite_report.json` is the machine-readable result.

Postlaunch lawful discovery recovered PMID32445400's original two-page PDF through a newly found public archive URL; it describes therapeutic rationale and planned studies rather than trial results. Raw PDF, extracted text and receipt are preserved separately in `data/benchmarks/popp2021_followup_sources_v1`. It was not retroactively injected into this run or used to rewrite its missing-fulltext result. Remaining letter discovery did not produce another full source; do not retry unchanged URLs.

Next useful iteration: integrate newly discovered original source into an isolated continuation with a frozen acquisition manifest; pursue distinct source routes for remaining letters if available. Improve generic reporting to distinguish missing full text, eligible trials without the specified outcome, and accepted counts with missing-follow-up limitations. Establish any adjudication policy from primary evidence before execution; do not relabel Lopes or weaken completion just to pass. Binary random-effects, multi-arm and rare-event clinical validation remain unsupported. Several-review validation and held-out evaluation remain unfinished.

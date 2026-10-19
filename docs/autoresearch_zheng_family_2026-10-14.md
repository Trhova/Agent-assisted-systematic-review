# Zheng pulse-pressure qualification and trial-family repair

Bounded cycle following the 14 October 00:13 UTC heartbeat. Sole worker: `/root/meta_analysis_execution`, Astra medium. No model or numerical-review runner was submitted. This cycle produced new primary evidence, a demonstrated runtime repair and an executed before/after integration experiment; it did not produce a new complete-review reproduction.

The candidate was selected because pulse pressure used parallel comparisons and fixed inverse-variance MD, unlike the review's broader outcomes. Exact forest inspection establishes laboratory resting pulse pressure at the end of training (8 weeks for the acquired reports), not the later follow-up or change scores. Figure 5 is preserved as `data/benchmarks/zheng2023_qualification_v1/review_figure5.png`; published numerical targets remain outside screening/extraction.

The publisher PDF of [Ubolsakka-Jones 2017](https://www.nature.com/articles/hr201754.pdf) was lawfully acquired even though its HTML was a subscription preview. Table 2 gives endpoint PP 56±8 versus 65±7 mmHg. Both analyzed groups contain ten participants. Results explain that one control participant excluded from home measurements attended every laboratory session and was included in this report. Thus the review's forest total of 92 is supported for these measurements; its characteristics-table total of 91 mixes in a different measurement population. This is a resolved denominator question, not evidence of an erroneous forest N.

The [2019 author-uploaded primary report](https://www.researchgate.net/publication/333460108_The_effects_of_slow_loaded_breathing_training_on_exercise_blood_pressure_in_isolated_systolic_hypertension) explicitly describes its exercise-tested participants as a subgroup of the 2018 report and gives the same registry NCT02752217. The preserved capture contains this statement at lines 285–296, and Table 2 identifies the 8-week laboratory endpoint and SD. It reports 63±5.7 versus 76±7.3 mmHg, ten analyzed per arm; two control losses are explicitly excluded from all results. The published forest includes both the 2018 full cohort and 2019 subgroup as independent comparisons. That independence assumption is contradicted by the primary report. Different sample sizes do not establish independence; see [Cochrane Handbook 4.6.1–4.6.2](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-04).

The 2018 complete primary report remains unavailable after bounded publisher, OpenAlex, author-page and institutional-repository discovery routes. Its review-transcribed numbers were not substituted for primary data. The 2010 author upload was located, but full acquisition and erratum assessment remain unfinished. Accordingly, this candidate is not qualified for complete independent-trial reproduction. No new protocol was frozen or model run launched simply to produce a knowingly invalid pool. Machine-readable source/qualification findings and hashes: `benchmarks/findings/zheng2023_qualification_v1.json`.

## Demonstrated software defect and repair

Inspection of the real overlap exposed a separate generic defect in `scripts/trial_families.py`: the resolver checked a verified distinct-trial assertion before all same-trial links had been joined. A later transitive merge could contradict the earlier assertion without registering an unresolved conflict. Identical extracted values could then leave an accepted row despite contradictory family evidence. This was an integration counterexample, not a claim that the Zheng papers contain these synthetic three-way assertions.

The resolver now forms complete same-trial equivalence classes before evaluating distinctness conflicts. It still requires source-verified links, withholds discordant reports and makes no automatic largest-sample or target-driven selection. Tests cover every permutation of the contradictory links, generator input, and the shape of a full cohort plus subgroup plus independent trial.

Reproducible experiment:

```bash
.venv/bin/python -m benchmarks.audits.family_link_order_v1
```

Output is immutable-by-creation at `data/benchmarks/family_link_order_v1/results.json` (rerunning against that existing destination deliberately fails). The script loads preserved code bundles, leaving old runs untouched. Baseline `6ca781dc3ed77318e5d719baa70217e688acedd54ed4cb7ff83be2ea743e7081` accepted contradictory families in **4/6** processing orders. Repaired `c605db2e4c1794930779a6130f6f14a534b81207b51e05f753446512b2b8de83` rejected them in **6/6** orders. This is deterministic software verification, not a clinical meta-analysis or model evaluation.

Validation: 183 tests pass, selected fatal/import lint and `git diff --check` pass. No current numerical/model PID. Original protocols, sources, failed runs and accumulated uncommitted work are preserved.

## Next research action

Move to another compatible published outcome rather than repeatedly probing the unavailable 2018 source. A concrete unqualified lead is Puliappadamb 2022, PMID36445912/PMC10586587: the placebo migraine-severity comparison involves two parallel trials (Gonçalves2016, PMID27165014/PMC5036209, and Ebrahimi-Monfared2017, DOI10.3233/RNN-160704), whereas frequency includes a crossover trial. Retrieve both originals and inspect the published forest before choosing any contract: establish whether its change-score dispersion is actually primary-reported, its exact N/timepoint/VAS units, and its comparator selection. Reject if change SD is only imputed or full primary access fails; do not substitute an endpoint analysis and label it reproduction. The newer 2026 review PMC12864225 explicitly imputes change SD with correlation 0.5 and is not method-compatible with the current reported-input contract. No new lead is yet qualified or prespecified.

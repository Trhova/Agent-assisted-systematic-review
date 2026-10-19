# Executed four-trial escalation comparison — 15 October 2026

The complete declared four-trial analysis finished with **four independent effects and no unresolved inputs**. The fixed Mantel–Haenszel RR is **0.702091931 (95% CI 0.536788721–0.918299996)**, I²51.7683%. All six trial-pair checks passed; all four outcome-specific RoB drafts passed source checking. These remain abbreviated automated drafts, not expert RoB2 assessments.

This is an agent-assisted development comparison of one published analysis in [Lee et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC9068973/), not a completed broad systematic review, prospective validation or clinical recommendation. The previous incomplete symptom-recovery run is preserved. No contributor was dropped to obtain completeness.

## Prespecified scope and primary inputs

The other complete published outcome was hospitalization, with the review explicitly including STOIC's broader urgent-care composite. Original reports support direct event counts, avoiding the unresolved symptom-complement problem. The contract retained the outcome definitions and horizons before execution:

| Trial | Original outcome/population | Treatment | Control |
|---|---|---:|---:|
| STOIC | COVID-related urgent care, ED assessment or hospitalization; 28-day follow-up; PP |1/70|10/69|
| PRINCIPLE | COVID hospital admission or death; 28 days; concurrent eligible SARS-CoV-2-positive observed WHO outcome population |72/787|98/799|
| CONTAIN | Hospital admission or death; 14-day admission follow-up; modified ITT |6/105|3/98|
| Clemency/Covis | Hospital admission or death by day30; ITT, original preprint |3/197|7/203|

PRINCIPLE's event total is the sum of explicitly disjoint WHO ordinal progression states, with original components and evidence retained. Its nonconcurrent controls and symptom-recovery denominators were not substituted. STOIC's PP counts were paired with PP denominators. Clemency's separate ED/hospital composite was not used, and its hospital/death endpoint was not silently restricted to COVID-attributable admissions.

These are heterogeneous escalation thresholds, time horizons, populations and regimens. CONTAIN includes intranasal treatment alongside inhaled treatment. Missing follow-up and original analysis-population limitations remain; reported ITT or modified-ITT analyses do not prove complete or unbiased ascertainment. The common-effect calculation is a conditional working summary for this declared comparison, not a uniform hospitalization effect. Selection was based on available primary evidence and design/outcome fit, not expected agreement. No new source retrieval was needed in this cycle.

The original fixed-effect weighting/interval invocation is unspecified. An independently chosen fixed-MH comparison is scientifically distinct from exact-method reproduction. See [the comparison workflow](independent_published_comparison_workflow.md), using Cochrane Chapter10 guidance on binary methods and heterogeneity.

## Actual execution and integrity

- Protocol: `benchmarks/protocols/inhaled_escalation_v1.yaml`, digest `771b952a834cff0ec71a5071ce143aa9ff1571c61f77cd839de2856a1dcd2a09`.
- Actual scientific/suite code: `eb9b151eb2da992aa78b56b163466352e719df4bd3d4ec7d0cfe7ba6b0a27353`.
- Run: `data/benchmarks/inhaled_escalation_comparison_v1/inhaled_escalation_development_v1/771b952a834c`.
- Launcher26626, suite26627, review26628/26629; started20:51:59UTC, suite completed21:08:19UTC. Terminal suite exit2 means **not reproduced**, not execution failure.
- Explicit gpt-6-astra/codex; worker Medium, nested effort default/unpinned. One scientific round; one adapter attempt per scientific request. Actual31 scientific and10 RoB response receipts. CLI-internal transport attempts are not counted by those receipts.
- Source/search files were exact preserved copies, without prior model decisions. Config/source and non-Python RoB assets were frozen. All211 files in the predecessor scientific run stayed unchanged.

The new RoB v4 policy fixes a demonstrated metadata defect: the runtime had restricted `sources_used` to journal articles or conference abstracts, making a correct preprint classification impossible. It now permits `other`, explicitly preserving the original preprint version without implying access to its journal companion or cited registries. The original failed draft remains untouched. The new Clemency draft passed source checking.

## Published-source verification and disagreement

Two separate evaluator-only requests read and checked the original table. The initial reading reproduced all four published rows. Verification correctly withheld CONTAIN's registry identity because its registration was absent from the body-only text. The preserved original XML contains that registration in its abstract. A separately pinned successor added an exact front-matter projection, raw XML hash and element locator; no cells, scientific inputs or gates changed. Two new requests then verified every mapping axis. The failed v1 receipt remains preserved.

Reference verification v2 completed21:13:35UTC, PID23625; v1 PID21483 also exited. Both used code `2d9fc6d9af5455f0940aca6d191399e54f7558f617a97f1eca7335ac50f8fc18`. Artifacts: `data/benchmarks/inhaled_escalation_reference_v1` and `inhaled_escalation_reference_v2`. Separate same-model requests are procedural checks, not independent human expertise.

**STOIC is a demonstrated input discrepancy:** the published table reports2/70 versus11/69. The original report gives ITT events2 versus11 with73 participants per arm, and PP events1 versus10 with70 versus69. The published row combines ITT event counts with PP-sized denominators. Our frozen PP analysis uses the matching original pair.

An evaluator-only arithmetic calculation using the published cells under our same fixed-MH method gives **0.704505927 [0.539460073,0.920046962]**. Thus this input substitution changes the point estimate by0.002414. It does **not** explain the entire difference from the published fixed estimate0.72[0.55,0.95]; the remaining point difference is0.015494 and the exact published estimator is unknown. No estimator identity is inferred from proximity. This is a supported input-error finding plus explicit residual method uncertainty, not a claim that the full numerical discrepancy is resolved.

The verified cells and mapping are consumed by the normal versioned input evaluator. Actual text request/response replay checks source pins, modality, context, saved readings, quotations and decision rather than trusting a supplied success flag. The new [text verification workflow](reference_text_verification_workflow.md) documents this route.

## Final two-case audit and release relevance

The final read-only audit replayed both HCQ and this inhaled case, including source-verification receipts and all28 HCQ/41 inhaled successful request caches. Both artifact audits and reference checks passed. **631 pinned files remained unchanged**, with zero new model calls or scientific runs during audit. Auditor code `0cb4e7fddaa13eea89ce382c43bb0768d94c601e3c33d0b7e2028c777bc1fa52`; completed21:14:28UTC. Exact commands, contracts, calibration and receipts: `data/benchmarks/agent_assisted_release_final_v1`.

Both cases have verified primary-versus-reference input disagreement; neither has exact-input reproduction. HCQ has rounded numerical agreement; this case does not. Those distinctions are retained rather than averaged into a success score. This supplies the second complete declared-analysis development case for the accepted agent-assisted release assessment, with uncertainty about published weighting explicitly unresolved.

Validation:462 tests passed, including preprint metadata, blind text separation, altered cells, request/context/modality tampering, false receipt relabelling, code identity and exact evaluator mapping. No numerical runner remains. All earlier failed/incomplete cases remain part of the development evidence.

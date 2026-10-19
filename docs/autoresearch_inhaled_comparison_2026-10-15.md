# Complete-source inhaled corticosteroid comparison, 15 October 2026

The bounded scientific workflow actually ran on all four published trial reports. It admitted three independent effects and withheld STOIC. This is useful development evidence, **not the second complete release case**. Agent-assisted execution is accepted; missing outcome support is not waived.

## Contract and sources

The original review is Lee et al., DOI10.1183/13993003.02921-2021 (PMC9068973). Its fixed-effect sensitivity does not disclose the precise weighting/interval implementation. This blocks exact-method reproduction, but does not prevent an independently prespecified comparison. The new contract selected fixed Mantel–Haenszel RR before extraction; retained all four contributors; and explicitly recorded differing recovery definitions, including PRINCIPLE early sustained recovery through day28. Selection was based on parallel design, complete accessible original reports and binary method fit, not anticipated agreement. This citation-defined analysis is neither an exhaustive new search nor a prospective validation.

STOIC, PRINCIPLE and CONTAIN original JATS were recovered. Clemency's original 24-page medRxiv preprint was recovered from a public PDF copy, with title, DOI, version and trial-registration mapping retained; journal full text was not claimed. Failed challenge/403 bodies remain preserved and were not admitted as articles. The original STOIC appendix/SAP and Figure2 image were later recovered separately; they did not overwrite frozen sources.

Original artifacts: `data/benchmarks/inhaled_complete_comparison_v1`. Scientific protocol `benchmarks/protocols/inhaled_symptom_recovery_v1.yaml`, digest `c2504171a4b3de96c6fb1e5a2626efa2265e3e3c19715ca317000f205232fff8`; actual scientific code `e128f7852eba1920da8dce49011bb93e75bc5dfa3be3ca027533860f5ed105cf`. The preregistration pins86 source/config files plus non-Python RoB assets. Published targets were evaluator-only.

## Actual result

| Trial | Recovery intervention | Recovery control |
|---|---:|---:|
| Clemency |81/197|76/203|
| CONTAIN |57/105|44/98|
| PRINCIPLE |251/781|173/794|
| STOIC |withheld|withheld|

Partial fixed-MH RR **1.336948649 [1.180322835,1.514358308]**, I²53.7474%, three independent effects. The published four-trial fixed sensitivity is1.31[1.18,1.45]. This partial pool cannot establish reproduction or explain the full difference. All four reports were retrieved, but one quantitative input remains unresolved. RoB drafts:2 source checked,1 unverified. Clemency's draft incorrectly declared a journal article although the assessed source is a preprint; verifier refused that source metadata. These are automated drafts, not expert RoB validation.

The scientific run made25 model calls, plus8 RoB response receipts; explicit gpt-6-astra/codex. Worker effort Medium; nested backend effort default/unpinned. Launcher19304 and review/suite children exited; completion19:05:57UTC. CLI-internal transport retries are not measured by adapter-call counts.

## New source adjudication, not a forced complement

The generic opt-in `binary_known_status_complement_v1` records original opposite-event counts, outcome-specific known-status denominators, exact evidence, transformation and source hash; it computes N−opposite only for an evidenced exhaustive binary partition. It does not classify missing status as recovered. Method rationale: Cochrane Handbook Chapter6 sections6.1.1/6.4, with the distinction between reversing events and inverting an RR retained.

The STOIC article reports7 versus21 with symptoms on day14; Figure2 prints corresponding risk sets from70 versus69. However, monitoring ceased after recovery or a primary event. The SAP's planned missing-data methods do not establish actual application to this binary endpoint. A risk-set complement is not automatically observed point-prevalence absence, and its position relative to events on day14 is unclear. Two new source-only calls inspected the original image, article and appendix, retaining exact text/pixel provenance. Verified adjudication remains **existing complement unsupported**; no input admitted. Same-model procedural separation has correlated-error limitations and is not independent expertise.

`data/benchmarks/stoic_followup_adjudication_v1/execution/receipt.json`: completed19:07:31UTC, code `d33add075ae4e45e06d2cee0fa1e266732fa93538f0d75bb0180d0ce30170b69`,2 new calls, no numerical execution. PID8180 exited. No curve digitization, missing-status imputation or replacement by reference cells.

## Demonstrated execution defect and repair

The original suite completed scientific/RoB work before discovering that its reference pin was a raw-file SHA rather than the required canonical JSON digest. That failure is preserved. `benchmark_suite.py` now checks evaluator asset pins before launching a scientific child; it still rechecks at evaluation and never passes targets to screening/extraction. A regression proves invalid reference or evaluation-contract hashes cause zero child/RoB submissions. The prior child-code-drift test now supplies a valid reference fixture so it still exercises the intended downstream guard.

The corrected evaluation ran from the **original frozen scientific code** on a new copy only: `data/benchmarks/inhaled_evaluation_v1`. Its preregistration records all original-file hashes and corrected configuration; receipt confirms originals unchanged,0 model calls, exit2/not_reproduced. Artifact audit valid; coverage4 accessible/3 accepted/1 unresolved; semantic agreement false because the published estimator is unspecified; numerical agreement false. Original failure and source artifacts remain immutable. This was evaluator replay, not a second scientific run.

A generic evaluator-only text-source verifier was also implemented and tested (blind source reading followed by source/mapping verification); prepared inhaled reference inputs remain **unexecuted/unverified**. Do not treat those manual transcriptions as independently verified evidence.

## Release state and next action

One supported declared-analysis development case remains (HCQ); second case and final release review are outstanding. Do not rerun these unchanged inputs, trim STOIC or silently replace point prevalence with first recovery. Next finite action is source-level outcome compatibility review of the already recovered complete four-trial set: determine whether another **published complete analysis** has explicitly reported, compatible outcome cells without complement assumptions. Inspect definitions before counts/targets; if none qualifies, close this candidate rather than building more evaluator stages. Any new outcome must receive a new contract and independent source qualification before execution. No extra paper search is justified solely to force this case through.

Validation:455 tests passed; focused lint and Git whitespace check passed. Tests establish implementation behavior, not scientific completeness.

# Evidence-linked outcome availability and continuation

Implemented `scripts/outcome_availability.py` and integrated its JSON ledger and continuation queue into ordinary `scripts.report_review` exports. It consumes completed-run artifacts without model calls or new clinical decisions. Exact stored reasons retain JSON-pointer locators. Source URLs, text hashes, matched/unmatched quotations, accepted limitations and original synthesis remain visible together.

The categories distinguish missing full-text access, unresolved target inputs, reported outcome-scope exclusions, other exclusions, accepted inputs, and accepted inputs with limitations. Timing, units, denominators, dispersion, outcome definitions, trial independence and intervention route are routing cues. They select concrete next evidence checks, not new exclusions or numerical substitutions. In particular, missing data mentioned for an accepted ITT estimate do not automatically make that estimate unresolved.

A stored claim that a different outcome was measured is not promoted into certainty merely because text mentions an outcome. Exact quote matching verifies an anchor exists in a hash-consistent source; it is not independent clinical adjudication of the claim. Where prior artifacts contain only a model refusal or no quotation, the report says so and preserves that uncertainty. No new evidence policy, eligibility rule, estimator or completion gate is introduced. Suggested actions never authorize changing scientific decisions automatically.

Actual experiment: `data/benchmarks/outcome_availability_v1`. Configuration `benchmarks/audits/outcome_availability_v1.json`; code snapshot83a89d6293a587ac346c12c6e9c26244a59fb3b176debdbaf5783ea112fe55ac. It generated both standalone availability outputs and integrated review exports in isolated directories, checking every source-run file before/after.

| Preserved run | Actual report observations | Original files unchanged |
|---|---|---:|
| Poppv2 |2 accepted with limitations;2 missing full texts; Lopes target timing unresolved;4 other exclusions|208|
| Pérezv2 |1 accepted;4 unresolved target inputs, including denominator/unit/dispersion cues|97|
| RawatIV |3 accepted with limitations;1 unresolved route;2 reported outcome-scope exclusions;6 other exclusions|272|

All577 original files are unchanged, including numerical, family, extraction and completion decisions. Rawat's ICU-only exclusion has two matching source quotations; the reported alternate-comparator/outcome exclusion has one. These remain preserved model decisions with visible evidence, not newly certified scientific conclusions. Popp's three continuation records are precisely33542047,32337546,33769172. Pérez has four and Rawat one. The queue preserves source/reason links and offers concrete checks instead of generic “needs review”.

Validation:207 tests pass, selected fatal/import lint and whitespace checks pass; all12 configured protocol/reference pairs verify. New tests cover accepted limitations versus unresolved inputs, source hash/quote failures, exact preservation of original reasons and files, safe output destinations, active-run refusal and preventing a design exclusion from being mislabeled solely because it mentions an outcome. The actual exercise also exposed broad outcome-word matching, which was narrowed before the frozen experiment.

```bash
.venv/bin/python -m scripts.outcome_availability --run RUN_DIRECTORY --output NEW_EMPTY_REPORT_DIRECTORY
.venv/bin/python -m scripts.report_review --run RUN_DIRECTORY --output NEW_REVIEW_EXPORT_DIRECTORY
.venv/bin/python -m benchmarks.audits.outcome_availability_v1 --output NEW_EXPERIMENT_DIRECTORY
```

Standalone availability/experiment commands refuse existing populated output; original reports should be preserved and new directories selected. Ordinary review exports retain their existing interface. JSON outputs are intended for both reviewer inspection and subsequent evidence-acquisition planning. They do not themselves run retrieval, change numerical data, adjudicate scientific uncertainty or establish production validation.

No model or clinical benchmark was rerun this cycle. The several-review autonomous-system objective remains incomplete. Next independent scientific candidate: Alabed2014 pericarditis total adverse effects, four parallel trials with fixed MH RR. The original review PDF was lawfully recovered from City Research Online after a failed PMC JATS route. Primary COPE, CORE, CORP and ICAP sources/counts/denominators/timing must all qualify before freezing and execution. Its time-to-recurrence HR is unsupported; fixed-time recurrence cells also need careful source/estimand reconciliation. See `benchmarks/findings/alabed2014_candidate_v1.json`; no qualified benchmark claim yet.

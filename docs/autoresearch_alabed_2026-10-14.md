Dated evidence correction,14October2026 09:52UTC: the retained `16446775_publisher_preview.txt` contains a failed Nature redirect, not a synopsis. Earlier descriptions of a preserved publisher synopsis are unsupported by that artifact. A new Springer publisher route also failed. No non-primary exclusion has been made; all five access gaps remain. Historical text is retained below for provenance.

# Alabed2014 safety development evaluation

The bounded execution is in `data/benchmarks/alabed2014_v1`, with immutable preregistration, original-source manifest and launch receipt. This is a post-hoc, developer-assisted historical comparison of the published four-trial total-adverse-effects analysis. It is not a complete autonomous review or prospective validation. Execution finished with no pool:157 screened,9 full-text candidates,4 accepted extractions,0 independent effects and5 access gaps. Artifact audit is valid with no issues; overall reproduction is false. Launcher PID21502 exited with code2 at07:55:19UTC.

The review combines acute and recurrent pericarditis for safety, using fixed Mantel–Haenszel risk ratios. Its broad eligibility includes multiple recurrences; CORP-2 was published before the search cutoff but remains awaiting assessment in this review. The new comparison explicitly restricts populations to first acute episode or first recurrence. This reproduces the published quantitative population rather than claiming the broader review question was completely searched and resolved. Mixed idiopathic/viral/autoimmune populations are retained as in the included primary trials; purely postoperative prevention is excluded. Treatment durations and total observation periods differ and are preserved, without inventing a common safety horizon.

Original sources recovered and preserved:

| Trial | Original source | Primary safety input | Observation evidence |
|---|---|---|---|
| COPE2005, PMID16186437 | Author-upload original text on ResearchGate, contiguous lines113–1274; Table2 | Colchicine5/60, control4/60; total side effects | All120 followed; mean24months, range8–39; colchicine3months |
| CORE2005, PMID16186468 | Original Arch Intern Med PDF from rima.org; Table2 | Colchicine3/42, control6/42; adverse effects | All84 followed; mean20months, range8–44; colchicine6months |
| CORP2011, PMID21873705 | Original Annals PDF from pharmaselect.sk; Table3 | Colchicine4/60, placebo4/60; overall adverse effects | No loss; safety monitored during follow-up; minimum18months; colchicine6months |
| ICAP2013, PMID23992557 | Original NEJM PDF from University of Maryland teaching archive; Table3 | Colchicine14/120, placebo12/120; overall adverse events | Scheduled follow-up, minimum18months; colchicine3months |

These qualification inputs are evaluator observations, not supplied to the model. The execution receives original primary documents and the frozen scientific contract. It must establish eligibility, arm assignment, counts, denominators, quotations and trial-family decisions itself. Distinct acute/recurrent cohorts and recruitment windows are documented, but common sites/authors alone neither prove nor disprove participant independence. Family assessment remains part of the actual run.

A concrete discrepancy was identified before execution: review Analysis2.1 puts6/42 in colchicine and3/42 in control, whereas CORE Table2 and the primary text identify group1 as conventional care and group2 as colchicine, with6 and3 adverse effects respectively. Its two2005 study labels also appear interchanged in that forest. The frozen published pooled target remains1.26[0.75,2.12]; it is not corrected to make the benchmark pass. Extraction never receives this target or the discrepancy hypothesis. Numerical discrepancy should be explained from primary evidence after execution.

ICAP bibliographic metadata lists four2014 comments, not a correction to the original safety table; these notices are preserved in original metadata and normal workflow integrity reporting. A similarly titled search hit for correspondence must not replace the original trial.

No engine/method changes were needed for qualification.207 tests passed before launch; code83a89d6293a587ac346c12c6e9c26244a59fb3b176debdbaf5783ea112fe55ac. Modelgpt-6-astra/codex is explicit; workerMedium, nested reasoning backend-default/unpinned. Public original-PDF imports and preserved web-capture import reuse existing generic acquisition routes. Publisher failures are retained and were not repeatedly retried.


Actual model extraction matched all four primary safety inputs above, including CORE3/42 versus6/42. Family adjudication withheld ICAP–CORP and CORE–COPE because overlap/reenrollment was not settled. These are unresolved possibilities, not demonstrated duplication. Consequently no pooled estimate was produced and no numerical reproduction is claimed. The primary-versus-review arm discrepancy is independently observable, but cannot be presented as an actually pooled result from this run.

Five inaccessible candidates remain:16446775,8184826,8284902,1826159,2892065. A publisher preview newly identifies16446775 as a Practice Point synopsis of COPE; preserved separately, not falsely imported as full text or used to rewrite this run. Remaining source access and family questions need different evidence routes rather than unchanged retries.

The run exposed and prompted a generic reporting repair: accepted-but-family-blocked records now retain the actual pairwise blocker and source evidence, rather than receiving irrelevant input-check actions from their successful extraction reasons. `scripts/outcome_availability.py` v2 and tests exercise this. Actual isolated export: `data/benchmarks/alabed2014_family_reporting_v2_final`, all201 original files unchanged, two family groups/four blocked reports/five access gaps, audit valid.209 tests pass. Earlier v2 export is retained; final adds readable paired blockers to Markdown. Scientific gates and original code snapshot are unchanged. Read [methodological assessment and next evidence action](family_adjudication_evidence_review_2026-10-14.md).

Reproduce the new export with `.venv/bin/python -m scripts.outcome_availability --run data/benchmarks/alabed2014_v1/alabed2014_total_adverse_effects_development_v1/d72deae41224 --output NEW_EMPTY_DIRECTORY`. The exact scientific launch command and environment are in the immutable launch receipt. Do not relaunch it unchanged.

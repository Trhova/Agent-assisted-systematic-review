# Local agent-assisted development release v0.1

**The finite release acceptance assessment passes.** The repository has an exercised agent-assisted workflow and two complete declared published-analysis benchmark cases, with source-verified input disagreements retained. This is a local development assessment, not exact reproduction of both references, an unattended system, a completed multi-outcome systematic review, or independent clinical validation.

The unchanged [release contract](agent_assisted_release.md) defines the gates. [The operating skill](../skills/agent-assisted-review/SKILL.md) is the entry point; its [workflows](../skills/agent-assisted-review/references/workflows.md) cover source recovery, quotation repair, family/denominator adjudication, frozen execution, interruption recovery and audit. Agent interventions are part of the supported operating model.

## Gate assessment

| Gate | Evidence | Assessment |
|---|---|---|
| Operable guarded workflow | Skill delivered and exercised on actual frozen analyses; source import, exact-anchor checks, independence/N gates, bounded requests and immutable failures retained | Pass |
| Two complete declared analyses | HCQ hospital mortality:3 independent trials/0 unresolved; inhaled escalation:4 independent trials/0 unresolved. Scope and primary inputs frozen before their executions | Pass for declared scopes; no whole-review claim |
| Evidence-backed comparison | Original reference figures/text checked in separate model requests and replayed against actual request/response assets. ORCHID denominator and STOIC population/count discrepancies preserved | Pass; exact-input reproduction false for both |
| Execution integrity | Actual code/model/protocol/source pins; terminal receipts; deterministic synthesis audit;28 HCQ and41 inhaled successful request caches checked | Pass; historical failures elsewhere remain failures |
| Usable handoff | This finite index, commands, capability limits, RoB status and462 passing tests; all four inhaled and three HCQ RoB drafts source checked | Pass for an assisted development tool |

This table is an explicit agent assessment using the evidence, not an automatic guarantee of scientific truth. Separate requests to the same model may share errors. Source-checked RoB drafts are abbreviated and not expert-validated RoB2/GRADE.

## Completed benchmark cases

| Declared analysis | Primary result | Reference comparison |
|---|---|---|
| HCQ predominantly hospital-treated28–30-day mortality sensitivity,3 trials | RR0.877845[0.578065,1.333090] | Rounded pooled agreement, exact-input disagreement. ORCHID primary mortality denominators241/236 versus published242/237; unknown vital status was not assigned an outcome. |
| Lee2022 inhaled-corticosteroid study-defined escalation,4 trials | RR0.702092[0.536789,0.918300] | Published fixed result0.72[0.55,0.95]. STOIC published2/70vs11/69 mixes ITT events with PP-sized Ns; source-supported PP is1/70vs10/69. Under our same MH method that cell substitution gives0.704506, so the remaining difference is **not explained**; published exact weighting/interval method remains unknown. |

The second case is a completed source-grounded comparison, not exact-method reproduction. Its interpretation retains urgent-care versus hospital/death thresholds,14/28/30-day horizons, modified-ITT/PP/ITT populations, follow-up limitations and a preprint source version. HCQ retains mixed HYCOVID recruitment, TEACH follow-up limits and its scoped sensitivity. Neither is prospective or held-out validation. No clinical decision recommendation follows from these benchmarks.

## Finite artifact index

- [Final two-case audit receipt](../data/benchmarks/agent_assisted_release_final_v1/receipt.json): completed15October2026 at21:14:28UTC; both audits/reference checks valid;631 pinned files unchanged; zero new model calls or scientific runs during this audit.
- [Final frozen manifest](../data/benchmarks/agent_assisted_release_final_v1/manifest.json): exact code, source inventories, case paths and evaluation contracts. Auditor code `0cb4e7fddaa13eea89ce382c43bb0768d94c601e3c33d0b7e2028c777bc1fa52`.
- [HCQ dossier](agent_assisted_release_checkpoint_2026-10-15.md) and [final evaluation](../data/benchmarks/agent_assisted_release_final_v1/hcq_evaluation.json).
- [Inhaled run, source qualification and discrepancy report](autoresearch_inhaled_escalation_2026-10-15.md), [final evaluation](../data/benchmarks/agent_assisted_release_final_v1/inhaled_evaluation.json), and [arithmetic impact calculation](../data/benchmarks/agent_assisted_release_final_v1/reference_cell_calibration.json).
- [Successful original-table verification](../data/benchmarks/inhaled_escalation_reference_v2/execution/receipt.json), preserving [the first missing-context failure](../data/benchmarks/inhaled_escalation_reference_v1/execution/receipt.json).
- [Text-source verification workflow](reference_text_verification_workflow.md) and [independently specified comparison workflow](independent_published_comparison_workflow.md), added without changing the pinned original skill/contract.

## Operating the release

Start with the operating skill and a source-led versioned question. Qualify outcome, population, unit, analyzed N, dispersion/events, arms, follow-up and independence before admission. Unsupported evidence produces an explicit abstention; the agent may pursue a bounded new source route or a separately specified continuation. Never overwrite a failed run or copy reference answers into extraction.

For new scientific work, prepare a new protocol/suite and source manifest, verify the requested model, freeze Python and non-Python assets, then invoke `scripts.benchmark_suite` through `scripts.run_frozen.command` as shown in the skill. Existing frozen launchers are receipts/examples, not destinations to rerun. The release does not authorize silently converting new endpoints or relaxing input gates.

For a read-only audit, use the recorded frozen auditor and a **new output path**. For example, from the repository root:

```python
import subprocess
from scripts.run_frozen import command

identity = "0cb4e7fddaa13eea89ce382c43bb0768d94c601e3c33d0b7e2028c777bc1fa52"
run = "data/benchmarks/inhaled_escalation_comparison_v1/inhaled_escalation_development_v1/771b952a834c"
subprocess.run(command(
    "data/benchmarks/code_bundles/" + identity, identity,
    "scripts.audit_run", [run, "--output", "NEW_AUDIT_OUTPUT.json"]
), check=True)
```

Use `.venv/bin/python` for repository commands. The audit checks consistency and arithmetic, not clinical truth. Source-verification receipts require the separate replay described in the text/image workflows.

## Limits and stopping point

The supported benchmark evidence is narrow: two assisted, post-hoc, binary fixed-MH analyses in COVID-19. Other continuous-outcome, acquisition and image capabilities have development evidence but are not thereby validated across disciplines. Single-database/citation-defined searches, incomplete original review coverage, inaccessible sources, unknown source statistics and same-model errors remain material limits. Ma/Li, Popp, Rawat, Alabed and the inhaled recovery failure stay in the dossier; no historical unsuccessful case was relabelled.

The finite two-case release task is complete under this assessment. No further numerical execution or source chase is required for these gates. Future work—broader domains, held-out reviews, expert RoB/GRADE, richer discovery and generic front-matter context—is separately scoped backlog, not a reason to repeat completed pools or erase failures. No schedules were changed by this worker.

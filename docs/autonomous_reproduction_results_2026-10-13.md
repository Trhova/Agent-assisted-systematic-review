# Autonomous development reproduction, 2026-10-13

The new source acquisition, protocol, statistical and parsing changes were implemented and executed with explicitly pinned `gpt-6-astra`. Both benchmark comparisons finished **not reproduced**. Processing queues finished and no review/model runner remains. The evidence remains incomplete; this is not a validated complete-review system.

These are familiar, post-hoc development cases, not held-out validation. Original protocols, references and failed runs remain unchanged. The fresh v2 and v3 executions are retained separately. The final v3 observation is a documented cache continuation after a quotation-handling repair; it is not presented as another independent model replication.

## Actual final observations

| Review | Search and screening | Reference report coverage | Accepted reference contributors | Quantitative result |
|---|---|---|---|---|
| Ma 2013, ALT change MD | 108 records; 15 candidate reports attempted | 4/4 retrieved and retained; 3/4 fulltexts accessible | 1/4 | No pool: fewer than two validated change effects. Published MD −23.71, CI [−33.46, −13.95]. |
| Li 2016, endpoint FBG SMD | 688 records; 31 candidate reports attempted | 12/12 review reports retrieved and retained; 7/12 fulltexts accessible | 4/9 reported FBG contributors | Partial DL random-effects SMD **−0.400466**, normal 95% CI **[−0.797189, −0.003744]**, I² **57.0%**. Published SMD −0.61, CI [−0.92, −0.30], k=9. |

Li's protocol/reference/effect semantics agree. Its four accepted contributors are Firouzi (26988693), Bayat (26955460), Hosseinzadeh (24319552), and Mazloom (23645956); no extra studies were pooled. The partial result has the same direction and barely excludes zero under the specified interval method, but cannot validate the complete published conclusion. Twelve review reports are not twelve independent FBG trials; the nine forest contributors are themselves subject to unresolved overlap/integrity questions.

Ma's Wong extraction matches all six forest arm inputs exactly. Li's Bayat, Firouzi and Hosseinzadeh extractions also match all six inputs. Mazloom's means and analyzed counts match; its dispersions differ for a documented statistical reason below. Source quotes, locators, original values, transformations and hashes remain in the run artifacts and [input audits](../benchmarks/findings/li2016_final_input_audit_v3.json).

## Evidence-backed reasons for disagreement

- **Ma uses changes, not endpoints.** Wong reports usable change means/SDs. Aller and Malaguarnera provide baseline/endpoint dispersions but no identified change SDs. No unknown within-person correlation was invented. Malaguarnera's primary Table 2 gives treatment ALT 101 before and 47.1 after, implying −53.9; the forest uses −63.9. This is an unexplained source discrepancy, not proof of which underlying clinical value is correct. The accessible author-response PDF supplies no statistical clarification. See [Ma](https://www.wjgnet.com/1007-9327/full/v19/i40/6911.htm) and [the primary report](https://magistralbr.caldic.com/storage/product-files/1689970583.pdf).
- **SE is not SD.** Mazloom Table 2 explicitly reports SE=16.38 for each endpoint arm. Supported analyzed counts are 16 treatment/18 control, yielding SDs 65.52/69.494454. The corrected Hedges SMD is −0.057434 versus −0.237240 from the forest's SE-as-SD inputs. Asemi's SEs 9.5/12 with reported 27/arm yield SDs 49.363448/62.353829; these are forensic calculations only because that report is withheld. The extension follows [Cochrane 6.5.2.2](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06), with original evidence retained and independent numerical verification.
- **Eligibility needed explicit reconstruction.** Li's stated placebo/probiotic criteria differ from its included advice comparator and inactivated yeast. The versioned contract documents the actual included scope. V3 requires a unique unconfounded comparison, permitting Bayat's probiotic yogurt versus advice while excluding the additional active vegetable arm. See [Li's review](https://pmc.ncbi.nlm.nih.gov/articles/PMC4937966/) and [Bayat's primary report](https://pmc.ncbi.nlm.nih.gov/articles/PMC4763470/).
- **Current integrity notices matter.** Asemi's [publisher notice](https://karger.com/anm/article/79/2/275/833712/Expression-of-concern-Effect-of-Multispecies) concerns within-article sample-size discrepancies. The [bread notice](https://karger.com/anm/article/79/2/276/833711/Expression-of-concern-Effects-of-Daily-Consumption) raises sample-size, registration and overlap concerns. Later notice errata correct pagination, not those concerns. Flagged reports may be extracted for audit but are not admitted to the primary pool.
- **Original source gaps persist.** Ma PMID21505361 and Li PMIDs21700013, 22129852, 24706266, 25196301, 25300285 were not recovered. PMID21700013 is a review report outside the nine forest contributors. New DOI-verified OpenAIRE routes and additional public repository/publisher routes were tried and logged; they recovered no additional usable original trial fulltexts. Error pages and abstract-only responses were not treated as articles. Other candidate reports also remain unresolved. Mohamadshahi's unknown withdrawal allocation and kefir's unspecified glucose-outlier exclusions were not replaced with guessed arm denominators.

## Implemented and verified

The runtime now supports opt-in source-audited within-arm mean SE→SD conversion, reported change-score MD, and separately specified endpoint/change MD combination (never mixed SMD). It retains linked publication notices, validates bibliographic query fields against Europe PMC, discovers DOI-matched OPEN OpenAIRE locations, and adds geometry-based readable views of rotated PDF pages without replacing originals. Exact-quote repair cannot change statistics, retains rejected snippets, and still requires independent source verification. Restart preparation can reuse content-addressed RoB model/geometry caches without copying compiled judgments or pooled answers.

The final code snapshot is `ce5957d1dfe2bf3a41d2fa113d9ba7ac85c60a9d860bc18d0feaf4aceaf40388`. **146 tests passed**, changed-file correctness/import lint passed, and all original/versioned protocol-reference hash checks passed. Full repository Ruff remains non-clean because of broader legacy pipeline/style findings; a repository-wide clean lint result is not claimed.

Automated RoB drafts: Ma one source-checked; Li three source-checked and one unverified. The yeast draft was correctly rejected for an inexact quotation and overconfident missingness/assignment assertions. These drafts do not affect numeric inclusion or weights, are not expert-validated canonical RoB2, and do not provide GRADE. Multi-database historical search equivalence, complete source access, reliable treatment of all trial designs and generalization beyond these development cases remain unestablished.

## Artifacts and execution

- [Final suite comparison](../benchmarks/findings/reproduction_v3_final_suite.json), [run map](../benchmarks/findings/reproduction_v3_final_run_map.json), [Ma input audit](../benchmarks/findings/ma2013_final_input_audit_v3.json), [Li input audit](../benchmarks/findings/li2016_final_input_audit_v3.json).
- Full immutable source/model/attempt artifacts: `data/benchmarks/reproduction_v2_suite`, `reproduction_v3_suite`, and `reproduction_v3_final`.
- Final test, lint and frozen-input checks: `data/benchmarks/reproduction_v3_final/{test_report.txt,lint_report.txt,frozen_input_verification.json}`.
- [Scientific contracts and iteration rationale](reproduction_v2_contract.md); final suite configuration is `benchmarks/suite_reproduction_v3.yaml`.

Fresh execution, using an empty work directory:

```bash
.venv/bin/python -m scripts.benchmark_suite --suite benchmarks/suite_reproduction_v3.yaml --workdir data/benchmarks/reproduction_fresh --model gpt-6-astra --max-rounds 3
```

The final observed continuation used `scripts.resume_inputs` from the two completed v3 runs into corresponding empty directories under `data/benchmarks/reproduction_v3_final`, then:

```bash
.venv/bin/python -m scripts.benchmark_suite --suite benchmarks/suite_reproduction_v3.yaml --workdir data/benchmarks/reproduction_v3_final --model gpt-6-astra --max-rounds 3
```

Each final run's `initialization.json` records its exact source, copied inputs and protocol/backend/model identity. The preserved code bundle and all raw failed attempts remain available. No credits were purchased, external messages sent, or automations started.

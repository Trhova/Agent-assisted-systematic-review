# Review reproduction development contracts, 2026-10-13

These are new, post-hoc development protocols. Original protocols, references and failed observations remain unchanged. The runner receives primary reports and review questions, never published numerical targets. Comparison occurs after execution.

## Ma 2013

The published Figure 2B uses **change scores**, not endpoint ALT. Negative arm values and Wong's primary Table 2 establish the convention. The new protocol therefore requires changes from baseline to treatment completion and their own reported SDs (or supported within-arm mean SEs), using fixed inverse-variance MD in U/L. It does not manufacture change SDs from baseline and endpoint SDs. The original submission-date search cutoff remains an explicitly uncertain proxy.

Visual inspection also found a specific reference discrepancy: Malaguarnera's primary Table 2 (journal page 548) gives treatment ALT 101 before and 47.1 after, implying −53.9; Ma's forest uses −63.9. The original table's baseline/final dispersions are not identified as change SDs. The forest mean is not recoverable from those primary arm means; this establishes a source discrepancy, not which underlying value is clinically correct. Neither copying the unexplained forest value nor reconstructing an unknown correlation is supported. Aller likewise reports baseline/final means and SDs; their difference alone does not supply a change SD. Wong directly reports change means/SDs.

Sources: [Ma methods and Figure 2](https://www.wjgnet.com/1007-9327/full/v19/i40/6911.htm), [primary Malaguarnera report](https://magistralbr.caldic.com/storage/product-files/1689970583.pdf). Local visual evidence and original hash-bearing source artifacts remain under `data/benchmarks/reproduction_v2_evidence` and the historical source folders.

## Li 2016

The new search includes Saccharomyces, yeast and the microbial terms in the published methods. It uses title/abstract and keyword fields in the accessible MED database; it cannot recreate historical EMBASE/Cochrane searches. The broad question is T2D and microbial supplements; twelve review reports remain distinct from nine reported FBG contributors.

The publication's stated placebo/probiotic eligibility conflicts with its actual included dietary-advice comparator and inactivated brewer yeast. The new **operational inclusion reconstruction** explicitly allows these classes, without calling inactivated yeast a live probiotic. This is a source-backed account of the included scope, not a claim that the stated methods are internally consistent. Primary endpoint FBG SMD is used; endpoint/change SMDs are never mixed. Random-effects DL and normal intervals are retained for comparison with the published analysis.

The Asemi and Mazloom SE/SD discrepancies remain evaluator findings. Primary SE values are converted only with verified unadjusted arm-mean scope and analyzed denominators. Asemi Table 3 gives 27/arm; Mazloom's Results population and Table 1 give 16 treatment/18 placebo, with after-treatment sampling described in Methods. Their applicability is independently checked during extraction; reference forest values are not model input.

Source: [Li primary review](https://pmc.ncbi.nlm.nih.gov/articles/PMC4937966/) sections 2.1–2.5, included studies and Figure 3. Cached original JATS is in `data/benchmarks/reproduction_v2_evidence/PMC4937966.xml`.

### Li v3 clarification after the first execution

The v2 extraction correctly identified multiple seemingly eligible arms in [Bayat's primary report](https://pmc.ncbi.nlm.nih.gov/articles/PMC4763470/), including probiotics with an additional active vegetable intervention. The v3 contract makes the microbial-intervention estimand explicit: additional nonmicrobial active ingredients must be balanced across selected arms. A unique unconfounded eligible pair may be extracted from a multiarm trial; multiple equally eligible pairs remain unresolved without a separately specified dependence method. This rule is generic and precedes the new execution. It does not select an arm by effect size or match to reference numbers. V2 files and observations are retained unchanged.

## Methods and integrity

The opt-in extension is `protocol/extensions/continuous_derivations_v1.yaml`. It preserves original dispersion, units, score definition, exact source quotes, analyzed denominator evidence, table/page locator, original-statistics hash, source hash and deterministic calculation. [Cochrane 6.5.2.2](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06) supports SD=SE×sqrt(n) for unadjusted within-arm means. [Cochrane 10.5.2](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10) supports separately prespecified endpoint/change MD combination; that optional extension is not the Ma change-only benchmark.

Related corrections/notices are now retained from bibliographic metadata. Expressions of concern were missed by the old normalized record, which retained only publication types. Source-supported numeric extraction may proceed for audit, but flagged reports are withheld from primary pooling until notice-specific scientific resolution. This is not an exclusion based on unfavorable results.

PDF sources also receive a supplementary orientation view when at least 100 nonspace glyphs and 80% agreement establish a cardinal page rotation. The original PDF/text remains intact; the added view records page numbers, rotation, PDF hash and parent text hash. This fixes a general reversed-table reading problem seen in Firouzi without hard-coded article identities or values. Exact-quotation repair is bounded to one call and may change only evidence strings; unsupported snippets never count as evidence and are retained as rejected artifacts. Every required evidence field must retain exact support, and a separate model must verify every numeric field against the full source.

The bread report [publisher notice](https://karger.com/anm/article/79/2/276/833711/Expression-of-concern-Effects-of-Daily-Consumption) identifies sample-size, registration and overlap concerns. The [Asemi notice](https://karger.com/anm/article/79/2/275/833712/Expression-of-concern-Effect-of-Multispecies) (PMID 37334997) specifically identifies sample-size discrepancies within the article; its apparently clear table denominator therefore does not resolve the integrity concern. Later notice errata (DOIs 10.1159/000533249 and 10.1159/000533251) correct pagination only. These are material barriers to interpreting a published numerical match as correct independent replication.

## Execution

A live isolated schema-constrained call verified `gpt-6-astra` availability through the existing authenticated Codex backend. The local model catalog specifies medium as its default reasoning effort. Extraction remains tool-disabled. No model substitution, credit purchase or external messaging occurred.

Fresh suite:

```bash
.venv/bin/python -m scripts.benchmark_suite --suite benchmarks/suite_reproduction_v2.yaml --workdir data/benchmarks/reproduction_v2_suite --model gpt-6-astra --max-rounds 3
```

Only primary-source acquisition artifacts may be warmed from prior development runs. No screening decisions, extraction calls, accepted effects or synthesis are carried across the changed protocol/model. Search and screening execute anew. Search-field identifiers are checked against the live Europe PMC field inventory, preventing unsupported field syntax from silently widening the query. Every review attempt freezes its code and protocol hashes.

The follow-up suite `benchmarks/suite_reproduction_v3.yaml` retains Ma v2 and uses Li v3. Use a separate `data/benchmarks/reproduction_v3_suite` work directory. Runtime source/parser repairs are captured by each run's code hash; they do not modify frozen review protocols.

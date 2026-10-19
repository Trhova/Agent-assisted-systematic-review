# Executed development comparison — 14 October 2026

Pérez-Gómez 2020 ashwagandha/VO₂max was executed twice with explicit `gpt-6-astra` using the authenticated Codex backend. Both versions completed the bounded workflow and failed scientific reproduction: seven records screened, all five original review reports read, one independent comparison accepted, four unresolved. Neither produced a pooled estimate. Complete source access did not establish usable quantitative inputs. This cycle does **not** add a successful complete-review reproduction or an autonomous pooled benchmark result.

| Run | Protocol hash prefix | Model requests | Accepted effects | Unresolved | Audit | Reproduction |
|---|---|---:|---:|---:|---|---|
| `data/benchmarks/perez2020_v1` | `9b6d0a691c23` | 9 | 1 | 4 | consistent | false |
| `data/benchmarks/perez2020_v2` | `3576ccdea7d5` | 9 | 1 | 4 | consistent | false |

Each run made seven screening/extraction/verification requests and two RoB requests. Each produced one source-checked RoB draft, zero unverified drafts; these are not expert validation. Execution code: `6ca781dc3ed77318e5d719baa70217e688acedd54ed4cb7ff83be2ea743e7081`. Worker reasoning is medium; nested model reasoning effort was the backend default, not independently pinned. Preregistration, exact commands, original process IDs and source configuration are preserved in each run directory. PIDs 28512 and 12436 have exited. No numerical/model runner remains active.

## Actual primary-source findings

Shenoy 2012, PMID23326093, was accepted independently: n18/19, endpoint means52.0/44.4 and SD4.8/5.7 mL/kg/min at eight weeks. Original Table1 explicitly gives analyzed counts after two active and one placebo withdrawals. The review's forest uses20/20. The single source-supported MD is7.6 mL/kg/min, but one trial cannot supply a meta-analysis.

Choudhary 2015, PMID26730141, was retained but not pooled. Abstract/results say Ashwagandha24/placebo25; Tables1–2 label Ashwagandha25/placebo24. The table footnote also describes litres/minute rather than establishing the protocol's mL/kg/min units. The review forest uses25/25 and the eight-week means, even though treatment lasts12weeks and later measurements exist. No denominator or unit was silently chosen. These are actual internal source conflicts, not an access problem.

Tripathi 2016, DOI10.18203/2319-2003.ijbcp20164114, describes two active doses and final day28. The printed Table2 stops at the330mg day14 column; final active-arm SDs are not printed. The text provides final means but cannot supply missing SDs. Screening/withdrawal arithmetic and stated group sizes also need reconciliation. The review forest uses one330mg comparison at day14. The protocol does not substitute that interim comparison for the final all-dose estimand.

Malik 2013 reports16 randomized participants per group and explicit endpoint means/SDs, but the model found no explicit outcome-specific analyzed N. Sandhu 2010 similarly reports assigned groups and ANOVA counts but lacks an unambiguous measurement construct/unit and analyzed-arm statement. These are conservative unresolved extraction decisions, **not proof that the trials lost participants or that their reported group sizes are wrong**. No counts were invented. Further adjudication would need an evidence-supported reporting convention or genuinely new source evidence; do not relabel these decisions as independently proven scientific errors.

V1 also imposed an unnecessary requirement that a trial explicitly validate its named exercise prediction test. That requirement was my benchmark-design error; it was absent from the review's published eligibility. V1 is preserved. Separately frozen v2 permits named exercise prediction tests or stated VO₂max prediction formulas while retaining uncertainty about measurement validity. V2 accepted Malik and Tripathi as eligible but still could not validate their required numerical inputs. No completed artifacts or contracts were overwritten.

## Independent comparison of the published answer

Evaluator-only transcription of Figure3 reproduces MD2.998278 [0.176063,5.820492], I²83.6652%, matching the published3.00[0.18,5.82]. This confirms the implemented inverse-variance DL/normal-CI MD arithmetic. It is **secondary numerical calibration**, not autonomous extraction or successful review reproduction. The independent reading exposes nominal denominators, interim timepoints and single-dose selection in the published forest. These values and the published answer are outside screening/extraction requests.

Machine-readable observations: `benchmarks/findings/perez2020_development_v1_v2.json`. Separate forest reading: `benchmarks/findings/perez2020_reference_reading_v1.json`. Full acquisition/selection account: [selection report](accessible_benchmark_selection_2026-10-14.md).

## Concrete engineering and validation

- `scripts/bibliographic_supplement.py` accepts a primary-source URL when a legitimate report lacks an assigned DOI. It still enforces frozen bibliographic-only input and rejects numerical fields. Malik exercised this path.
- `scripts/import_source_capture.py` imports preserved line-numbered primary web text, checks contiguous boundaries, source URL/title and conflicting overlaps, rejects overwrites, and retains original captures and hashes. It excluded unrelated later platform material from the Malik article supplied to extraction. Direct local publisher retrieval had returned a blocking page; that response was preserved and never treated as a PDF.
- Regression coverage checks both acquisition paths and their rejection cases. **181 tests passed**, selected fatal/import lint and whitespace checks passed, and **nine unique configured protocol/reference pairs** verified. Original Ma/Li/Rawat contracts and failures remain unchanged.

The source assistance and frozen backward-citation leads mean this is not validation of wholly autonomous discovery. The artifact audit establishes recorded consistency, not scientific truth or expert consensus. This case exercised a two-arm comparison through the multiarm adapter; no accepted multi-dose combination occurred. The broader project objective remains incomplete.

## Next bounded action

Do not rerun these unchanged sources or loosen their numerical gates. Qualify a new target using a contributor-level matrix of primary analyzed N, mean, SD/SE, unit, exact timepoint, independence and published selection **before** freezing execution. A new lead outside nutritional supplements is Zheng2023, PMC10270119, the prespecified pulse-pressure outcome: four parallel trials and fixed-effect MD, unlike its broader blood-pressure outcome that includes a crossover study. Only the review has been downloaded; primary accessibility, score definition, family independence and its92-versus-table91 participant discrepancy remain to be checked. It is not yet a qualified or launched benchmark. If any target contributor lacks usable primary inputs, reject it as a complete numerical-reproduction candidate and move on rather than launch another deliberately partial analysis.

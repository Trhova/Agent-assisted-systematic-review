# Development benchmark results — 12 October 2026

Historical first-pass observations are preserved below. Later autonomous acquisition, segmentation and verification work is tracked in [current execution status](autonomous_review_status.md) and `benchmarks/findings/runtime_*.json`; the test counts and remaining implementation work below describe that initial pass.

**Neither historical review was independently reproduced.** The runner executed search, screening, source acquisition, structured extraction, source verification, synthesis and comparison using real literature and authenticated model calls. Additional primary PDFs were supplied through evaluator-assisted web discovery; these runs therefore do not establish completely autonomous retrieval. The original review workflow and protocol remain intact.

| Frozen review | Records screened | Full-text candidates | Parsed reports | Unavailable | Input-limit errors | Validated effects | Unresolved candidates |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ma 2013, ALT | 972 | 105 | 15 | 80 | 10 | 2 | 93 |
| Li 2016, fasting glucose | 2,180 | 50 | 27 | 22 | 1 | 2 | 33 |

The input-limit failures are oversized source documents/conference collections, preserved without truncation. Unresolved counts also include eligible trials with missing or ambiguous measurements. “Parsed reports” includes ineligible full texts; it is not an included-trial count.

## Provisional estimates, not completed reviews

| Analysis | Current incomplete study set | Provisional result (95% CI) | Published target | Benchmark |
|---|---|---|---|---|
| Ma, fixed-effect endpoint ALT MD | Aller; Malaguarnera | −9.8006 U/L (−20.2371, 0.6358), k=2 | −23.71 (−33.46, −13.95), k=4 | Not reproduced |
| Li, random-effects endpoint FBG SMD | Ostadrahimi/kefir; Firouzi | −0.58966 (−0.90594, −0.27338), k=2 | −0.61 (−0.92, −0.30), k=9 | Not reproduced |

The similar Li point estimates are incidental: only one current contributor belongs to its nine-report reference set. Missing studies and different composition prevent a pass independently of numeric tolerance. These provisional estimates are not clinical conclusions.

## Source-level explanations

- **Ma coverage:** all four reference reports were found and retained; three original full texts became accessible with assistance. Vajro PMID 21505361 remains unavailable through attempted paths. Wong PMID 23396737 reports changes in ALT, without endpoint means/SDs required by the frozen protocol. Its secondary report also cannot provide those means/SDs. The protocol was not changed to force a match.
- **Li coverage:** 11 of 12 review reports were retrieved, 10 retained, and five full texts accessible. The missing search report, PMID 24319552, concerns brewer’s yeast; the frozen microbiome query lacks yeast terms. Bayat PMID 26955460 was excluded because its control received dietary advice rather than placebo. These are explicit query/eligibility differences from the historical included set.
- **Apparent SE/SD discrepancy:** Asemi PMID 23899653 Table 3 and Mazloom PMID 23645956 Table 2 label dispersion as SE. Li Figure 3 places identical values in SD columns (Asemi 9.5/12; Mazloom 16.38/16.38). The pipeline refused to reinterpret SE as SD. This merits independent scientific adjudication; numerical reproduction alone would reward an apparent error. The compact audit is in `benchmarks/findings/li2016_dispersion_audit.json`.
- **Other uncertainty:** Shavakhi PMID 23930163 has conflicting arm counts and was not accepted. Several reports omit outcome-specific analyzed denominators. Trial-family linkage across separate reports is still incomplete. Accepted rows retain reporting caveats and the original source evidence.

Primary sources: [Wong trial](https://www.medigraphic.com/pdfs/hepato/ah-2013/ah132l.pdf), [Aller trial](https://www.europeanreview.org/wp/wp-content/uploads/1039.pdf), [Asemi trial PDF](https://magistralbr.caldic.com/storage/product-files/1151404700.pdf), [Mazloom trial](https://pmc.ncbi.nlm.nih.gov/articles/PMC3642943/), [Firouzi trial PDF](https://bcrobes.com.my/pdf/Probiotics%20Reduces%20HbA1c%20and%20Fasting%20Insulin%20in%20Type%202%20Diabetes.pdf). Locally preserved metadata identifies all other source URLs and hashes.

## Numerical calibration and verification

A **separate secondary-source calibration** using Li’s printed forest-plot inputs produced SMD −0.6077924368 (95% CI −0.9174281125 to −0.2981567612), I² 65.57994%, k=9. These round to the published result. This validates RevMan-compatible arithmetic, not primary extraction, data correctness or independent reproduction. The runner never reads the calibration inputs.

Twenty-four automated tests pass, covering statistics, API payloads, source retrieval checks, evidence repair, cache validation, a complete synthetic pipeline fixture, and stale-result prevention. Selected syntax/import/static checks and `git diff --check` pass for changed files. There is an unrelated pre-existing unused import in `03_screen_abstracts_llm.py`; the whole-repository lint suite is not claimed clean. No live OpenAI API call was made; real model execution used existing Codex authentication with its default model, not a pinned model revision.

## Reproducibility and remaining work

The compact observed outputs are committed-ready in `benchmarks/findings/2026-10-12_results.json`. Raw searches, PDFs/JATS, source-discovery logs, model prompts/results, code snapshots and prior attempts remain locally under ignored `data/benchmarks/`. Both final runs used code hash `edb5cffb0b2e465ba06d18ee568be2d6a04d3592590953e105bba616a822b8db`. They finished with `incomplete` status and exit code 2; no benchmark process is intentionally left running.

The next scientifically justified steps are to acquire the remaining lawful original reports/supplements, independently adjudicate the SE/SD and endpoint/change issues, freeze explicitly revised sensitivity protocols (including yeast and comparator definitions where warranted), add robust trial-family/multiarm handling and source segmentation, and then run a new untouched evaluation with automatic source discovery and a pinned model. Reusing cached development responses is not a held-out benchmark. The system is an implemented, tested development pipeline, **not yet a completely autonomous production review system**.

# Protocol (high level)

Scope: **human randomized, placebo-controlled clinical trials** (2014–2024) evaluating **live microbiome interventions** for metabolic disease indications:
- T2D/prediabetes
- obesity/overweight
- MASLD/NAFLD
- NASH

Included interventions:
- probiotics (live)
- synbiotics **with a live component**
- defined consortia
- engineered live microbes

Exclusions:
- fecal microbiota transplant (FMT)
- postbiotics / heat-killed / nonliving
- nonliving small molecules
- diet-only interventions

See `protocol/protocol.yaml` for machine-readable rules and `docs/decision_rules.md` for tier logic.

## Search strategy (2-pass)

This repo uses a 2-pass PubMed strategy defined in `protocol/queries.yaml`:
- **Precision** query: uses PubMed publication-type trial filters (`[pt]`) plus exclusions for reviews/editorials/protocols.
- **Recall** query (optional): omits trial `[pt]` filters but requires trial language in title/abstract to catch mis-tagged trials.

After fetching, we apply strict cleanup using PubMed `PublicationTypeList` plus a small heuristic on trial language; see `PublicationTypes`, `ExcludedByPTFilter`, and `ExclusionReasonAuto` columns in the master table for auditability.

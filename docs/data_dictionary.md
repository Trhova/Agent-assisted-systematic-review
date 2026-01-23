# Data dictionary

Stable screening/final table columns (order preserved in outputs).

Legend:
- `auto`: rule-based / fetched
- `llm`: LLM-extracted (schema validated)
- `manual`: human input (table edits)
- `derived`: computed deterministically

Columns:
- `PMID` (auto): PubMed identifier.
- `Year` (auto): publication year (best effort).
- `Journal` (auto)
- `Title` (auto)
- `IndicationBucketHint` (auto/llm): T2D/prediabetes, obesity/overweight, MASLD/NAFLD, NASH, unknown.
- `EndpointsTagged` (auto/llm): semicolon-separated tags.
- `TierSuggestedFromAbstract` (auto/llm): rough tier suggestion or `unknown`.
- `InterventionAliveHint` (auto/llm): `true/false/unknown`.
- `RandomizedHint` (auto/llm): `true/false/unknown`.
- `PlaceboHint` (auto/llm): `true/false/unknown`.
- `DoubleBlindHint` (auto/llm): `true/false/unknown`.
- `TrialRegistryIDs` (auto/llm): comma-separated IDs (e.g., NCT01234567).
- `NeedsRegistryCheck` (auto/llm): boolean.
- `PublicationTypes` (auto): semicolon-separated PubMed publication types (from `PublicationTypeList`).
- `ExcludedByPTFilter` (auto): boolean; true if removed from downstream screening due to publication type / heuristic.
- `ExclusionReasonAuto` (auto): populated explanation for `ExcludedByPTFilter` (PT-based or heuristic).
- `Include_YN` (manual/llm): `Y`, `N`, or empty.
- `Reason_Exclude` (manual/llm): short canonical reason.
- `Intervention_Class` (llm/manual)
- `Intervention_Name` (llm/manual)
- `Strains_or_Consortium` (llm/manual)
- `Dose` (llm/manual)
- `Duration_weeks` (llm/manual): numeric or empty.
- `Population_notes` (llm/manual)
- `Primary_endpoint_verbatim` (llm/manual)
- `Primary_endpoint_category` (llm/derived): taxonomy category.
- `Outcome_direction` (llm/manual): `improved`, `no_effect`, `worsened`, `mixed`, `unknown`.
- `Effect_size` (llm/manual): free text.
- `Durability_timepoint` (llm/manual): free text, preferably weeks.
- `TierFinal` (derived/manual): `Tier 1`, `Tier 2a`, `Tier 2b`, `Tier 3`, or empty.
- `RoB2_overall` (llm/manual): `low`, `some_concerns`, `high`, `unknown`.
- `RoB2_notes` (llm/manual)
- `Multiplicity_flags` (derived): semicolon-separated flags.
- `Comments` (manual)
- `record_id` (derived): deterministic sha256(PMID + normalized title).

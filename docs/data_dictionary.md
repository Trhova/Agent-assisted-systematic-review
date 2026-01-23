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
- `TrialRegistryIDs` (auto/llm): semicolon-separated IDs (e.g., NCT01234567;ISRCTN12345678).
- `NeedsRegistryCheck` (auto/llm): boolean; true when no registry IDs captured.
- `PublicationTypes` (auto): semicolon-separated PubMed publication types (from `PublicationTypeList`).
- `ExcludedByPTFilter` (auto): boolean; true if removed from downstream screening due to publication type / heuristic.
- `ExclusionReasonAuto` (auto): populated explanation for `ExcludedByPTFilter` (PT-based or heuristic).
- `Include_YN` (manual/llm): `Y`, `N`, `U` (uncertain but carry-forward), or empty (not screened yet).
- `Reason_Exclude` (manual/llm): PRISMA-style reason (category + free text) when excluded.
- `Reason_Exclude_Category` (llm/manual): PRISMA-compatible exclusion category (e.g., "Not RCT").
- `NeedsFullTextReview` (llm/manual): boolean; true when abstract screening returns uncertain.
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
- `MagnitudeBarPass` (derived): `Y/N/U` for Tier 1 or Tier 2a; separate magnitude layer (not part of TierFinal).
- `MagnitudeBarNotes` (derived): how `MagnitudeBarPass` was computed.
- `RoB2_overall` (llm/manual): `Low` / `Some concerns` / `High` (or legacy `low`/`some_concerns`/`high`).
- `RoB2_notes` (llm/manual)
- `RoB2_domains_json` (llm): JSON string of full RoB2 domain answers for auditability.
- `Multiplicity_flags` (derived): semicolon-separated flags.
- `Comments` (manual)
- `record_id` (derived): deterministic sha256(PMID + normalized title).

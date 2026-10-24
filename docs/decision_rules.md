# Decision rules

This repo uses deterministic tiering (no LLM) in `scripts/06_apply_overrides_and_export.py`, based on:
- minimum design bar (randomized + placebo)
- endpoint category (clinical non-surrogate vs validated surrogate vs others)
- primary endpoint success (as extracted)
- durability thresholds
- multiplicity considerations
- RoB2 overall rating

## Assessment status and inclusion (export step)

The export step first classifies every record into one `AssessmentStatus` from the
decision columns written by the earlier steps. The states partition the table, so
PRISMA counts always add up to `identified`:

| `AssessmentStatus` | Derived from | Exported as |
| --- | --- | --- |
| `excluded_pt_filter` | `Include_YN` empty and `ExcludedByPTFilter` true | not screened downstream |
| `not_screened` | `Include_YN` empty (script 03 has not run on the record) | `TierFinal` empty |
| `excluded_abstract` | `Include_YN` = `N` without full-text extraction | abstract-stage reason kept |
| `fulltext_not_assessed` | `Include_YN` in {`Y`,`U`} but `Outcome_direction` empty (script 04 has not run) | `TierFinal` empty |
| `excluded_fulltext` | `Include_YN` in {`Y`,`U`}, extraction present, and an explicit protocol exclusion (see below) | `Include_YN` set to `N` with a PRISMA reason |
| `included` | `Include_YN` = `Y`, extraction present, no exclusion | tiered |
| `included_uncertain` | `Include_YN` = `U`, extraction present, no exclusion | tiered; needs a human override to become `Y` or `N` |

`Outcome_direction` is the marker for a completed full-text assessment because it is a
required field of the extraction schema and script 04 writes it unconditionally.

Full-text exclusion is deterministic and only acts on explicit evidence; `unknown`
hints never exclude (they lower the tier instead):
- `Intervention_Class` in the protocol `exclusions` list (FMT, postbiotics/non-living, small molecules, diet only) or `InterventionAliveHint` = `false` → "Intervention not live microbiome"
- `RandomizedHint` = `false` → "Not RCT"
- `PlaceboHint` = `false` → "No placebo control"

The export step never upgrades `U` to `Y`: uncertain abstract decisions are carried
forward, tiered, counted separately (`included_uncertain`) and left for a human override.

Records that are `not_screened` or `fulltext_not_assessed` are **not tiered**. An empty
`TierFinal` means "not assessed"; `Tier 3` means "assessed and failing the efficacy bar".
`prisma_counts.json` reports `fulltext_retrieved` (text downloaded) separately from
`fulltext_assessed` (extraction decision present), lists `warnings` for every incomplete
stage and sets `assessment_complete` only when nothing is pending.

## Tier assignment (included records only)

1. Non-living intervention (hint `false` or excluded class) → Tier 3.
2. Minimum design bar not met (`RandomizedHint` and `PlaceboHint` not both `true`) → Tier 3.
3. Primary endpoint not met (`Outcome_direction` ≠ `improved`, or `Effect_size` reports non-significance) → Tier 3.
4. Durability below the protocol threshold for the endpoint category → Tier 2b.
5. RoB2 overall not in `acceptable_rob2` (including missing) → Tier 2b.
6. Otherwise: clinical non-surrogate endpoint → Tier 1; validated surrogate → Tier 2a; other → Tier 2b.

`Duration_weeks` / `Durability_timepoint` accept numbers or text such as `12 weeks`, `8 wk`.
The magnitude bar (`MagnitudeBarPass`) is a separate layer computed for Tier 1/2a only.

Overrides:
- Human corrections live in `overrides/overrides.jsonl` and are applied at export only.
- Overrides on input columns (for example `Include_YN`, `Outcome_direction`, `RoB2_overall`) are applied **before** derivation so they feed it; overrides on derived columns (`TierFinal`, `MagnitudeBarPass`, `MagnitudeBarNotes`, `Multiplicity_flags`, `AssessmentStatus`) are applied **after** and are the final word.

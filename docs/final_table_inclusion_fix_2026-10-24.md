# Final table inclusion fix (2026-10-24)

## Symptom

`data/outputs/final_table.parquet` (written 2026-01-23) has 274 rows, `TierFinal` =
`Tier 3` for all 274, `Include_YN` empty for all 274, while `prisma_counts.json` reports
`fulltext_assessed: 111`, `screened: 0`, `included: 0`.

## Root cause

Two layers, both verified offline against the January files.

1. **The LLM steps were never run on this table.** `data/intermediate/llm/screening`,
   `.../extraction` and `.../rob2` are empty, and in `screening_table.parquet` every
   decision column is empty for all 274 records: `Include_YN`, `Reason_Exclude*`,
   `Intervention_Class`, `Outcome_direction`, `Primary_endpoint_category`,
   `Duration_weeks`, `Effect_size`, `RoB2_overall`. Only steps 00 (search), 01 (build
   table) and 02 (PDF download/text extraction, 111 texts) ran. The "111 full texts
   assessed" figure was `prisma_counts()` counting files in
   `data/intermediate/fulltext_text/`, i.e. full texts *retrieved*, not assessed.

2. **The export step tiered every record regardless of whether it had been assessed.**
   In `scripts/06_apply_overrides_and_export.py`, `main()` called `assign_tier()` on
   all rows. `assign_tier()` never consulted `Include_YN` or the presence of
   extraction data; with `Outcome_direction` empty, `_primary_outcome_met()` returned
   `primary_outcome_unknown` and the function fell through to `Tier 3` (the final-table
   `Multiplicity_flags` are `rob2_unknown;primary_outcome_unknown` for 191 rows and
   variants for the rest). Nothing in the export step ever wrote `Include_YN`, so it
   stayed empty and `included` was 0. An unassessed record was therefore
   indistinguishable from an assessed study that failed the efficacy bar.

A third, latent defect was found while checking the tier rules: all regular
expressions in the script were double-escaped inside raw strings (`r"(\\d+..."`), so
`_parse_weeks("12 weeks")` returned `None`, the non-significance check never matched,
and the magnitude-bar parsers never matched. Because script 04 stores
`Duration_weeks` as a string, every validated-surrogate trial would have been demoted
to `Tier 2b` (`durability_below_threshold`) once the LLM steps had run. Checked on the
HEAD script: a clean positive 12-week HbA1c trial tiered as `Tier 2b` instead of
`Tier 2a`.

## Change

`scripts/06_apply_overrides_and_export.py`
- New derived column `AssessmentStatus` partitioning the table into
  `excluded_pt_filter`, `not_screened`, `excluded_abstract`, `fulltext_not_assessed`,
  `excluded_fulltext`, `included`, `included_uncertain` (rules in
  `docs/decision_rules.md`). `Outcome_direction` non-empty is the marker for a
  completed full-text extraction (required, unconditionally written by script 04).
- `assign_tier()` returns an empty tier unless `Include_YN` in {Y, U} and extraction is
  present. Empty `TierFinal` now means "not assessed".
- `derive_record()` sets `Include_YN = N` with a PRISMA reason only for explicit
  protocol exclusions found at full text (excluded intervention class, non-living
  hint, randomized/placebo hint explicitly `false`). `U` is never upgraded to `Y`.
- `prisma_counts()` is derived from `AssessmentStatus` (sums to `identified` by
  construction), reports `fulltext_retrieved` separately from `fulltext_assessed`,
  adds `not_screened`, `fulltext_not_assessed`, `included_uncertain`,
  `tiers_included`, `warnings` and `assessment_complete`.
- Overrides on input columns are applied before derivation, overrides on derived
  columns after.
- Regexes fixed; `_parse_weeks` also accepts `wk` and numeric strings.
- New CLI options `--outputs-dir`, `--work-dir`, `--overrides`, `--fulltext-dir`
  (defaults unchanged) so the step can be re-run into a scratch directory.
- `main(argv)` is importable for tests.

`scripts/utils.py`, `scripts/01_build_table.py`: `AssessmentStatus` added to the stable
column list (after `Multiplicity_flags`); scripts 03-05 add missing stable columns
automatically, so older tables load unchanged.

`docs/decision_rules.md`, `docs/data_dictionary.md`, `README.md`: documented.

## Test evidence

- New `tests/test_export_inclusion.py` (12 tests): unscreened row is not Tier 3;
  screened-in row without extraction is `fulltext_not_assessed`; duration parsing;
  Tier 1 / 2a / 2b / 3 assignment on synthetic assessed rows; full-text protocol
  exclusion with idempotent re-derivation; unknown hints lower tier but do not exclude;
  `U` carried forward; end-to-end `main()` into a tmp directory with override and
  PRISMA identity checks; the project table (if present) is reported as not screened.
- Against the HEAD script all 12 fail (`12 failed in 0.80s`); against the fix they pass.
- Full suite before: `462 passed in 7.70s`. After: `474 passed in 3.91s`.

## Offline re-run on the January screening table

Run into a scratch directory (no network, no LLM, January outputs and
`data/intermediate` untouched):

```
.venv/bin/python scripts/06_apply_overrides_and_export.py --protocol protocol/protocol.yaml \
  --table data/outputs/screening_table.parquet --outputs-dir <scratch>/outputs --work-dir <scratch>/work
```

Result: 274 rows, `AssessmentStatus = not_screened` for all 274, `TierFinal` empty for
all 274, `Include_YN` empty, PRISMA `identified 274, not_screened 274, screened 0,
fulltext_retrieved 111, fulltext_assessed 0, included 0, assessment_complete false`,
with warnings "274 records have no abstract screening decision (scripts/03 ... has not
been run on them)" and "111 full texts were retrieved but none has been assessed".

Before/after included count: 0 → 0. The count is unchanged because the table genuinely
contains no screening or full-text decisions; the export now says so instead of
labelling every record `Tier 3`. No inclusion decisions were fabricated.

## What remains open

- `scripts/03_screen_abstracts_llm.py`, `04_extract_fulltext_llm.py` and
  `05_rob2_llm.py` still need to be run (requires `OPENAI_API_KEY`) before the review
  can have included studies. After that, `make export` will derive inclusion and tiers
  from their outputs.
- The January `data/outputs/final_table.*` and `prisma_counts.json` were deliberately
  not overwritten (the default export also rewrites `data/intermediate/export/`).
  Re-running `make export` regenerates them deterministically from the screening table.
- `RandomizedHint`/`PlaceboHint` come from the abstract stage (scripts 01/03); script 04
  does not re-extract design flags from the full text, so the minimum design bar still
  rests on abstract-level hints.
- `TierSuggestedFromAbstract` (23 Tier 1 / 184 Tier 2a) is a heuristic hint from
  script 01 and is intentionally not used for `TierFinal`.

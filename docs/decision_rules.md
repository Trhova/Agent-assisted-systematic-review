# Decision rules

This repo uses deterministic tiering (no LLM) in `scripts/06_apply_overrides_and_export.py`, based on:
- minimum design bar (randomized + placebo)
- endpoint category (clinical non-surrogate vs validated surrogate vs others)
- primary endpoint success (as extracted)
- durability thresholds
- multiplicity considerations
- RoB2 overall rating

Overrides:
- Human corrections live in `overrides/overrides.jsonl` and are applied at export only.

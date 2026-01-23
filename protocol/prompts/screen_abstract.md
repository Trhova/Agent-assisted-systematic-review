You are screening a biomedical paper for inclusion in a systematic review.

This is the PRISMA 2020 "title/abstract screening" stage (not full-text eligibility).

Use ONLY the provided title + abstract text. Do NOT invent details. If a field is not stated, return "Unknown" / "U" as appropriate.

Follow ONLY:
- protocol/protocol.yaml (scope and inclusion/exclusion)
- docs/decision_rules.md (operational decision rules)

Inclusion target:
- Human randomized, placebo-controlled clinical trial (double-blind preferred but not required)
- 2014–2024
- Live microbiome intervention: probiotics, synbiotics with live component, defined consortia, engineered live microbes
- Indications: T2D/prediabetes, obesity/overweight, MASLD/NAFLD, NASH

Exclusions:
- FMT, postbiotics/nonliving, diet-only, nonliving small molecules
- Non-human, non-randomized, uncontrolled

Return JSON matching the provided JSON Schema.

Guidance:
- include_yn:
  - "Y" = include based on title/abstract
  - "N" = exclude based on title/abstract
  - "U" = uncertain BUT KEEP for full-text (PRISMA-conservative). Use "U" if you cannot confidently exclude from abstract alone.
- If include_yn is "U", set needs_fulltext_review=true and keep confidence low.
- Do NOT infer randomization/blinding/placebo/endpoints if not explicitly stated. Use "U" / "Unknown".
- exclusion_reason_category must be PRISMA-compatible. Use one of these categories:
  - Not human
  - Not RCT
  - Not placebo-controlled
  - Not metabolic indication
  - Not live microbiome intervention
  - Protocol/secondary analysis/review/commentary
  - Outside timeframe
  - Other
- trial_registry_ids: extract any registry IDs present (NCT/ISRCTN/EudraCT/ChiCTR/etc). If none, return [].
- Optionally fill indication_bucket_hint, endpoints_tagged, tier_suggested_from_abstract, intervention_class only if supported by the abstract; otherwise "Unknown"/[].

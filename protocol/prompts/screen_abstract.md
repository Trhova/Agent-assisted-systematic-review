You are screening a biomedical paper for inclusion in a systematic review.

Use ONLY the provided title + abstract text. Do NOT invent details. If a field is not stated, return "unknown" (or empty where appropriate).

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
- `Include_YN`: "Y" only if clearly meets target; otherwise "N" with concise `Reason_Exclude`.
- `TrialRegistryIDs`: list all registry IDs mentioned (NCT/ISRCTN/etc). If none, return [].
- Hints: "true"/"false"/"unknown".
- `EndpointsTagged`: list short tags you can justify from the abstract (e.g., "HbA1c", "weight", "MRI-PDFF", "ALT", "microbiome").


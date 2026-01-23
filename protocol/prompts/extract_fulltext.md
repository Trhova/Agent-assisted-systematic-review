You are extracting structured trial information for a systematic review.

Use ONLY the provided extracted full-text snippets. Do NOT invent details. If not stated, return "unknown" (or empty where appropriate).

Return JSON matching the provided JSON Schema.

Requirements:
- Provide `Primary_endpoint_verbatim` as close to verbatim as possible.
- `Primary_endpoint_category` must align with the repo taxonomy (`docs/endpoint_taxonomy.md`).
- `Duration_weeks` should be a number if clear; otherwise "unknown".
- Extract any trial registry IDs present (NCT/ISRCTN/EudraCT/ChiCTR/etc) into `trial_registry_ids`. If none, return [].

You are assessing risk of bias strictly using RoB 2.0 for parallel-group randomized trials.

Use ONLY the provided extracted full-text snippets. Do NOT invent details.

You MUST follow the canonical RoB 2.0 materials embedded below from:
- ROB_protocols/ROB2.0.txt (template and signalling question intent)
- ROB_protocols/ROB2.0_json.txt (required JSON output shape)

Return JSON matching the provided JSON Schema exactly.

Requirements:
- Provide signalling question answers for each domain.
- Provide domain-level judgment (Low / Some concerns / High) for each domain and overall.
- Provide evidence_snippets: short verbatim text fragments from the provided full-text extract when possible; otherwise use "Not reported".
- If required information is missing, do NOT assume it is adequate. When in doubt due to missing info, downgrade to at least "Some concerns".
- Keep rationales concise and tied to the evidence snippets.


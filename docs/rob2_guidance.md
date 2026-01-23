# RoB2 guidance (Cochrane RoB 2)

Domains to assess (trial-level):
1. Bias arising from the randomization process
2. Bias due to deviations from intended interventions
3. Bias due to missing outcome data
4. Bias in measurement of the outcome
5. Bias in selection of the reported result

The LLM prompt requires:
- a judgment per domain: `low`, `some_concerns`, or `high`
- short evidence notes anchored in the provided text
- an overall rating and a brief explanation

Common cues:
- Randomization: sequence generation, allocation concealment, baseline balance
- Deviations: blinding, adherence, co-interventions
- Missing data: attrition, reasons, ITT vs per-protocol
- Measurement: blinded assessors, objective measures
- Reporting: protocol registration, prespecified outcomes, multiple analyses


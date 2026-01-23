# Endpoint taxonomy

Endpoint categories used for deterministic tiering:

Clinical non-surrogate (Tier 1 candidates):
- incident T2D diagnosis
- medication initiation/escalation
- clinical events (rare in these trials)

Validated surrogate (Tier 2a candidates):
- HbA1c
- fasting plasma glucose
- HOMA-IR (often treated as surrogate, but less validated than HbA1c)
- body weight / BMI / waist circumference
- imaging-derived liver fat (MRI-PDFF, MRS)

Weak surrogate:
- ALT/AST
- lipids
- inflammatory markers

Exploratory:
- microbiome composition/function only
- SCFAs, bile acids (unless tied to prespecified clinical endpoint)

The canonical mapping lives in `protocol/protocol.yaml`.


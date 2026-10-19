# Executed post-cutoff Li fixed-input sensitivity

The separately frozen four-trial sensitivity completed on15October2026 at10:47:27UTC. It adds the recovered soy comparison to the **exact three independent effects** in the preserved Li v3 synthesis. It is a developer-assisted, post-hoc fixed-input sensitivity—not a complete updated review, historical Li reproduction or prospective validation.

| Analysis | Independent trials | Analyzed participants | Endpoint SMD (95% CI) | I² |
|---|---:|---:|---|---:|
| Preserved Li v3 quantitative baseline | 3 | 158 | −0.355548 (−0.940752 to0.229657) | 67.0156% |
| Baseline plus post-cutoff soy comparison | 4 | 198 | −0.271578 (−0.704125 to0.160969) | 54.1369% |

The added comparison moves the estimate toward zero; both intervals include zero. This does not establish equivalence or absence of effect. The baseline remains incomplete because its unresolved trials are still unresolved. No comparison to a historical pooled target can validate this expanded post-cutoff set.

## Scientific contract and source decisions

Baseline rows are exactly PMIDs26955460,24319552 and23645956 from `reproduction_v3_suite/li2016_t2d_fbg_reproduction_v3/664e53794051/trial_families.json`. Their source values, eligibility, old family links and synthesis remain unchanged. The added row is27757829, representing the single IRCT201405265062N8 trial shared with26261453/26577825. Its first-online18October2016 date is beyond Li's12April2016 cutoff. The explicit known-report addendum extends through1March2017 but does not claim an exhaustive intervening search.

The estimand remains unadjusted end-of-treatment FBG endpoint SMD, with Hedges correction, the existing RevMan sampling variance, DerSimonian–Laird random effects and normal95%intervals. No change scores, guessed N/SD or additional arms were introduced. Reported SE15.6/17.4 with analyzedN20each yields SD69.76532089799343/77.81516561699267 through the already specified transformation; means remain132/135mg/dL. Its random-effects weight in the four-effect sensitivity is23.8225%. Source quotations, locators and transformation audit remain attached to the row.

The pre-existing `family_evidence_tiers_v2` rule was separately frozen for new-versus-baseline pairs; old baseline pair decisions were retained. It requires affirmative original evidence of distinct randomizations and another corroborating feature, then separate verification. This follows the documented interpretation of [Cochrane Handbook4.6.2](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-04), accessed15October2026, on using multiple characteristics to link study reports. Different registrations alone are insufficient, and positive reuse/conflicting linkage remain blocking. The guidance does not guarantee participant-level disjointness.

All three new pairs ultimately passed. Primary evidence distinguishes Bayat's80-person/four-arm yogurt/pumpkin/dietary-advice randomization from the48-person/two-arm soy randomization, yeast versus soy cohorts, and the Mazloom capsule versus soy cohorts. Participant identifiers and explicit cross-trial overlap assessments are unavailable. Shared-site theoretical reenrollment remains a limitation, not a claimed impossibility. The family records also retain source inconsistencies: Bayat narrative age/BMI versus baseline-table differences, and the yeast report's recruited/randomized wording discrepancy. The latter does not change the preserved outcome-specific42-per-arm completer input; randomized and analyzed denominators are distinct. Indexed publication-integrity checks remain limited to their frozen metadata snapshot.

## Actual runs and the preserved failed attempt

V1 launchedPID7544/child7545, code `52ead851ad532bd0c9024757b910bc95833ec5ee709b3c1c97a22b0c0c3cc63a`. It completed10:45:43UTC, exit0, after11fresh adaptercalls. Two pairs passed; the Bayat–soy pair failed exact quotation matching despite a positive scientific verifier. Its evidence strings retained typographic quotation marks and appended page/report labels after the existing bounded repairs. The four-effect pool was correctly withheld, rather than dropping Bayat. V1's no-pool result and all raw attempts remain immutable in `data/benchmarks/li_soy_fixed_input_addendum_v1`.

This exposed a reusable workflow defect: asking the model to repair an entire scientific proposal lets evidence-field formatting persist and permits unnecessary semantic rewriting. New `scripts/family_quote_repair.py` repairs only a fixed ordered list of paired evidence strings. It cannot change identity, participant-reuse category, feature domains/count, reason or limitations. Every string still requires exact matching apart from whitespace, and a fresh full-source verifier must support the entire scientific proposal. An adverse/uncertain scientific verdict is not eligible for this repair. Documented reuse remains blocked.

V2 froze this evidence-only continuation before calls in `protocol/extensions/li_soy_fixed_input_addendum_v2.md`. It replayed all11V1family requests/schema/responses, reused the two valid pairs, and spent exactly2fresh calls on the remaining pair. Launcher16035/child16036 completed10:47:27UTC, exit0; code `a68f069d36cffc0538910df1a1e27ca324219ce066c314d69f45ff0280a9a742`. Explicitgpt-6-astra/codex, workerMedium; nested effort backend-default/unpinned. One attempt per adapter invocation; internal CLI transport retries are not counted by this bound. Same-model separated calls may share errors. The two runs made13fresh calls in total; cached replay is not counted as a fresh call.

No published pooled answers, review forest values or desired sensitivity estimates entered the model requests. Model work assessed original-report study identity; scientific values were fixed before those decisions. `scripts/fixed_input_addendum.py` requires baseline artifact audit/arithmetic replay, exact candidate response replay, complete pair coverage and survival of every prespecified record before synthesis. Missing/unclear links produce no new pool; selective omission is forbidden.

## Audits and remaining work

399tests pass, including18new cases covering exact fixed-set membership, duplicate/missing pairs, shared-registry conflicts, no partial pooling, immutable scientific features, annotated/unmatched snippets, adverse verifiers and affirmative reuse. Focused changed-code lint and whitespace checks pass; previously documented broad lint limitations remain.

V1 and V2 audits replay their actual original-source family requests and numerical decisions. V2 validates163pins, all1040original baseline files unchanged,11prior candidate-response chains,11V1family chains and2new V2chains. The old baseline synthesis and the four-effect sensitivity both reproduce deterministically under frozen code with1e-12absolute/relative tolerance. The original failed source attempt and original Li targets/results remain untouched. No live model or numerical runner remains.

```bash
PYTHONPATH=. .venv/bin/python data/benchmarks/li_soy_fixed_input_addendum_v1/audit_replay.py
PYTHONPATH=. .venv/bin/python data/benchmarks/li_soy_fixed_input_addendum_v2/audit_replay.py
```

Do not rerun these completed pools unchanged. The next useful scientific action is a bounded primary companion/protocol investigation for the unresolved Mohamadshahi trial PMID25035851 (PMC4097976): its original source reports44recruited and42attending two visits, with two withdrawals but no arm allocation. Seek genuinely new arm-specific analyzed-denominator evidence, preserving family identity and chronology; never infer21/21. If unavailable, retain the missing denominator and move to another concrete source blocker. Original six Ma/Li access gaps, Alabed five report gaps and Popp three unresolved records remain; the overall autonomous-review objective is incomplete.

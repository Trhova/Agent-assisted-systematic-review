from pathlib import Path

from scripts.utils import load_json_schema, validate_json, validate_llm_output


def test_json_schemas_are_valid():
    for p in [
        Path("protocol/schemas/screening.schema.json"),
        Path("protocol/schemas/extraction.schema.json"),
        Path("protocol/schemas/rob2.schema.json"),
    ]:
        load_json_schema(p)


def test_screening_schema_and_pydantic_accept_sample():
    schema = load_json_schema(Path("protocol/schemas/screening.schema.json"))
    payload = {
        "include_yn": "U",
        "exclusion_reason_category": "",
        "exclusion_reason_free_text": "",
        "flags": {
            "randomized": "U",
            "placebo": "U",
            "double_blind": "U",
            "live_intervention": "U",
            "metabolic_indication": "U",
        },
        "trial_registry_ids": ["NCT01234567"],
        "confidence": 0.5,
        "needs_fulltext_review": True,
        "indication_bucket_hint": "Unknown",
        "endpoints_tagged": [],
        "tier_suggested_from_abstract": "Unknown",
        "intervention_class": "Unknown",
    }
    ok, errors = validate_json(schema, payload)
    assert ok, errors

    ok2, cleaned, err = validate_llm_output("screening", payload)
    assert ok2, err
    assert cleaned is not None


def test_rob2_pydantic_accepts_sample():
    payload = {
        "study_metadata": {
            "reference": "PMID: 123",
            "outcome_assessed": "HbA1c",
            "effect_of_interest": "assignment",
            "sources_used": ["journal_article"],
        },
        "domain_1_randomization": {
            "signaling_questions": {"allocation_sequence_random": "NI", "allocation_concealed": "NI", "baseline_imbalance": "NI"},
            "judgment": "Some concerns",
            "rationale": "Randomization/concealment not described.",
            "evidence_snippets": ["Not reported"],
        },
        "domain_2_deviations_from_intended_interventions": {
            "effect_of_interest": "assignment",
            "signaling_questions": {
                "participants_aware": "NI",
                "carers_aware": "NI",
                "contextual_deviations": "NI",
                "deviations_affect_outcome": "NI",
                "deviations_balanced": "NI",
                "appropriate_analysis_used": "NI",
                "failure_impacts_result": "NI",
            },
            "judgment": "Some concerns",
            "rationale": "Insufficient blinding/analysis detail.",
            "evidence_snippets": ["Not reported"],
        },
        "domain_3_missing_outcome_data": {
            "signaling_questions": {
                "data_complete": "NI",
                "bias_from_missing_unlikely": "NI",
                "missing_depends_on_true_value": "NI",
                "dependence_likely": "NI",
            },
            "judgment": "Some concerns",
            "rationale": "Attrition handling not described.",
            "evidence_snippets": ["Not reported"],
        },
        "domain_4_measurement_of_outcome": {
            "signaling_questions": {
                "measurement_inappropriate": "NI",
                "measurement_differs_between_groups": "NI",
                "assessors_aware": "NI",
                "assessment_influenced": "NI",
                "influence_likely": "NI",
            },
            "judgment": "Some concerns",
            "rationale": "Outcome assessment blinding not described.",
            "evidence_snippets": ["Not reported"],
        },
        "domain_5_selection_of_reported_result": {
            "signaling_questions": {"analysis_prespecified": "NI", "multiple_eligible_outcomes": "NI", "multiple_eligible_analyses": "NI"},
            "judgment": "Some concerns",
            "rationale": "No protocol/SAP evidence.",
            "evidence_snippets": ["Not reported"],
        },
        "overall_risk_of_bias": {
            "judgment": "Some concerns",
            "rationale": "Multiple RoB2 domains have insufficient reporting.",
            "highest_risk_domain": "domain_1_randomization",
            "confidence": 0.4,
        },
    }
    ok, cleaned, err = validate_llm_output("rob2", payload)
    assert ok, err
    assert cleaned is not None

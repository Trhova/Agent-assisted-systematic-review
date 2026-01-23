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
        "Include_YN": "N",
        "Reason_Exclude": "not_rct",
        "IndicationBucketHint": "unknown",
        "EndpointsTagged": [],
        "TierSuggestedFromAbstract": "unknown",
        "InterventionAliveHint": "unknown",
        "RandomizedHint": "unknown",
        "PlaceboHint": "unknown",
        "DoubleBlindHint": "unknown",
        "TrialRegistryIDs": [],
        "confidence": {"include_decision": 0.5, "overall": 0.5},
    }
    ok, errors = validate_json(schema, payload)
    assert ok, errors

    ok2, cleaned, err = validate_llm_output("screening", payload)
    assert ok2, err
    assert cleaned is not None


def test_rob2_pydantic_accepts_sample():
    payload = {
        "domain_1_randomization": "some_concerns",
        "domain_2_deviations": "low",
        "domain_3_missing_data": "low",
        "domain_4_measurement": "low",
        "domain_5_reporting": "some_concerns",
        "overall": "some_concerns",
        "notes": "Insufficient detail about allocation concealment; otherwise OK.",
    }
    ok, cleaned, err = validate_llm_output("rob2", payload)
    assert ok, err
    assert cleaned is not None


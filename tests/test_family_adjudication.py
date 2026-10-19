from scripts.family_adjudication import adjudicate


def test_report_pair_requires_source_quotes_and_independent_verification():
    rows = [{"record_id": "a"}, {"record_id": "b"}]
    replies = iter(
        [
            {
                "relationship": "same_trial",
                "evidence_a": "invented",
                "evidence_b": "invented",
                "reason": "guess",
            },
            {
                "relationship": "same_trial",
                "evidence_a": "Trial 123",
                "evidence_b": "Trial 123",
                "reason": "same participants",
            },
            {
                "valid": False,
                "reason": "Registry alone does not establish participant overlap",
            },
        ]
    )
    result = adjudicate(
        rows, {"a": "Trial 123", "b": "Trial 123"}, lambda *args: next(replies)
    )
    assert result[0]["relationship"] == "unclear"
    assert not result[0]["independently_verified"]


def test_pair_budget_is_unresolved_not_silently_independent():
    result = adjudicate([{"record_id": "a"}, {"record_id": "b"}], {}, None, max_pairs=0)
    assert result[0]["relationship"] == "unclear"
    assert "budget" in result[0]["reason"]

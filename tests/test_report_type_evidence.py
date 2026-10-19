from scripts.report_type_evidence import evidence_errors


def test_secondary_role_requires_all_exact_features_and_identity():
    text = "Target title. Practice Point. Synopsis by editor. Original trial citation."
    proposal = dict(
        classification="secondary_synopsis",
        identity_quote="Target title",
        report_type_quote="Practice Point",
        editorial_role_quote="Synopsis by editor",
        primary_report_link_quote="Original trial citation",
    )
    assert evidence_errors(proposal, text, "Target title") == []
    proposal["editorial_role_quote"] = "Guessed editor"
    assert evidence_errors(proposal, text, "Target title")
    proposal["editorial_role_quote"] = ""
    assert evidence_errors(proposal, text, "Target title")
    proposal["editorial_role_quote"] = "Synopsis by editor"
    assert evidence_errors(proposal, text, "Another article")


def test_uncertainty_is_not_forced_into_secondary_classification():
    assert evidence_errors({"classification": "unclear"}, "Letter", "Title") == []


def test_publisher_identity_and_failure_checks():
    import hashlib

    import pytest

    from scripts.report_type_evidence import publisher_text

    body = b'<meta name="citation_doi" content="10.1/test"><meta name="citation_title" content="Title"><p>Letter</p>'
    h = hashlib.sha256(body).hexdigest()
    receipt = dict(
        status=200,
        content_type="text/html",
        final_url="https://publisher/article",
        sha256=h,
    )
    manifest = dict(
        url=receipt["final_url"], body_sha256=h, doi="10.1/test", title="Title"
    )
    assert publisher_text(body, receipt, manifest) == "Letter"
    for change in ({"doi": "10.1/other"}, {"title": "Other"}, {"body_sha256": "wrong"}):
        with pytest.raises(ValueError):
            publisher_text(body, receipt, manifest | change)
    with pytest.raises(ValueError):
        publisher_text(body, receipt | {"status": 403}, manifest)
    title_only = b'<meta name="citation_title" content="Title">'
    h2 = hashlib.sha256(title_only).hexdigest()
    with pytest.raises(ValueError):
        publisher_text(
            title_only, receipt | {"sha256": h2}, manifest | {"body_sha256": h2}
        )


def test_narrow_policy_cannot_certify_original_report_from_a_label():
    assert evidence_errors({"classification": "original_report"}, "Letter", "Title")


def test_reject_unsupported_policy_and_missing_model_before_calls(tmp_path):
    import json

    import pytest

    from scripts.report_type_evidence import assess

    manifest = tmp_path / "manifest.json"
    for data in (
        {"policy": "wrong", "model": "explicit"},
        {"policy": "publisher_report_role_v1", "model": ""},
    ):
        manifest.write_text(json.dumps(data))
        with pytest.raises(ValueError):
            assess(manifest, tmp_path / "output")
    assert not (tmp_path / "output").exists()

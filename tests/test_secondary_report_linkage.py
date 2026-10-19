import pytest

from scripts.secondary_report_linkage import validate_link


def test_link_requires_explicit_matching_original_title():
    primary = {"title": "A randomized trial of an intervention in an original cohort"}
    proposal = {
        "classification": "secondary_synopsis",
        "primary_report_link_quote": "Author et al. A randomized trial of an intervention in an original cohort.",
    }
    validate_link({"proposal": proposal}, primary)
    with pytest.raises(ValueError):
        validate_link(
            {"proposal": proposal},
            {"title": "A different original randomized trial in another cohort"},
        )
    with pytest.raises(ValueError):
        validate_link({"proposal": proposal | {"classification": "unclear"}}, primary)

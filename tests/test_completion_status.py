import pytest

from scripts.autonomous_review import unresolved_extraction


@pytest.mark.parametrize('rows,unresolved', [
    ([], True),
    ([{}], True),
    ([{'validation_errors': ['Unverified denominator']}], True),
    ([{'validation_errors': []}], False),
    ([{'validation_errors': []}, {}], True),
])
def test_required_inputs_must_be_validated_despite_contextual_missing_notes(rows, unresolved):
    item = {'status': 'extracted', 'result': {'eligibility': 'include', 'rows': rows, 'missing': ['Reported mean/SD absent; quartiles extracted under prespecified method.']}}
    assert unresolved_extraction(item) is unresolved
    item['status'] = 'publication_integrity_unresolved'
    assert unresolved_extraction(item)

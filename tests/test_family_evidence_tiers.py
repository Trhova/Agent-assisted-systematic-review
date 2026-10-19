import pytest
from scripts.family_evidence_tiers import decide, adjudicate


def proposal(reuse='theoretical_only'):
    return {'study_identity': 'distinct_randomizations', 'participant_reuse': reuse,
            'features': [{'domain': 'randomization', 'evidence_a': 'Trial A randomized 100', 'evidence_b': 'Trial B randomized 200'},
                         {'domain': 'population', 'evidence_a': 'first episode', 'evidence_b': 'first recurrence'}],
            'reason': 'Separate randomized cohorts; same sites', 'limitations': ['No participant identifiers']}

SOURCES = ('Trial A randomized 100 first episode', 'Trial B randomized 200 first recurrence')


def test_supported_distinct_trials_retain_theoretical_reenrollment():
    r = decide(proposal(), SOURCES, {'valid': True})
    assert r['relationship'] == 'distinct_trials'
    assert r['residual_limitations'] and r['independently_verified']


@pytest.mark.parametrize('reuse', ['documented', 'conflicting_evidence'])
def test_positive_reuse_blocks_despite_distinct_randomization(reuse):
    assert decide(proposal(reuse), SOURCES, {'valid': True})['relationship'] == 'unclear'


def test_registration_alone_and_unmatched_or_rejected_evidence_cannot_pass():
    p = proposal(); p['features'][1]['domain'] = 'registration'
    assert decide(p, SOURCES, {'valid': True})['relationship'] == 'unclear'
    assert decide(proposal(), ('wrong', SOURCES[1]), {'valid': True})['relationship'] == 'unclear'
    assert decide(proposal(), SOURCES, {'valid': False})['relationship'] == 'unclear'


def test_companion_and_unresolved_study_identity_stay_separate_from_reuse():
    p = proposal('not_indicated'); p['study_identity'] = 'same_study'
    assert decide(p, SOURCES, {'valid': True})['relationship'] == 'same_trial'
    p['study_identity'] = 'unresolved'
    assert decide(p, SOURCES, {'valid': True})['relationship'] == 'unclear'


def test_missing_sources_no_call_or_silent_distinctness():
    r = adjudicate([{'record_id': 'a'}, {'record_id': 'b'}], {}, None)
    assert r[0]['relationship'] == 'unclear'


def test_new_policy_cannot_override_shared_registry_conflict():
    from scripts.trial_families import resolve
    rows = [{'record_id': 'a', 'study_id': 'NCT00000001'},
            {'record_id': 'b', 'study_id': 'NCT00000001'}]
    link = decide(proposal(), SOURCES, {'valid': True})
    link.update(report_a='a', report_b='b')
    result = resolve(rows, [link])
    assert result['rows'] == []
    assert any('conflicts' in u['reason'] for u in result['unresolved'])

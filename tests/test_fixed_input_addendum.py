import copy

import pytest

from scripts.fixed_input_addendum import complete_set


def row(rid,registry):
    return {'record_id':rid,'study_id':registry}


def link(a,b,relationship='distinct_trials'):
    return {'report_a':a,'report_b':b,'relationship':relationship,'independently_verified':True,
            'evidence_a':'original A','evidence_b':'original B'}


def test_complete_new_set_preserves_baseline_and_does_not_duplicate():
    base=[row('a','NCT00000001'),row('b','NCT00000002')];prior=copy.deepcopy(base)
    result=complete_set(base,row('c','NCT00000003'),[link('a','b')],[link('a','c'),link('b','c')])
    assert result['supported'] and len(result['rows'])==3 and base==prior


@pytest.mark.parametrize('links',[[link('a','c')],[link('a','c'),link('a','c')],
                                  [link('a','c'),link('b','d')]])
def test_missing_duplicate_or_wrong_pair_rejected(links):
    with pytest.raises(ValueError):
        complete_set([row('a','NCT00000001'),row('b','NCT00000002')],row('c','NCT00000003'),[link('a','b')],links)


@pytest.mark.parametrize('relationship',['unclear','same_trial'])
def test_no_partial_pool_after_one_new_dependency_failure(relationship):
    result=complete_set([row('a','NCT00000001'),row('b','NCT00000002')],row('c','NCT00000003'),
                        [link('a','b')],[link('a','c',relationship),link('b','c')])
    assert not result['supported'] and result['rows']==[]


def test_same_registry_cannot_be_overridden_by_distinct_model_claim():
    result=complete_set([row('a','NCT00000001')],row('c','NCT00000001'),[],[link('a','c')])
    assert not result['supported'] and result['rows']==[]


def test_repeated_candidate_report_rejected():
    with pytest.raises(ValueError):complete_set([row('a','NCT00000001')],row('a','NCT00000001'),[],[])

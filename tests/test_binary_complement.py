import copy

import pytest

from scripts.binary_complement import POLICY, derive


@pytest.fixture
def args():
    source='All 20 patients had recorded day14 status; 6 remained ill.'
    item={'opposite_events':6,'known_status_n':20,'complete_binary_partition':True,
          'opposite_event_definition':'ill','target_event_definition':'not ill',
          'population_and_timepoint':'observed atday14','evidence':[source]}
    return ({'n_treatment':20,'events_treatment':None,'event_components_treatment':[],
             'complement_treatment':item,'complement_control':None},source,{'binary_complement_policy':POLICY,'measure':'RR'},'hash')


def test_exact_preserved(args):
    original=copy.deepcopy(args[0]);result=derive(*args)
    assert result['events_treatment']==14 and args[0]==original
    assert result['complement_audit']['treatment']['original']['opposite_events']==6


@pytest.mark.parametrize('field,value',[('known_status_n',21),('opposite_events',21),('opposite_events',True),('complete_binary_partition',False),('evidence',[]),('evidence',['paraphrase']),('population_and_timepoint','')])
def test_unsupported_rejected(args,field,value):
    args[0]['complement_treatment'][field]=value
    with pytest.raises(ValueError): derive(*args)


def test_disagrees_with_proposal(args):
    args[0]['events_treatment']=15
    with pytest.raises(ValueError):derive(*args)


def test_requires_opt_in(args):
    args[2].clear()
    with pytest.raises(ValueError):derive(*args)

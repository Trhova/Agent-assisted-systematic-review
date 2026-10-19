import copy

import pytest

from scripts.repair_source_candidate import gate_errors, repair_evidence


def test_repair_preserves_scientific_fields_and_original():
    original={'n_treatment':20,'mean_treatment':132,'evidence':['wrong'],'nested':{'value':1}}
    before=copy.deepcopy(original)
    result=repair_evidence(original,{'evidence':['actual source']},'actual\nsource')
    assert original==before
    assert {k:v for k,v in result.items() if k!='evidence'}=={k:v for k,v in original.items() if k!='evidence'}


@pytest.mark.parametrize('proposal',[
    {'evidence':[]}, {'evidence':['absent']}, {'evidence':['actual','absent']},
    {'evidence':['actual'],'n_treatment':99}, {'evidence':['actual source']},
    {'evidence':[1]}, {'evidence':'actual'},
])
def test_invalid_or_joined_quotes_fail_closed(proposal):
    with pytest.raises(ValueError):
        repair_evidence({'evidence':['old']},proposal,'actual intervening source')


def setup():
    row={'evidence':['source'],'design':'parallel','outcome':'FBG','unit':'mg/dL',
         'value_type':'endpoint','n_treatment':20,'n_control':20,'mean_treatment':132,
         'mean_control':135,'sd_treatment':60,'sd_control':70,'timepoint_reported':'8 weeks'}
    protocol={'outcome':'FBG','unit':'mg/dL','value_type':'endpoint','measure':'SMD'}
    links=[{'report_a':'a','report_b':'b','relationship':'same_trial','independently_verified':True}]
    return [row,'source',protocol,{'valid':True,'problems':[]},[],{'status':'after_cutoff'},
            {'status':'on_or_before_cutoff'},links,[('a','b')]]


def test_supported_postcutoff_input_can_pass_without_pooling():
    assert gate_errors(*setup())==[]


@pytest.mark.parametrize('index,value',[
    (3,{'valid':False,'problems':[]}), (3,{'valid':True,'problems':['N unclear']}),
    (4,['Expression of concern']), (5,{'status':'on_or_before_cutoff'}),
    (6,{'status':'unresolved_publication_date'}), (7,[]),
    (7,[{'report_a':'a','report_b':'b','relationship':'distinct_trials','independently_verified':True}]),
    (7,[{'report_a':'a','report_b':'b','relationship':'same_trial','independently_verified':False}]),
])
def test_verifier_integrity_dates_and_family_are_independent_gates(index,value):
    args=setup();args[index]=value
    assert gate_errors(*args)

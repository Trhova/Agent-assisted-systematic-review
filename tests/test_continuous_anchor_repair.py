import copy
import json

import pytest

from scripts.repair_continuous_anchors import FIELDS, prior_candidate, repair


def test_only_quotes_change_and_original_is_preserved():
    row={**{k:['bad'] for k in FIELDS},'n_treatment':48,'sd_control':2.3,'limitations':['PP only']}
    before=copy.deepcopy(row)
    result=repair(row,{k:['exact\nsource'] for k in FIELDS},'exact source')
    assert row==before
    assert {k:v for k,v in result.items() if k not in FIELDS}=={k:v for k,v in row.items() if k not in FIELDS}


@pytest.mark.parametrize('bad',[[],['absent'],['exact','absent'],[1],[''],['exact joined'], 'exact'])
def test_bad_quotes_never_filtered_or_fuzzily_accepted(bad):
    p={k:['exact'] for k in FIELDS};p['denominator_evidence_control']=bad
    with pytest.raises(ValueError):repair({},p,'exact intervening joined')


def test_extra_statistical_change_rejected():
    with pytest.raises(ValueError):repair({}, {**{k:['exact'] for k in FIELDS},'n_treatment':49},'exact')


def inputs():
    protocol={'measure':'SMD','outcome':'FBG','id':'old','query':'old search'}
    scientific={k:v for k,v in protocol.items() if k not in ('id','query')}
    request={'prompt':'\nPROTOCOL:\n'+json.dumps(scientific)+'\nBIBLIOGRAPHIC METADATA:\n{"id":"record"}\nARTICLE:\nexact source'}
    parsed={'eligibility':'include','rows':[{k:['old'] for k in FIELDS}]}
    return request,parsed,'exact source',protocol,'record'


def test_prior_projection_binds_scientific_contract_not_run_label():
    args=inputs();assert prior_candidate(*args)==args[1]['rows'][0]
    args[3]['outcome']='HbA1c'
    with pytest.raises(ValueError):prior_candidate(*args)


@pytest.mark.parametrize('change',['source','missing','excluded','multirow','binary'])
def test_unbound_or_unsupported_prior_rejected(change):
    args=list(inputs())
    if change=='source':args[2]='different source'
    if change=='missing':args[1]['rows'][0].pop('denominator_evidence_control')
    if change=='excluded':args[1]['eligibility']='exclude'
    if change=='multirow':args[1]['rows']*=2
    if change=='binary':args[3]['measure']='RR'
    with pytest.raises(ValueError):prior_candidate(*args)


def test_wrong_record_identity_rejected():
    args=list(inputs());args[4]='other'
    with pytest.raises(ValueError):prior_candidate(*args)

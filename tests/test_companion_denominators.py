import copy

import pytest

from scripts.companion_denominators import assess


def anchor(s,q):return {'source_id':s,'quote':q,'locator':'Results'}


def example():
    return {'family':'same_trial','family_evidence':[anchor('a','Trial X'),anchor('b','Trial X')],
            'denominator_status':'supported','treatment':{'n':20,'basis':'analyzed_outcome','evidence':[anchor('b','20 treated analyzed')]},
            'control':{'n':18,'basis':'analyzed_outcome','evidence':[anchor('b','18 controls analyzed')]},
            'population_bridge':[anchor('a','All endpoint measurements included'),anchor('b','same complete cohort')],
            'discrepancies':[],'reason':'Common analysis set','limitations':[]}


SOURCES={'a':'Trial X All endpoint measurements included','b':'Trial X 20 treated analyzed 18 controls analyzed same complete cohort',
         'registry':'Target sample size 44'}
VERIFY={'valid':True,'family_supported':True,'denominator_supported':True,'problems':[],'reason':'Source supported'}


def test_explicit_analyzed_counts_can_be_supported_without_numeric_admission():
    r=assess(example(),VERIFY,SOURCES,'a','b')
    assert r['denominators_supported'] and not r['numerical_admission']


@pytest.mark.parametrize('change',['randomized','planned','null','registry','population','conflict','quote','verifier','family'])
def test_unsupported_transfer_fails_closed(change):
    p=example();v=copy.deepcopy(VERIFY)
    if change=='randomized':p['treatment']['basis']='randomized_only'
    if change=='planned':p['treatment']['basis']='planned_only'
    if change=='null':p['treatment']['n']=None
    if change=='registry':p['treatment']['evidence']=[anchor('registry','Target sample size 44')]
    if change=='population':p['population_bridge']=[]
    if change=='conflict':p['discrepancies']=[{'description':'Different analysis populations','material_for_denominator':True,'evidence':[anchor('a','Trial X')],'resolution_evidence':[]}]
    if change=='quote':p['family_evidence'][0]['quote']='“Trial X” (page 1)'
    if change=='verifier':v['denominator_supported']=False
    if change=='family':p['family']='unresolved'
    assert not assess(p,v,SOURCES,'a','b')['denominators_supported']


def test_source_checked_unresolved_is_not_a_numeric_acceptance():
    p=example();p['denominator_status']='unresolved';p['treatment']['n']=None;p['control']['n']=None
    v={**VERIFY,'denominator_supported':False}
    r=assess(p,v,SOURCES,'a','b')
    assert r['source_checked'] and r['family_supported'] and not r['denominators_supported']

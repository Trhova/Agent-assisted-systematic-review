import copy

import pytest

from scripts.family_quote_repair import apply_quotes, repair_link


def proposal():
    return {'study_identity':'distinct_randomizations','participant_reuse':'theoretical_only',
            'features':[{'domain':'randomization','evidence_a':'wrong','evidence_b':'wrong'},
                        {'domain':'intervention','evidence_a':'wrong','evidence_b':'wrong'}],
            'reason':'Separate protocols','limitations':['No participant-level identifiers']}


SOURCES=('A randomized 80 yogurt','B randomized 48 soy')
QUOTES={'features':[{'evidence_a':'A randomized 80','evidence_b':'B randomized 48'},
                    {'evidence_a':'yogurt','evidence_b':'soy'}]}


def seed():
    return {'report_a':'a','report_b':'b','relationship':'unclear','independently_verified':False,
            'source_features_valid':False,'verification':{'valid':True},'evidence_tier_assessment':proposal()}


def test_only_literal_fields_change_and_original_remains_intact():
    old=proposal();before=copy.deepcopy(old);new=apply_quotes(old,QUOTES,SOURCES)
    assert old==before
    for key in old:
        if key!='features':assert new[key]==old[key]
    assert [f['domain'] for f in new['features']]==[f['domain'] for f in old['features']]


@pytest.mark.parametrize('repair',[
    {'features':[]}, {'features':QUOTES['features'],'study_identity':'same_study'},
    {'features':[{'evidence_a':'A randomized 80 (page 1)','evidence_b':'B randomized 48'},QUOTES['features'][1]]},
    {'features':[{'evidence_a':'A randomized 80','evidence_b':'B randomized 48','domain':'baseline'},QUOTES['features'][1]]},
    {'features':[{'evidence_a':'','evidence_b':'B randomized 48'},QUOTES['features'][1]]},
])
def test_missing_annotated_or_semantically_expanded_repair_rejected(repair):
    with pytest.raises(ValueError):apply_quotes(proposal(),repair,SOURCES)


def test_exact_repair_requires_new_scientific_verification():
    values=iter([QUOTES,{'valid':False,'reason':'Different totals do not entail separate cohorts'}])
    r=repair_link(seed(),SOURCES,lambda *args:next(values))
    assert r['relationship']=='unclear' and not r['independently_verified']


def test_supported_repair_retains_theoretical_overlap_limitation():
    values=iter([QUOTES,{'valid':True,'reason':'Original sources establish separate cohorts'}])
    old=seed();r=repair_link(old,SOURCES,lambda *args:next(values))
    assert r['relationship']=='distinct_trials' and r['independently_verified']
    assert r['prior_quote_blocked_assessment']==old and r['residual_limitations']


def test_adverse_scientific_verdict_cannot_be_repaired_into_acceptance():
    old=seed();old['verification']['valid']=False
    assert repair_link(old,SOURCES,lambda *args:pytest.fail('No call authorized'))==old


def test_documented_reuse_stays_blocked_after_exact_quotes():
    old=seed();old['evidence_tier_assessment']['participant_reuse']='documented'
    values=iter([QUOTES,{'valid':True}]);r=repair_link(old,SOURCES,lambda *args:next(values))
    assert r['relationship']=='unclear'

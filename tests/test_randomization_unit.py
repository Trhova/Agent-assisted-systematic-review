import copy
import pytest
from scripts.randomization_unit import assess, acceptance_errors
from scripts.autonomous_review import validate_evidence, unresolved_extraction


def answers(unit, quote, valid=True):
    values=iter([dict(unit=unit,evidence=[quote],reason='Own methods',limitations=[]),dict(valid=valid,problems=[] if valid else ['Only cited study'])])
    return lambda prompt,schema: next(values)


def test_legacy_design_label_does_not_establish_allocation_unit():
    source='To prevent unblinding, randomization occurred by household 1:1:1.'
    row=dict(evidence=[source],design='parallel',outcome='admission',unit='dimensionless',value_type='binary_rr_mh_fixed_v1',events_treatment=2,n_treatment=71,events_control=4,n_control=83,timepoint_reported='28 days')
    protocol=dict(measure='RR',outcome='admission',unit='dimensionless',value_type='binary_rr_mh_fixed_v1')
    assert validate_evidence(row,source,protocol)==[]  # Preserved counterexample: label-only gate.
    protocol['randomization_unit_policy']='randomization_unit_v2'
    assert validate_evidence(row,source,protocol)
    assessment=assess(source,answers('household',source))
    assert assessment['source_checked'] and not assessment['independent_participant_compatible']
    row['randomization_unit']=assessment
    assert validate_evidence(row,source,protocol)
    assert unresolved_extraction({'status':assessment['status']})


def test_individual_allocation_with_cluster_background_is_not_keyword_rejected():
    source='Earlier cluster trials recruited schools. In our trial patients were individually randomized, stratified by site.'
    q='In our trial patients were individually randomized, stratified by site.'
    result=assess(source,answers('individual',q))
    assert acceptance_errors(result,source)==[]
    assert acceptance_errors(result,source+' changed')


def test_cited_cluster_and_missing_design_are_not_proof():
    source='Other investigators randomized households. Our methods are not reported.'
    result=assess(source,answers('household','Other investigators randomized households.',False))
    assert not result['source_checked']
    unknown=assess(source,answers('unclear','Our methods are not reported.'))
    assert unknown['status']=='allocation_unit_unresolved'


@pytest.mark.parametrize('quote',['','invented methods'])
def test_quotes_fail_closed_after_bounded_repair(quote):
    calls=[]
    def call(prompt,schema):
        calls.append(prompt)
        if list(schema['properties']) == ['evidence']:
            return {'evidence': []}
        return dict(unit='individual',evidence=[quote],reason='',limitations=[])
    result=assess('This source has no allocation description.',call)
    assert len(calls)==2 and not result['independent_participant_compatible']


def test_spoofed_compatible_flag_does_not_override_cluster():
    source='Households were randomized.'
    result=assess(source,answers('household',source)); result['independent_participant_compatible']=True
    assert acceptance_errors(result,source)
    forged=copy.deepcopy(result);forged['verification']=None
    assert acceptance_errors(forged,source)


@pytest.mark.parametrize("eligible", [True, False])
def test_runner_guard_preserves_eligibility_and_blocks_numeric_acceptance(tmp_path, monkeypatch, eligible):
    import json
    import yaml
    import scripts.autonomous_review as runner
    from scripts.model_backend import digest
    protocol={'id':'unit-gate','query':'fixture','eligibility':'parallel trials','outcome':'admission','unit':'dimensionless','value_type':'binary_rr_mh_fixed_v1','measure':'RR','model':'mantel_haenszel_fixed','binary_policy':'binary_rr_mh_fixed_v1','randomization_unit_policy':'randomization_unit_v2'}
    path=tmp_path/'protocol.yaml';path.write_text(yaml.safe_dump(protocol))
    source='In this trial households were randomized.'
    monkeypatch.setattr(runner,'search',lambda p,w:{'records':[{'id':'one','title':'Original trial','publication_types':[]}]})
    monkeypatch.setattr(runner,'fulltext',lambda *a,**k:{'text':source,'sha256':digest(source)})
    calls=[]
    def call(prompt,schema,*a,**k):
        calls.append(prompt)
        if 'records' in schema['properties']:
            return {'records':[{'id':'one','decision':'include','reason':'Full text needed'}]}
        if 'rows' in schema['properties']:
            return {'eligibility':'include' if eligible else 'exclude','reason':'Original design eligibility','missing':[], 'rows':[]}
        if 'unit' in schema['properties']:
            assert eligible
            return {'unit':'household','evidence':[source],'reason':'Own methods','limitations':[]}
        if 'valid' in schema['properties']:
            return {'valid':True,'problems':[]}
        raise AssertionError('Numeric extraction must never be called for this cluster source')
    monkeypatch.setattr(runner,'model_json',call)
    work,status=runner.run(path,tmp_path/'runs','codex','gpt-6-astra')
    assert status['counts']['accepted_effects']==0
    assert not (work/'synthesis.json').exists()
    extraction=json.loads((work/'extractions.json').read_text())[0]
    if eligible:
        assert json.loads((work/'randomization_unit/one.json').read_text())['source_checked']
        assert extraction['status']=='unsupported_allocation_unit'
        assert len(calls)==4
    else:
        assert extraction['result']['eligibility']=='exclude'
        assert not (work/'randomization_unit/one.json').exists()
        assert not unresolved_extraction(extraction)
        assert len(calls)==2


def test_quote_repair_preserves_claim_and_requires_independent_verification():
    source='Patients were individually randomized.'
    values=iter([dict(unit='individual',evidence=['“'+source+'”'],reason='Own methods',limitations=[]), {'evidence':[source]}, {'valid':True,'problems':[]}])
    result=assess(source,lambda p,s:next(values))
    assert acceptance_errors(result,source)==[]
    assert result['original_proposal']['evidence']!=result['proposal']['evidence']
    assert result['verification']['valid']

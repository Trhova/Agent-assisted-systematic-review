import json

import pytest
from scripts.evaluate_contract import claims, evaluate, sha


def comparison():
    return dict(numerically_matches=True,semantic_agreement={'agrees':True},missing_studies=[],extra_studies=[],k_observed=3,k_expected=3,reproduced=True)


@pytest.mark.parametrize('cells,trust,expected', [(None,'unverified',None),({'all_reported_cells_agree':True},'manual_transcription_unverified',None),({'all_reported_cells_agree':False},'manual_transcription_unverified',None),({'all_reported_cells_agree':False},'independently_verified',False),({'all_reported_cells_agree':True},'independently_verified',True)])
def test_input_trust_never_inferred_from_numerical_match(cells,trust,expected):
    r=claims(comparison(),cells,True,trust,'published_subgroup_development',True)
    assert r['verified_input_agreement'] is expected
    assert r['reproduced'] is (expected is True)
    assert r['complete_review_reproduction']=='not_established'
    assert r['prospective_validation']=='not_established'


@pytest.mark.parametrize('kind',['mapping','integrity','semantics','coverage'])
def test_positive_cells_cannot_override_other_gates(kind):
    c=comparison()
    if kind=='semantics':c['semantic_agreement']['agrees']=False
    if kind=='coverage':c['missing_studies']=['missing']
    r=claims(c,{'all_reported_cells_agree':True},kind!='mapping','independently_verified','whole_review_development',kind!='integrity')
    assert not r['reproduced']


def test_missing_comparison_fields_are_not_agreement():
    r=claims({},None,False,'unverified','whole_review_development',True)
    assert not r['report_coverage_agreement']
    assert not r['numerical_agreement']


def fixture_contract(tmp_path):
    r=tmp_path/'run';r.mkdir()
    row=dict(record_id='1',study_id='trial',timepoint_reported='28days',treatment='A',control='B')
    values={'status.json':{'status':'complete'},'protocol.json':{},'accepted.json':[row], 'benchmark_comparison.json':comparison(), 'trial_families.json':{},'family_links.json':{},'synthesis.json':{}}
    for n,v in values.items():(r/n).write_text(json.dumps(v))
    c={'policy':'evaluator_input_contract_v2','scope':'published_subgroup_development','run_sha256':{n:sha(r/n) for n in values},'mapping':[{**row,'reference_trial_id':'T1','reference_locator':'forest row1'}]}
    p=tmp_path/'contract.json';p.write_text(json.dumps(c));return r,p,c


def test_ambiguous_families_fail_closed(tmp_path):
    r,p,c=fixture_contract(tmp_path);c['mapping']*=2;p.write_text(json.dumps(c))
    with pytest.raises(ValueError,match='Ambiguous'):evaluate(r,p)


def test_mutated_source_fails_before_evaluation(tmp_path):
    r,p,c=fixture_contract(tmp_path);(r/'accepted.json').write_text('[]')
    with pytest.raises(ValueError,match='checksum'):evaluate(r,p)


def test_missing_pin_fails(tmp_path):
    r,p,c=fixture_contract(tmp_path);del c['run_sha256']['accepted.json'];p.write_text(json.dumps(c))
    with pytest.raises(ValueError,match='pins'):evaluate(r,p)


def test_suite_opt_in_checks_contract_hash(tmp_path):
    from scripts.benchmark_suite import evaluate as suite_evaluate
    r,p,c=fixture_contract(tmp_path)
    with pytest.raises(ValueError,match='contract checksum'):
        suite_evaluate({'evaluation_contract':str(p),'evaluation_contract_sha256':'bad'},r)


@pytest.mark.parametrize('field',['study_id','timepoint_reported','treatment','control','reference_locator'])
def test_incomplete_or_misaligned_mapping_is_not_verified(tmp_path,monkeypatch,field):
    import scripts.evaluate_contract as module
    r,p,c=fixture_contract(tmp_path);c['mapping'][0][field]='';p.write_text(json.dumps(c))
    monkeypatch.setattr(module,'artifact_audit',lambda r:{'valid':True})
    result=evaluate(r,p)
    assert result['trial_arm_time_mapping']=='unresolved'
    assert result['verified_contributor_agreement'] is None
    assert not result['reproduced']


def test_absent_reference_cells_stay_not_assessed(tmp_path,monkeypatch):
    import scripts.evaluate_contract as module
    r,p,c=fixture_contract(tmp_path)
    monkeypatch.setattr(module,'artifact_audit',lambda r:{'valid':True})
    result=evaluate(r,p)
    assert result['input_observation']=='not_assessed'
    assert result['verified_input_agreement'] is None


@pytest.mark.parametrize('receipt_valid,mapping_matches', [(True, True), (False, True), (True, False)])
def test_text_receipt_requires_replay_and_exact_mapping(tmp_path, monkeypatch, receipt_valid, mapping_matches):
    import hashlib
    import scripts.evaluate_contract as module
    import scripts.validate_reference_receipt as validator
    r, p, c = fixture_contract(tmp_path)
    ref = tmp_path / 'cells.json';ref.write_text('{}')
    manifest = tmp_path / 'manifest.json';manifest.write_text('{}')
    receipt = tmp_path / 'receipt.json'
    receipt.write_text(json.dumps({'policy':'reference_original_text_verification_v1',
        'reference_sha256':sha(ref),
        'mapping_canonical_sha256':hashlib.sha256(json.dumps(c['mapping'],sort_keys=True).encode()).hexdigest() if mapping_matches else 'wrong'}))
    c.update(cell_reference={'path':str(ref),'sha256':sha(ref)},
             independent_verification={'path':str(receipt),'sha256':sha(receipt)},
             model_verification_manifest={'path':str(manifest),'sha256':sha(manifest)})
    p.write_text(json.dumps(c))
    monkeypatch.setattr(module,'artifact_audit',lambda r:{'valid':True})
    monkeypatch.setattr(module,'cell_audit',lambda *a:{'all_reported_cells_agree':False})
    monkeypatch.setattr(validator,'validate_receipt',lambda *a:{'valid':receipt_valid})
    result=evaluate(r,p)
    verified = receipt_valid and mapping_matches
    assert result['reference_evidence_trust'] == ('independently_verified' if verified else 'manual_transcription_unverified')
    assert result['verified_input_agreement'] is (False if verified else None)
    assert not result['reproduced']  # Matching pooled target never overrides discrepant primary cells.

import pytest
from scripts.benchmark_input_audit import reconcile


def row(rid='one', n=242):
    return dict(record_id=rid,events_treatment=25,n_treatment=n,events_control=25,n_control=237)


def test_denominator_discrepancy_survives_rounded_pool_similarity():
    result=reconcile([row(n=241)],[row()])
    assert not result['all_reported_cells_agree']
    assert result['differences']==[dict(record_id='one',field='n_treatment',observed_primary_input=241,published_input=242)]


def test_coverage_and_ambiguous_arm_mapping_are_not_ignored():
    result=reconcile([row()],[row(),row('two')]);assert result['missing_from_run']==['two']
    assert not result['all_reported_cells_agree']
    with pytest.raises(ValueError,match='Ambiguous'):
        reconcile([row(),row()],[row()])


def test_exact_match_and_invalid_inputs():
    assert reconcile([row()],[row()])['all_reported_cells_agree']
    assert not reconcile([],[])['all_reported_cells_agree']
    bad=row();bad['events_control']=300
    with pytest.raises(ValueError):reconcile([bad],[row()])


def test_audit_requires_finished_semantically_matching_evidenced_inputs(tmp_path):
    import json
    import hashlib
    from scripts.benchmark_input_audit import audit
    run=tmp_path/'run';run.mkdir()
    protocol=dict(outcome='mortality',unit='dimensionless',value_type='binary_rr_mh_fixed_v1',measure='RR',model='mantel_haenszel_fixed')
    evidence=tmp_path/'forest.txt';evidence.write_text('preserved published evidence')
    ref={**protocol,'policy':'published_binary_input_audit_v1','rows':[row()], 'published_evidence':{'path':str(evidence),'sha256':hashlib.sha256(evidence.read_bytes()).hexdigest()}}
    rp=tmp_path/'reference.json';rp.write_text(json.dumps(ref))
    (run/'protocol.json').write_text(json.dumps(protocol));(run/'accepted.json').write_text(json.dumps([row()]))
    (run/'status.json').write_text(json.dumps({'status':'running'}))
    with pytest.raises(ValueError,match='finished'):audit(run,rp)
    (run/'status.json').write_text(json.dumps({'status':'complete'}))
    assert audit(run,rp)['source_run_unchanged']
    ref['outcome']='other';rp.write_text(json.dumps(ref))
    with pytest.raises(ValueError,match='semantic'):audit(run,rp)
    ref['outcome']='mortality';rp.write_text(json.dumps(ref));evidence.write_text('changed')
    with pytest.raises(ValueError,match='checksum'):audit(run,rp)

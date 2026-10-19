import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from test_docx_source_upgrade import prepare
from scripts.upgrade_supplement_source import upgrade
from scripts.primary_image_queue import build,sha
from scripts.inspect_primary_image import run


def test_queue_checks_images_and_raw_context(tmp_path):
    manifest,_=prepare(tmp_path);folder=tmp_path/'source2';upgrade(manifest,folder);doc=json.loads((folder/'text.json').read_text());q=build(folder,doc)
    assert len(q['items'])==1 and q['items'][0]['numerical_admission'] is False
    assert q['items'][0]['context_interpretation'].startswith('Adjacent text only')
    (folder/q['items'][0]['image_relative_path']).write_bytes(b'changed')
    with pytest.raises(ValueError,match='image checksum'):build(folder,doc)


@pytest.mark.parametrize('relevance,legible,expected',[('relevant',True,'source_checked_visual_observation'),('irrelevant',True,'checked_irrelevant'),('unclear',True,'checked_relevance_unclear'),('relevant',False,'checked_unreadable')])
def test_inspection_is_durable_and_never_statistical_admission(tmp_path,monkeypatch,relevance,legible,expected):
    manifest,_=prepare(tmp_path);folder=tmp_path/'source2';upgrade(manifest,folder);doc=json.loads((folder/'text.json').read_text());q=build(folder,doc)
    proposal={'legible':legible,'relevance':relevance,'content_type':'graph','visible_labels':['axis'],'visual_observations':['Plot visible'],'explicit_analyzed_n_present':True,'explicit_mean_and_sd_present':True,'limitations':[]}
    calls=[]
    def fake(cmd,**kwargs):
        calls.append(cmd);schema=json.loads(Path(cmd[cmd.index('--output-schema')+1]).read_text());value=proposal if 'legible' in schema['properties'] else {'valid':True,'problems':[],'limitations':[]};payload=json.dumps(value);Path(cmd[cmd.index('-o')+1]).write_text(payload)
        return SimpleNamespace(returncode=0,stdout=json.dumps({'type':'item.completed','item':{'type':'agent_message','text':payload}}),stderr='')
    monkeypatch.setattr('scripts.model_backend.subprocess.run',fake)
    m={'policy':'primary_image_inspection_v1','model':'gpt-6-astra','source_folder':str(folder),'selected_id':q['items'][0]['id'],'question':'Read the original plot','files_sha256':{str(p):sha(p) for p in folder.rglob('*') if p.is_file()}}
    mp=tmp_path/'inspection.json';mp.write_text(json.dumps(m));out=tmp_path/'out';result=run(mp,out)
    assert len(calls)==2 and result['status']==expected and result['numerical_admission'] is False
    successor=out/'source_successor';after=json.loads((successor/'text.json').read_text());rebuilt=build(successor,after)
    assert rebuilt['items'][0]['status']==expected
    assert after['text']==doc['text'] and after['sha256']==doc['sha256']
    m['source_folder']=str(successor);m['files_sha256']={str(p):sha(p) for p in successor.rglob('*') if p.is_file()};mp.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='Selection'):run(mp,tmp_path/'never_retry')
    assert len(calls)==2


def test_outcome_consumer_exposes_primary_images_without_numeric_gate_change(tmp_path):
    from scripts.outcome_availability import build as availability
    manifest,_=prepare(tmp_path);folder=tmp_path/'source2';upgrade(manifest,folder)
    import shutil
    run=tmp_path/'review';(run/'sources').mkdir(parents=True);shutil.copytree(folder,run/'sources/1')
    (run/'status.json').write_text(json.dumps({'status':'incomplete'}));(run/'extractions.json').write_text(json.dumps([{'id':'1','status':'extracted','result':{'eligibility':'include','rows':[],'missing':['Image-only data need inspection']}}]))
    report=availability(run)
    assert report['primary_image_inspection_queue'][0]['automatic_numeric_admission'] is False
    assert report['primary_image_inspection_queue'][0]['queue']['items'][0]['status']=='pending_source_inspection'
    assert report['synthesis_unchanged'] is None

import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts.verify_reference_source import adjudicate
from scripts.model_backend import model_json
from scripts.import_model_cache import verify_entry


def sample():
    row=dict(label='Trial',events_treatment=1,n_treatment=10,events_control=2,n_control=10,locator='row Trial')
    blind=dict(image_legible=True,rows=[row])
    check=dict(cells_match_source=True,mapping_supported=True,problems=[],row_checks=[dict(record_id='1',image_label='Trial',source_locator='figure1',mapping_evidence='original methods',cells_match=True,mapping_supported=True)])
    ref={'rows':[dict(record_id='1',**{k:v for k,v in row.items() if k not in ['label','locator']})]}
    return blind,check,ref,[{'record_id':'1'}]


def test_altered_reference_cell_rejected_despite_positive_verifier():
    b,c,r,m=sample();assert adjudicate(b,c,r,m)['valid']
    r['rows'][0]['n_treatment']=11
    assert not adjudicate(b,c,r,m)['valid'] # pooled target is deliberately irrelevant


@pytest.mark.parametrize('fault',['illegible','duplicate','missing','mapping','null'])
def test_ambiguity_never_passes(fault):
    b,c,r,m=sample()
    if fault=='illegible':b['image_legible']=False
    if fault=='duplicate':c['row_checks']*=2
    if fault=='missing':c['row_checks']=[]
    if fault=='mapping':c['row_checks'][0]['mapping_supported']=False
    if fault=='null':b['rows'][0]['n_control']=None
    assert not adjudicate(b,c,r,m)['valid']


def test_image_bytes_bound_to_request_and_actual_cli(tmp_path,monkeypatch):
    from PIL import Image
    image=tmp_path/'source.png';Image.new('RGB',(20,20),'white').save(image)
    schema={'type':'object','properties':{'ok':{'type':'boolean'}},'required':['ok'],'additionalProperties':False}
    def fake(cmd,**kwargs):
        assert '--image' in cmd
        attached=Path(cmd[cmd.index('--image')+1]);assert attached.read_bytes()==image.read_bytes()
        Path(cmd[cmd.index('-o')+1]).write_text('{"ok":true}')
        return SimpleNamespace(returncode=0,stdout=json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'{"ok":true}'}}),stderr='')
    monkeypatch.setattr('scripts.model_backend.subprocess.run',fake)
    assert model_json('source only',schema,tmp_path/'calls',model='gpt-6-astra',images=[image],max_attempts=1)=={'ok':True}
    folder=next((tmp_path/'calls').iterdir());verify_entry(folder,model='gpt-6-astra',backend='codex')
    submission=next(folder.glob('*.submission.json'));saved=submission.read_bytes();submission.unlink()
    with pytest.raises(ValueError,match='matching successful'):verify_entry(folder,model='gpt-6-astra',backend='codex')
    submission.write_bytes(saved)
    (folder/'input-0.png').write_bytes(b'altered')
    with pytest.raises(ValueError,match='Image request'):verify_entry(folder,model='gpt-6-astra',backend='codex')


def test_full_receipt_replay_detects_forged_decision(tmp_path,monkeypatch):
    from PIL import Image
    from scripts.verify_reference_source import run
    from scripts.validate_reference_receipt import validate_receipt
    from scripts.evaluate_contract import sha
    b,c,r,mapping=sample();b.update(treatment_header='A',control_header='B',limitations=[]);c['limitations']=[]
    image=tmp_path/'image.png';Image.new('RGB',(20,20),'white').save(image)
    context=tmp_path/'source.txt';context.write_text('original methods')
    reference=tmp_path/'reference.json';reference.write_text(json.dumps(r))
    contract=tmp_path/'contract.json';contract.write_text(json.dumps({'mapping':mapping}))
    def fake(cmd,**kwargs):
        schema=json.loads(Path(cmd[cmd.index('--output-schema')+1]).read_text());value=b if 'image_legible' in schema['properties'] else c
        if value is b:assert 'PROPOSED PUBLISHED CELLS' not in kwargs['input']
        payload=json.dumps(value);Path(cmd[cmd.index('-o')+1]).write_text(payload)
        return SimpleNamespace(returncode=0,stdout=json.dumps({'type':'item.completed','item':{'type':'agent_message','text':payload}}),stderr='')
    monkeypatch.setattr('scripts.model_backend.subprocess.run',fake)
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps({'policy':'reference_source_verification_v1','model':'gpt-6-astra','image':str(image),'image_locator':'figure','review_text':str(context),'primary_context':[],'reference':str(reference),'contract':str(contract),'files_sha256':{str(p):sha(p) for p in [image,context,reference,contract]}}))
    out=tmp_path/'output';run(manifest,out)
    assert validate_receipt(out/'receipt.json',manifest)['valid']
    receipt=json.loads((out/'receipt.json').read_text());receipt['valid']=False;(out/'receipt.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match='decision replay'):validate_receipt(out/'receipt.json',manifest)
    with pytest.raises(ValueError,match='new isolated'):run(manifest,out)


@pytest.mark.parametrize('axis',['cells','trial_identity','arms','timepoint','population','source_locator','outcome'])
@pytest.mark.parametrize('state',['unsupported','unclear'])
def test_typed_semantic_failure_blocks_despite_matching_cells(axis,state):
    from scripts.verify_reference_source import adjudicate_v2,AXES
    b,c,r,m=sample();row=c['row_checks'][0];row['assessments']={a:'supported' for a in AXES};row['assessments'][axis]=state
    typed={'row_checks':[row],'blocking_problems':[],'observations':[{'kind':'scope_note','record_id':'1','description':'Does not override a failed axis'}]}
    assert not adjudicate_v2(b,typed,r,m)['valid']


def test_primary_value_difference_does_not_change_published_transcription():
    from scripts.verify_reference_source import adjudicate_v2,AXES
    b,c,r,m=sample();row=c['row_checks'][0];row['assessments']={a:'supported' for a in AXES}
    typed={'row_checks':[row],'blocking_problems':[],'observations':[{'kind':'primary_value_difference','record_id':'1','description':'Primary denominator differs'}]}
    assert adjudicate_v2(b,typed,r,m)['valid']
    r['rows'][0]['n_treatment']=11
    assert not adjudicate_v2(b,typed,r,m)['valid']


def test_docx_context_preserves_run_text_order_image_caption_and_table(tmp_path):
    import zipfile,hashlib
    from scripts.docx_evidence import extract
    p=tmp_path/'source.docx';raw=b'original image'
    xml='''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body><w:p><a:blip r:embed="rId1"/></w:p><w:p><w:r><w:t>Fig. S</w:t></w:r><w:r><w:t>15. Caption</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Table cell</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'''
    with zipfile.ZipFile(p,'w') as z:
        z.writestr('word/document.xml',xml);z.writestr('word/_rels/document.xml.rels','<Relationships><Relationship Id="rId1" Target="media/image.png"/></Relationships>');z.writestr('word/media/image.png',raw)
    d=extract(p)['blocks'];assert d[0]['images'][0]['sha256']==hashlib.sha256(raw).hexdigest();assert d[1]['text']=='Fig. S15. Caption';assert d[2]['text']=='Table cell';assert d[1]['locator'].endswith('2')

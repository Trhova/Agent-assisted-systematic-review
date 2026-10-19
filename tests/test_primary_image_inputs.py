import pytest

from scripts.autonomous_review import validate_evidence
from scripts.primary_image_inputs import AXES, POLICY, adjudicate, validate_row


def fixture():
    p={'legible': True,'events_treatment': 2,'n_treatment': 15,'events_control': 3,'n_control': 14,'treatment_label': 'Drug','control_label': 'Placebo','outcome_label': 'Death','timepoint_label': '28 d','pixel_locator': 'Table 2 row death','denominator_locator': 'Death heading','design_quote': 'Participants were randomly assigned.','limitations': []}
    c={'assessments': {k:'supported' for k in AXES},'blocking_problems': [],'limitations': []}
    return p,c,{'segments':[{'text':'Participants were randomly assigned.','locator':'page 2'}]}


def test_explicit_inputs():
    assert adjudicate(*fixture()) == []


@pytest.mark.parametrize('axis',AXES)
def test_semantics_block_despite_valid_counts(axis):
    p,c,s=fixture();c['assessments'][axis]='unclear'
    assert adjudicate(p,c,s)


@pytest.mark.parametrize('value',[None,False,2.5,-1,16])
def test_bad_counts(value):
    p,c,s=fixture();p['events_treatment']=value
    assert adjudicate(p,c,s)


def test_quote_not_pixel_fabrication():
    p,c,s=fixture();p['design_quote']='Imagined individual allocation'
    assert adjudicate(p,c,s)


def test_receipt_pointer_fails_closed(tmp_path):
    assert validate_row({'image_admission':{'manifest':str(tmp_path/'missing')}},'source',{})


def test_normal_consumer_requires_optin():
    row={'image_admission': {'manifest':'missing'},'evidence': ['source'],'design': 'parallel','outcome': 'mortality','unit': 'participants','value_type': 'binary_rr_mh_fixed_v1','n_treatment': 15,'n_control': 14,'events_treatment': 2,'events_control': 3,'timepoint_reported': '28 d'}
    p={'measure': 'RR','outcome': 'mortality','unit': 'participants'}
    assert any('separately specified' in x for x in validate_evidence(row,'source',p))
    p['image_input_policy']=POLICY
    assert any('Image evidence invalid' in x for x in validate_evidence(row,'source',p))


def source_fixture(tmp_path):
    import json

    import pypdfium2 as pdfium
    from pypdf import PdfWriter

    from scripts.model_backend import atomic_json, digest
    from scripts.primary_image_queue import sha
    pdf=tmp_path/'original.pdf'; writer=PdfWriter();writer.add_blank_page(width=200,height=200)
    with pdf.open('wb') as h: writer.write(h)
    image=tmp_path/'page.png';d=pdfium.PdfDocument(pdf);d[0].render(scale=2).to_pil().save(image);d.close()
    atomic_json(tmp_path/'acquisition.json',{'status':200,'sha256':sha(pdf)})
    atomic_json(tmp_path/'text.json',{'text':'Participants were randomly assigned.','sha256':digest('Participants were randomly assigned.'),'pdf_sha256':sha(pdf),'identity':{'verified':True},'import_provenance':{'record':{'id':'123'},'receipt_relative_path':'acquisition.json','receipt_sha256':sha(tmp_path/'acquisition.json')}})
    atomic_json(tmp_path/'context.json',{'segments':[{'locator':'page 1','text':'Participants were randomly assigned.'}]})
    atomic_json(tmp_path/'protocol.json',{'image_input_policy':POLICY,'measure':'RR'})
    atomic_json(tmp_path/'render.json',{'page':1,'scale':2,'crop':'full_page','pdf_sha256':sha(pdf),'image_sha256':sha(image)})
    m={'policy':POLICY,'model':'explicit-model','backend':'codex','record_id':'123','page':1,
       **{k:str(tmp_path/v) for k,v in {'source':'text.json','pdf':'original.pdf','image':'page.png','context':'context.json','protocol':'protocol.json','render_receipt':'render.json'}.items()}}
    m['files_sha256']={str(p):sha(p) for p in tmp_path.iterdir()}
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(m));return manifest,m


def test_manifest_exact_source_pixels(tmp_path):
    from scripts.primary_image_inputs import load_manifest
    m,_=source_fixture(tmp_path)
    assert load_manifest(m)[0]['record_id']=='123'


@pytest.mark.parametrize('kind',['image','context','identity','missing_pin'])
def test_forged_evidence_even_when_rehashed(tmp_path,kind):
    import json

    from scripts.primary_image_inputs import load_manifest
    from scripts.primary_image_queue import sha
    manifest,m=source_fixture(tmp_path)
    if kind=='identity':m['record_id']='456'
    elif kind=='missing_pin':del m['files_sha256'][m['image']]
    elif kind=='context':
        p=tmp_path/'context.json';p.write_text(json.dumps({'segments':[{'locator':'page 1','text':'Invented randomization'}]}));m['files_sha256'][str(p)]=sha(p)
    else:
        from PIL import Image
        p=tmp_path/'page.png';Image.new('RGB',(400,400),'red').save(p)
        render=tmp_path/'render.json';r=json.loads(render.read_text());r['image_sha256']=sha(p);render.write_text(json.dumps(r))
        m['files_sha256'][str(p)]=sha(p);m['files_sha256'][str(render)]=sha(render)
    manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError):load_manifest(manifest)


@pytest.mark.parametrize('mutation',['count','timepoint','source','contract','pointer'])
def test_consumer_rejects_transplanted_or_changed_admission(monkeypatch,mutation):
    from scripts.model_backend import digest
    from scripts.primary_image_inputs import validate_row
    row={'events_treatment':2,'timepoint_reported':'28d'};protocol={'image_input_policy':POLICY};source='primary'
    result={'admitted':True,'manifest_sha256':'pin','source_text_sha256':digest(source),'protocol_sha256':digest(protocol),'row':dict(row)}
    monkeypatch.setattr('scripts.primary_image_inputs.replay',lambda *a:result)
    row['image_admission']={'manifest':'m','output':'o','manifest_sha256':'pin'}
    assert validate_row(row,source,protocol)==[]
    if mutation=='count':row['events_treatment']=3
    elif mutation=='timepoint':row['timepoint_reported']='14d'
    elif mutation=='source':source='different primary'
    elif mutation=='contract':protocol['timepoint']='14d'
    else:row['image_admission']['manifest_sha256']='changed'
    assert validate_row(row,source,protocol)


def test_reordered_context_requires_exact_original_projection(tmp_path):
    import json

    import pypdf

    from scripts.primary_image_inputs import load_manifest
    from scripts.primary_image_queue import sha
    manifest,m=source_fixture(tmp_path)
    context=tmp_path/'context.json'
    data={'parser':'pypdf_content_stream_v1','parser_version':pypdf.__version__,'pdf_sha256':sha(m['pdf']),'segments':[{'page':1,'locator':'Original report PDF page 1','text':pypdf.PdfReader(m['pdf']).pages[0].extract_text()}]}
    context.write_text(json.dumps(data));m['files_sha256'][str(context)]=sha(context);manifest.write_text(json.dumps(m))
    load_manifest(manifest)
    data['segments'][0]['text']='Invented text';context.write_text(json.dumps(data));m['files_sha256'][str(context)]=sha(context);manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='content stream'):load_manifest(manifest)

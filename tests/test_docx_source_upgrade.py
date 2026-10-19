import io
import json
import zipfile
import pytest
from scripts.docx_evidence import extract
from scripts.model_backend import digest
from scripts.upgrade_supplement_source import upgrade,sha


def docx(target='media/a.png',external=False):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        z.writestr('word/document.xml','''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body><w:p><w:r><w:t>Original paragraph</w:t></w:r></w:p><w:p><a:blip r:embed="rId1"/></w:p><w:p><w:r><w:t>Nearby text, not necessarily a caption</w:t></w:r></w:p></w:body></w:document>''')
        mode=' TargetMode="External"' if external else ''
        z.writestr('word/_rels/document.xml.rels',f'<Relationships><Relationship Id="rId1" Target="{target}"{mode}/></Relationships>')
        from PIL import Image
        pixels=io.BytesIO();Image.new('RGB',(20,20),'white').save(pixels,format='PNG')
        z.writestr('word/media/a.png',pixels.getvalue())
    return out.getvalue()


@pytest.mark.parametrize('target',['../outside.png','/etc/passwd','http://example.org/a','media\\a.png'])
def test_relationship_paths_fail_closed(tmp_path,target):
    p=tmp_path/'a.docx';p.write_bytes(docx(target))
    with pytest.raises(ValueError,match='Unsafe'):extract(p,tmp_path/'assets')


def test_external_image_not_fetched_or_assigned_caption(tmp_path):
    p=tmp_path/'a.docx';p.write_bytes(docx('https://example.org/a.png',True));d=extract(p)
    assert d['blocks'][1]['images'][0]['status']=='not_fetched'
    assert 'caption' not in d['blocks'][1]['images'][0]


def test_zip_size_and_duplicate_member_guards(tmp_path):
    p=tmp_path/'a.docx';p.write_bytes(docx())
    with zipfile.ZipFile(p,'a') as z:z.writestr('huge',b'x'*20_000_001)
    with pytest.raises(ValueError,match='budget'):extract(p)
    p.write_bytes(docx())
    with pytest.warns(UserWarning):
        with zipfile.ZipFile(p,'a') as z:z.writestr('word/media/a.png',b'other')
    with pytest.raises(ValueError,match='duplicate'):extract(p)


def prepare(tmp_path):
    source=tmp_path/'source';source.mkdir();text='primary article';(source/'text.json').write_text(json.dumps({'text':text,'sha256':digest(text),'format':'JATS','url':'https://example.org/original'}))
    (source/'article.xml').write_text('''<article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta><article-id pub-id-type="pmid">1</article-id><article-id pub-id-type="pmcid">PMC1</article-id></article-meta></front><body><supplementary-material xlink:href="mmc1.docx"/></body></article>''')
    archive=tmp_path/'archive.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('mmc1.docx',docx())
    receipt=tmp_path/'receipt.json';receipt.write_text(json.dumps({'url':'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC1/supplementaryFiles','status':200,'sha256':sha(archive)}))
    m={'policy':'primary_supplement_context_upgrade_v1','source_folder':str(source),'record':{'id':'1','pmcid':'PMC1'},'archive':str(archive),'archive_receipt':str(receipt),'files_sha256':{str(p):sha(p) for p in [*source.iterdir(),archive,receipt]}}
    path=tmp_path/'manifest.json';path.write_text(json.dumps(m));return path,source


def test_normal_archive_augment_consumer_and_immutable_upgrade(tmp_path,monkeypatch):
    manifest,source=prepare(tmp_path)
    def forbidden(*args,**kwargs):raise AssertionError('Network must not run')
    monkeypatch.setattr('requests.sessions.Session.request',forbidden)
    out=tmp_path/'upgraded';result=upgrade(manifest,out)
    assert result['status']=='upgraded' and result['originals_unchanged']
    doc=json.loads((out/'text.json').read_text())
    assert 'word/document.xml body block 2' in doc['text']
    assert 'pixels_preserved_not_transcribed' in doc['text']
    a=doc['supplements']['attachments'][0];context=json.loads((out/a['ordered_context']['relative_path']).read_text());image=context['blocks'][1]['images'][0]
    assert image['relationship_id']=='rId1'
    assert sha(out/a['ordered_context']['asset_directory']/image['asset_filename'])==image['sha256']
    with pytest.raises(ValueError,match='new destination'):upgrade(manifest,out)
    assert 'supplements' not in json.loads((source/'text.json').read_text())


def test_wrong_primary_archive_identity_rejected(tmp_path):
    manifest,source=prepare(tmp_path);m=json.loads(manifest.read_text());m['record']['pmcid']='PMC2';manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='identity'):upgrade(manifest,tmp_path/'out')


def test_original_jats_external_doctype_allowed_without_entity_resolution():
    from scripts.docx_evidence import safe_xml
    root=safe_xml(b'<!DOCTYPE article PUBLIC "JATS" "https://example.org/unfetched.dtd"><article/>',allow_external_doctype=True)
    assert root.tag=='article'
    with pytest.raises(ValueError,match='entities'):
        safe_xml(b'<!DOCTYPE article [<!ENTITY attack SYSTEM "file:///etc/passwd">]><article>&attack;</article>',allow_external_doctype=True)

import hashlib
import json

import pytest

from scripts.model_backend import digest
from scripts.supplements import augment, publisher_attachment_candidates


def source():
    return {'identity':{'doi_metadata':True,'metadata':{'citation_doi':'10.1007/s12263-015-0503-1'}}}


def test_exact_primary_identifier_route():
    assert publisher_attachment_candidates(source(),{'doi':'10.1007/s12263-015-0503-1'},'https://pmc.ncbi.nlm.nih.gov/bin/12263_2015_503_MOESM1_ESM.docx')==['https://static-content.springer.com/esm/art%3A10.1007%2Fs12263-015-0503-1/MediaObjects/12263_2015_503_MOESM1_ESM.docx']


@pytest.mark.parametrize('name',['12263_2016_503_MOESM1_ESM.docx','12263_2015_504_MOESM1_ESM.docx','12264_2015_503_MOESM1_ESM.docx','other.docx','..%2F12263_2015_503_MOESM1_ESM.docx'])
def test_no_cross_article_assets(name):
    assert not publisher_attachment_candidates(source(),{'doi':'10.1007/s12263-015-0503-1'},'https://example.org/'+name)


def test_unverified_or_wrong_doi():
    assert not publisher_attachment_candidates(source(),{'doi':'different'},'https://example.org/12263_2015_503_MOESM1_ESM.docx')
    d=source();d['identity']['doi_metadata']=False
    assert not publisher_attachment_candidates(d,{'doi':'10.1007/s12263-015-0503-1'},'https://example.org/12263_2015_503_MOESM1_ESM.docx')


def test_normal_augment_after_failed_primary_route(tmp_path,monkeypatch):
    raw=b'<section id="supplement"><a href="/bin/12263_2015_503_MOESM1_ESM.txt">Supplement</a></section>'
    (tmp_path/'primary.html').write_bytes(raw)
    doc={**source(),'text':'original','sha256':digest('original'),'url':'https://pmc.ncbi.nlm.nih.gov/article','html_relative_path':'primary.html','html_sha256':hashlib.sha256(raw).hexdigest()}
    calls=[]
    def get(self,url):
        calls.append(url)
        if 'static-content.springer.com' not in url:raise ValueError('Preserved failed route')
        body=b'Original supplementary characteristics; no glucose endpoint.'
        return body,{'sha256':hashlib.sha256(body).hexdigest()}
    monkeypatch.setattr('scripts.supplements.PublicFetcher.get',get)
    r=augment({'doi':'10.1007/s12263-015-0503-1','pmcid':'PMC123'},tmp_path,doc)
    assert len(calls)==3
    a=r['supplements']['attachments'][0]
    assert a['status']=='parsed' and a['publisher_attempts'][0]['status']=='parsed'
    assert 'no glucose endpoint' in r['text']
    assert 'archive_error' in a and 'reason' in a
    assert json.loads((tmp_path/('primary-'+doc['sha256'][:16]+'.json')).read_text())==doc


def upgrade_fixture(tmp_path):
    from scripts.model_backend import atomic_json
    from scripts.primary_image_queue import sha
    folder=tmp_path/'source';folder.mkdir()
    html=b'<section id="supplement"><a href="/bin/12263_2015_503_MOESM1_ESM.txt">Supplement</a></section>'
    (folder/'article.html').write_bytes(html)
    doc={**source(),'text':'Original article','sha256':digest('Original article'),'url':'https://pmc.ncbi.nlm.nih.gov/article','html_relative_path':'article.html','html_sha256':hashlib.sha256(html).hexdigest()}
    atomic_json(folder/'text.json',doc)
    asset=tmp_path/'asset.txt';asset.write_text('Original attachment without outcome data')
    url='https://static-content.springer.com/esm/art%3A10.1007%2Fs12263-015-0503-1/MediaObjects/12263_2015_503_MOESM1_ESM.txt'
    receipt=tmp_path/'receipt.json';atomic_json(receipt,{'url':url,'final_url':url,'status':200,'sha256':sha(asset)})
    m={'policy':'publisher_supplement_upgrade_v1','source_folder':str(folder),'asset':str(asset),'receipt':str(receipt),'record':{'id':'123','pmcid':'PMC123','doi':'10.1007/s12263-015-0503-1'},'files_sha256':{str(p):sha(p) for p in [*folder.iterdir(),asset,receipt]}}
    manifest=tmp_path/'manifest.json';atomic_json(manifest,m);return manifest,m


def test_receipt_backed_upgrade_normal_consumer(tmp_path):
    from scripts.upgrade_publisher_supplement import upgrade
    manifest,_m=upgrade_fixture(tmp_path)
    result=upgrade(manifest,tmp_path/'successor')
    assert result['originals_unchanged'] and result['network_requests']==0
    assert result['parsed_attachments'][0]['status']=='parsed'
    assert 'Original attachment' in json.loads((tmp_path/'successor/text.json').read_text())['text']
    with pytest.raises(ValueError,match='isolated'):upgrade(manifest,tmp_path/'successor')


@pytest.mark.parametrize('kind',['wrong_asset','wrong_article_url','failed_response','missing_pin'])
def test_upgrade_rejects_unbound_assets(tmp_path,kind):
    from pathlib import Path

    from scripts.primary_image_queue import sha
    from scripts.upgrade_publisher_supplement import upgrade
    manifest,m=upgrade_fixture(tmp_path)
    r=Path(m['receipt']);receipt=json.loads(r.read_text())
    if kind=='wrong_asset':receipt['sha256']='0'*64
    elif kind=='wrong_article_url':receipt['url']=receipt['url'].replace('0503','0504');receipt['final_url']=receipt['url']
    elif kind=='failed_response':receipt['status']=404
    else:del m['files_sha256'][m['asset']]
    r.write_text(json.dumps(receipt));m['files_sha256'][str(r)]=sha(r);manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError):upgrade(manifest,tmp_path/'successor')
    assert not (tmp_path/'successor').exists()

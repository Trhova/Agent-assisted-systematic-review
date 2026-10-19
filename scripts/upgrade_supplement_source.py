"""Versioned, cache-only primary-supplement context upgrade; originals immutable."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from scripts.model_backend import atomic_json,digest
from scripts.supplements import augment
from scripts.docx_evidence import safe_xml


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def upgrade(manifest, destination):
    manifest=Path(manifest);m=json.loads(manifest.read_text());source=Path(m['source_folder']).resolve();destination=Path(destination).resolve()
    if m.get('policy')!='primary_supplement_context_upgrade_v1':raise ValueError('Unsupported source upgrade policy')
    if destination.exists() or destination.is_relative_to(source):raise ValueError('Use new destination outside original source')
    before={str(p):sha(p) for p in source.rglob('*') if p.is_file()}
    if any(p.is_symlink() for p in source.rglob('*')):raise ValueError('Source symlinks unsupported')
    if not before or not set(before)<=m['files_sha256'].keys():raise ValueError('Source pins incomplete')
    if not {m['archive'],m['archive_receipt']}<=m['files_sha256'].keys():raise ValueError('Archive pins incomplete')
    for path,h in m['files_sha256'].items():
        if sha(path)!=h:raise ValueError('Source pin differs')
    doc=json.loads((source/'text.json').read_text());record=m['record']
    if digest(doc['text'])!=doc['sha256']:raise ValueError('Primary text checksum differs')
    root=safe_xml((source/'article.xml').read_bytes(),allow_external_doctype=True)
    ids={x.get('pub-id-type'):''.join(x.itertext()).strip() for x in root.findall('.//front/article-meta/article-id')}
    if ids.get('pmid')!=str(record['id']) or ids.get('pmcid')!=record['pmcid']:raise ValueError('Original article identity differs')
    receipt=json.loads(Path(m['archive_receipt']).read_text());body=Path(m['archive']).read_bytes();url='https://www.ebi.ac.uk/europepmc/webservices/rest/'+record['pmcid']+'/supplementaryFiles'
    if receipt.get('url')!=url or receipt.get('status')!=200 or receipt.get('sha256')!=hashlib.sha256(body).hexdigest():raise ValueError('Primary archive receipt binding differs')
    shutil.copytree(source,destination)
    atomic_json(destination/'text.before_context_upgrade.json',doc)
    if doc.get('supplements'):
        rel=Path(doc['supplements']['primary_snapshot']);target=(destination/rel).resolve()
        if not target.is_relative_to(destination):raise ValueError('Primary snapshot escapes source')
        doc=json.loads(target.read_text())
        if digest(doc['text'])!=doc['sha256']:raise ValueError('Primary snapshot checksum differs')
    cache=destination/'supplement_http'/digest(url);cache.mkdir(parents=True,exist_ok=True)
    (cache/'body').write_bytes(body)
    atomic_json(cache/'response.json',{'status':'success','url':url,'sha256':hashlib.sha256(body).hexdigest(),'cache_policy_version':2,'acquisition_method':'verified_preserved_primary_archive_import','original_receipt_sha256':sha(m['archive_receipt'])})
    shutil.copyfile(m['archive_receipt'],destination/'imported_archive_receipt.json')
    previous=os.environ.get('ASR_ACQUISITION_CACHE_ONLY');os.environ['ASR_ACQUISITION_CACHE_ONLY']='1'
    try:result=augment(record,destination,doc)
    finally:
        if previous is None:os.environ.pop('ASR_ACQUISITION_CACHE_ONLY',None)
        else:os.environ['ASR_ACQUISITION_CACHE_ONLY']=previous
    context=[a['ordered_context'] for a in result['supplements']['attachments'] if a.get('ordered_context') and a.get('status')=='parsed']
    receipt={'policy':m['policy'],'status':'upgraded' if context else 'unresolved_no_ordered_context','manifest_sha256':sha(manifest),'original_files_sha256':before,'originals_unchanged':all(sha(p)==h for p,h in before.items()),'source_text_sha256_before':json.loads((source/'text.json').read_text())['sha256'],'source_text_sha256_after':result['sha256'],'ordered_contexts':context,'network_requests':0,'model_calls':0,'scientific_decisions_changed':False,'limitations':['Source replay does not resolve missing cluster adjustments or establish outcome eligibility.','Images are preserved and located, not automatically transcribed.'],'output_sha256':{str(p.relative_to(destination)):sha(p) for p in destination.rglob('*') if p.is_file()}}
    if not receipt['originals_unchanged']:raise ValueError('Original source changed')
    atomic_json(destination/'source_upgrade_manifest.json',receipt)
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(upgrade(a.manifest,a.output),indent=2))

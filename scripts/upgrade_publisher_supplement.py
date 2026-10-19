"""Replay a receipt-backed publisher attachment through normal supplement ingestion."""
import argparse
import json
import os
import shutil
from pathlib import Path

from scripts.model_backend import atomic_json, digest
from scripts.primary_image_queue import sha
from scripts.supplements import (
    augment,
    linked_attachments,
    publisher_attachment_candidates,
)


def upgrade(manifest, output):
    m=json.loads(Path(manifest).read_text());source=Path(m['source_folder']).resolve();output=Path(output).resolve()
    if m.get('policy')!='publisher_supplement_upgrade_v1':raise ValueError('Unsupported policy')
    if output.exists() or output.is_relative_to(source):raise ValueError('New isolated output required')
    before={str(p):sha(p) for p in source.rglob('*') if p.is_file()}
    if any(p.is_symlink() for p in source.rglob('*')) or not set(before)<=m['files_sha256'].keys():raise ValueError('Complete regular source pins required')
    for path,h in m['files_sha256'].items():
        if sha(path)!=h:raise ValueError('Source pin changed')
    if not {m['asset'],m['receipt']}<=m['files_sha256'].keys():raise ValueError('Asset/receipt pins required')
    doc=json.loads((source/'text.json').read_text())
    if digest(doc['text'])!=doc['sha256']:raise ValueError('Original text mismatch')
    primary=doc
    if doc.get('supplements'):
        p=(source/doc['supplements']['primary_snapshot']).resolve()
        if not p.is_relative_to(source):raise ValueError('Unsafe primary snapshot')
        primary=json.loads(p.read_text())
    if digest(primary['text'])!=primary['sha256']:raise ValueError('Primary text mismatch')
    candidates=[u for link in linked_attachments(source,primary,m['record']) for u in publisher_attachment_candidates(primary,m['record'],link)]
    receipt=json.loads(Path(m['receipt']).read_text());body=Path(m['asset']).read_bytes()
    if receipt.get('url') not in candidates or receipt.get('final_url')!=receipt['url'] or receipt.get('status')!=200 or receipt.get('sha256')!=sha(m['asset']):raise ValueError('Exact primary-derived publisher receipt required')
    shutil.copytree(source,output);atomic_json(output/'text.before_publisher_upgrade.json',doc)
    cache=output/'supplement_http'/digest(receipt['url']);cache.mkdir(parents=True,exist_ok=True)
    (cache/'body').write_bytes(body)
    atomic_json(cache/'response.json',{'status':'success','url':receipt['url'],'sha256':receipt['sha256'],'cache_policy_version':2,'acquisition_method':'verified_preserved_publisher_attachment_import','original_receipt_sha256':sha(m['receipt'])})
    shutil.copyfile(m['receipt'],output/'publisher_acquisition_receipt.json')
    old=os.environ.get('ASR_ACQUISITION_CACHE_ONLY');os.environ['ASR_ACQUISITION_CACHE_ONLY']='1'
    try:result=augment(m['record'],output,primary)
    finally:
        if old is None:os.environ.pop('ASR_ACQUISITION_CACHE_ONLY',None)
        else:os.environ['ASR_ACQUISITION_CACHE_ONLY']=old
    parsed=[a for a in result['supplements']['attachments'] if a.get('status')=='parsed' and a.get('raw_sha256')==receipt['sha256']]
    if not parsed:raise ValueError('Verified publisher source not consumed')
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('Original source changed')
    result={'policy':m['policy'],'manifest_sha256':sha(manifest),'original_files_sha256':before,'originals_unchanged':True,'parsed_attachments':parsed,'source_text_sha256':result['sha256'],'network_requests':0,'model_calls':0,'scientific_decisions_changed':False}
    atomic_json(output/'publisher_upgrade_receipt.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(upgrade(a.manifest,a.output),indent=2))

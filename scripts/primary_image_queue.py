"""Actionable ordered primary-image inspections without numeric admission."""
import hashlib
import json
from pathlib import Path
from scripts.model_backend import digest


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def inside(folder,relative):
    p=(folder/relative).resolve()
    if not p.is_relative_to(folder.resolve()):raise ValueError('Image evidence path escapes source')
    return p


def build(folder,doc):
    folder=Path(folder);items=[];seen=set()
    for attachment in doc.get('supplements',{}).get('attachments',[]):
        c=attachment.get('ordered_context')
        if not c:continue
        raw=inside(folder,attachment['relative_path']);sidecar=inside(folder,c['relative_path'])
        if sha(raw)!=attachment['raw_sha256'] or sha(sidecar)!=c['sha256']:raise ValueError('Primary context checksum differs')
        evidence=json.loads(sidecar.read_text())
        if evidence['raw_sha256']!=attachment['raw_sha256']:raise ValueError('Context raw binding differs')
        blocks=evidence['blocks']
        for j,block in enumerate(blocks):
            for image in block['images']:
                if image.get('external'):continue
                path=inside(folder,str(Path(c['asset_directory'])/image['asset_filename']))
                if sha(path)!=image['sha256']:raise ValueError('Primary image checksum differs')
                identity=digest({'raw':attachment['raw_sha256'],'member':image['member'],'relationship':image['relationship_id'],'locator':block['locator']})
                if identity in seen:raise ValueError('Duplicate image identity')
                seen.add(identity)
                items.append({'id':identity,'status':'pending_source_inspection','image_relative_path':str(path.relative_to(folder.resolve())),'image_sha256':image['sha256'],'raw_relative_path':attachment['relative_path'],'raw_sha256':attachment['raw_sha256'],'context_relative_path':c['relative_path'],'context_sha256':c['sha256'],'relationship_id':image['relationship_id'],'member':image['member'],'locator':block['locator'],'preceding_text':blocks[j-1]['text'] if j else '', 'following_text':blocks[j+1]['text'] if j+1<len(blocks) else '', 'context_interpretation':'Adjacent text only; caption ownership not established','numerical_admission':False,'next_action':'Inspect original pixels with source locator; preserve uncertainty; do not infer missing N/dispersion or digitize graphs.'})
    previous={x['id']:x for x in doc.get('primary_image_queue',{}).get('items',[])}
    for item in items:
        old=previous.get(item['id'],{})
        if old.get('inspection_relative_path'):
            receipt=inside(folder,old['inspection_relative_path'])
            if sha(receipt)!=old.get('inspection_sha256'):raise ValueError('Inspection receipt checksum differs')
            result=json.loads(receipt.read_text())
            if result.get('item_id')!=item['id'] or result.get('source_locator',{}).get('image_sha256')!=item['image_sha256'] or result.get('source_locator',{}).get('context_sha256')!=item['context_sha256'] or result.get('numerical_admission') is not False:raise ValueError('Inspection binding differs')
            item.update(status=result['status'],inspection_relative_path=old['inspection_relative_path'],inspection_sha256=old['inspection_sha256'],next_action=old.get('next_action','Retain completed source observation; no automatic reinspection.'))
    return {'policy':'primary_image_queue_v1','source_text_sha256':doc['sha256'],'items':items,'limitations':['Queue presence is not evidence of outcome relevance or statistical compatibility.','Image-derived observations never become accepted statistical rows under this policy.']}

"""One queued primary image, two isolated source-reading calls; no numerical admission."""
import argparse
import json
import shutil
from pathlib import Path
from scripts.model_backend import model_json,atomic_json,digest
from scripts.primary_image_queue import build,sha
from scripts.import_model_cache import verify_entry
from scripts.verify_reference_source import obj,TEXT

READ=obj({'legible':{'type':'boolean'},'relevance':{'type':'string','enum':['relevant','irrelevant','unclear']},'content_type':{'type':'string','enum':['graph','table','diagram','other','unclear']},'visible_labels':{'type':'array','items':TEXT},'visual_observations':{'type':'array','items':TEXT},'explicit_analyzed_n_present':{'type':'boolean'},'explicit_mean_and_sd_present':{'type':'boolean'},'limitations':{'type':'array','items':TEXT}})
CHECK=obj({'valid':{'type':'boolean'},'problems':{'type':'array','items':TEXT},'limitations':{'type':'array','items':TEXT}})


def run(manifest_path,output):
    m=json.loads(Path(manifest_path).read_text());output=Path(output)
    if m.get('policy')!='primary_image_inspection_v1' or not m.get('model','').strip():raise ValueError('Policy/model required')
    if output.exists():raise ValueError('Use new output; reconcile uncertain calls before resuming')
    folder=Path(m['source_folder']).resolve()
    if output.resolve().is_relative_to(folder):raise ValueError('Output must preserve original source')
    for p,h in m['files_sha256'].items():
        if sha(p)!=h:raise ValueError('Frozen primary source differs')
    doc=json.loads((folder/'text.json').read_text())
    if digest(doc['text'])!=doc['sha256']:raise ValueError('Source text checksum differs')
    queue=build(folder,doc)
    pending=[x for x in queue['items'] if x['status']=='pending_source_inspection']
    if not pending or pending[0]['id']!=m['selected_id']:raise ValueError('Selection must be frozen first document-order item')
    item=pending[0];image=folder/item['image_relative_path'];output.mkdir(parents=True)
    atomic_json(output/'queue_before.json',queue)
    prompt='Inspect this original primary-study image only. This is source triage, not numerical extraction. Describe visible labels and plot/table structure; do not digitize marks, infer means/SDs/N, assert nearby text is its caption, or fabricate verbatim article quotations. Pixel-derived wording must be called visual observations. Answer the frozen question using image and labelled adjacent text.\nQUESTION: '+m['question']+'\nPROVENANCE/ADJACENT TEXT (ownership not established):\n'+json.dumps(item)
    proposal=model_json(prompt,READ,output/'read',model=m['model'],max_attempts=1,images=[image],timeout=300)
    atomic_json(output/'proposal.json',proposal)
    check=model_json('Separate source-image verification. Inspect attached original pixels and the proposal. Reject any invented exact values, N/SD inference, misleading caption attribution or unsupported visual claims. This is source triage only, never statistical admission. Same-model correlated errors possible.\nPROVENANCE:\n'+json.dumps(item)+'\nPROPOSAL:\n'+json.dumps(proposal),CHECK,output/'verify',model=m['model'],max_attempts=1,images=[image],timeout=300)
    atomic_json(output/'verification.json',check)
    receipts=[]
    for phase in ['read','verify']:
        requests=list((output/phase).glob('*/request.json'))
        if len(requests)!=1:raise ValueError('Unexpected source-inspection request count')
        receipts.append(verify_entry(requests[0].parent,model=m['model'],backend='codex'))
    valid=check['valid'] and not check['problems']
    status=('inspected_unverified' if not valid else 'checked_unreadable' if not proposal['legible'] else 'checked_irrelevant' if proposal['relevance']=='irrelevant' else 'checked_relevance_unclear' if proposal['relevance']=='unclear' else 'source_checked_visual_observation')
    result={'policy':m['policy'],'item_id':item['id'],'status':status,'source_locator':item,'visual_observations':proposal,'verification':check,'numerical_admission':False,'request_receipts':receipts,'manifest_sha256':sha(manifest_path),'limitations':['Separate requests from the same model are procedural separation, not independent human expertise.','No image observations are merged into primary text or accepted statistical rows.']}
    atomic_json(output/'inspection.json',result)
    # Usable successor source metadata, leaving raw primary text unchanged.
    target=output/'source_successor';shutil.copytree(folder,target)
    receipt_rel='image-inspections/'+item['id']+'.json'
    atomic_json(target/receipt_rel,result)
    item.update(status=result['status'],inspection_relative_path=receipt_rel,inspection_sha256=sha(target/receipt_rel),numerical_admission=False,next_action='Retain source-checked visual evidence; any quantitative use needs a separate supported protocol and input verification.' if valid else 'Resolve original visual ambiguity before further use.')
    doc['primary_image_queue']=queue
    doc['primary_image_inspections']=[{'item_id':item['id'],'status':result['status'],'artifact':receipt_rel,'numerical_admission':False}]
    atomic_json(target/'text.json',doc);atomic_json(output/'queue_after.json',queue)
    if any(sha(p)!=h for p,h in m['files_sha256'].items()):raise ValueError('Original source changed')
    atomic_json(output/'completion.json',{'source_pins_unchanged':True,'new_model_adapter_calls':2,'numeric_calls':0,'pending_images':sum(x['status']=='pending_source_inspection' for x in queue['items']),'source_text_unchanged':doc['sha256']==digest(doc['text'])})
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(run(a.manifest,a.output),indent=2))

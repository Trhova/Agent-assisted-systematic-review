"""Bounded single-record source continuation; never modifies or pools old results."""
import argparse
import json
import shutil
import sys
from pathlib import Path

from scripts.autonomous_review import EXTRACT, HEADER, VERIFY
from scripts.continuous_derivations import extraction_instructions, extraction_schema
from scripts.import_model_cache import verify_entry
from scripts.model_backend import atomic_json, digest, model_json
from scripts.outcome_availability import build
from scripts.primary_image_queue import sha


def run(manifest,output):
    m=json.loads(Path(manifest).read_text());output=Path(output)
    if m.get('policy')!='single_source_reassessment_v1' or not m.get('model','').strip():raise ValueError('Explicit model/policy required')
    if getattr(sys,'_asr_frozen_code',None)!=m['code_sha256']:raise ValueError('Frozen execution required')
    if output.exists():raise ValueError('New output required; reconcile uncertain requests')
    for path,h in m['files_sha256'].items():
        if sha(path)!=h:raise ValueError('Pinned inputs changed')
    if not {m['protocol'],m['source']}<=m['files_sha256'].keys():raise ValueError('Required inputs not pinned')
    protocol=json.loads(Path(m['protocol']).read_text());doc=json.loads(Path(m['source']).read_text())
    if digest(doc['text'])!=doc['sha256']:raise ValueError('Source text mismatch')
    if protocol.get('summary_policy') or protocol.get('multiarm_policy') or protocol.get('measure')=='RR':raise ValueError('This source reassessment currently supports basic continuous contracts only')
    schema=extraction_schema(EXTRACT,protocol) if protocol.get('dispersion_policy') else EXTRACT
    prompt=HEADER+' Assess this original primary article and its linked original supplement against the frozen outcome contract. Eligibility and data availability are distinct: an eligible trial with absent required outcome data remains included/unresolved, never excluded merely because numbers are missing. Do not substitute general characteristics or baseline values for endpoint outcomes. Quote exact source evidence and identify source locators. Empty rows are required if inputs are unsupported. '+extraction_instructions(protocol)+'\nCONTRACT:\n'+json.dumps(protocol)+'\nSOURCE:\n'+doc['text']
    output.mkdir(parents=True)
    result=model_json(prompt,schema,output/'extract',model=m['model'],max_attempts=1,timeout=300)
    atomic_json(output/'proposal.json',result)
    check=model_json(HEADER+' Separately verify this eligibility and outcome-availability assessment against the entire original article and supplement. Check what the supplement actually reports; do not mistake its general-characteristic N or SE for outcome-specific endpoint data. A negative outcome-availability assessment is limited to supplied reports, not proof no companion report exists. Never endorse numerical inputs lacking explicit source support.\nCONTRACT:\n'+json.dumps(protocol)+'\nPROPOSAL:\n'+json.dumps(result)+'\nSOURCE:\n'+doc['text'],VERIFY,output/'verify',model=m['model'],max_attempts=1,timeout=300)
    atomic_json(output/'verification.json',check)
    receipts=[]
    for phase,value in [('extract',result),('verify',check)]:
        paths=list((output/phase).glob('*/request.json'))
        if len(paths)!=1:raise ValueError('Unexpected request count')
        receipts.append(verify_entry(paths[0].parent,model=m['model'],backend='codex'))
        if json.loads((paths[0].parent/'parsed.json').read_text())!=value:raise ValueError('Saved assessment differs from response')
    rid=m['record']['id'];target=output/'sources'/rid;shutil.copytree(Path(m['source']).parent,target)
    atomic_json(output/'protocol.json',protocol)
    atomic_json(output/'extractions.json',[{'id':rid,'status':'extracted','result':result,'source_sha256':doc['sha256'],'source_reassessment':{'verification':check,'request_receipts':receipts,'manifest_sha256':sha(manifest)}}])
    atomic_json(output/'accepted.json',[])
    if m.get('validate_candidate_rows'):
        from scripts.autonomous_review import validate_evidence
        from scripts.continuous_derivations import derive
        candidates=[]
        for original in result['rows']:
            row={**original,'record_id':rid}
            errors=[]
            if not check['valid'] or check['problems'] or result['eligibility']!='include':
                errors.append('Source assessment not independently verified eligible')
            try:
                if protocol.get('dispersion_policy'):
                    row=derive(row,doc['text'],protocol,doc['sha256'])
                errors+=validate_evidence(row,doc['text'],protocol)
            except ValueError as error:
                errors.append(str(error))
            candidates.append({'row':row,'validation_errors':errors,'input_supported':not errors,'accepted_for_pooling':False})
        atomic_json(output/'candidate_validation.json',{'policy':'single_source_candidate_validation_v1','candidates':candidates,'trial_integrity_and_family_adjudication_pending':True,'pooled':False})
    atomic_json(output/'status.json',{'status':'incomplete','scope':'Single-source continuation, not complete review; old acceptance and synthesis untouched','model':m['model'],'code_sha256':m['code_sha256']})
    atomic_json(output/'availability.json',build(output))
    if any(sha(p)!=h for p,h in m['files_sha256'].items()):raise ValueError('Pinned inputs changed')
    atomic_json(output/'completion.json',{'verified_assessment':check['valid'] and not check['problems'],'numeric_rows_proposed':len(result['rows']),'numeric_rows_accepted':0,'model_calls':2,'numerical_runs':0,'source_pins_unchanged':True,'next_action':'If any rows proposed, require normal derivation, validation, integrity and family gates in separately authorized continuation; no automatic pooling.'})
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(run(a.manifest,a.output),indent=2))

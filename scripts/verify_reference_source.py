"""Bounded evaluator-only blind image transcription and source verification."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.model_backend import model_json, atomic_json
from scripts.import_model_cache import verify_entry
from scripts.evaluate_contract import sha


def obj(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


TEXT={'type':'string'}
ROW=obj({'label':TEXT,'events_treatment':{'type':['integer','null']},'n_treatment':{'type':['integer','null']},'events_control':{'type':['integer','null']},'n_control':{'type':['integer','null']},'locator':TEXT})
READ=obj({'image_legible':{'type':'boolean'},'treatment_header':TEXT,'control_header':TEXT,'rows':{'type':'array','items':ROW},'limitations':{'type':'array','items':TEXT}})
CHECK=obj({'cells_match_source':{'type':'boolean'},'mapping_supported':{'type':'boolean'},'problems':{'type':'array','items':TEXT},'row_checks':{'type':'array','items':obj({'record_id':TEXT,'image_label':TEXT,'source_locator':TEXT,'mapping_evidence':TEXT,'cells_match':{'type':'boolean'},'mapping_supported':{'type':'boolean'}})},'limitations':{'type':'array','items':TEXT}})


AXES=('cells','trial_identity','arms','timepoint','population','source_locator','outcome')
STATE={'type':'string','enum':['supported','unsupported','unclear']}
CHECK_V2=obj({'blocking_problems':{'type':'array','items':obj({'category':{'type':'string','enum':list(AXES)},'record_id':TEXT,'reason':TEXT})},
    'observations':{'type':'array','items':obj({'kind':{'type':'string','enum':['primary_value_difference','followup_limitation','scope_note']},'record_id':TEXT,'description':TEXT})},
    'row_checks':{'type':'array','items':obj({'record_id':TEXT,'image_label':TEXT,'source_locator':TEXT,'mapping_evidence':TEXT,'assessments':obj({axis:STATE for axis in AXES})})},
    'limitations':{'type':'array','items':TEXT}})


def adjudicate_v2(blind,check,reference,mapping):
    # v1 cell/coverage guards remain; every semantic axis adds an independent gate.
    converted={'cells_match_source':True,'mapping_supported':True,'problems':check['blocking_problems'],
        'row_checks':[{**x,'cells_match':x['assessments']['cells']=='supported',
        'mapping_supported':all(x['assessments'].get(a)=='supported' for a in AXES)} for x in check['row_checks']]}
    result=adjudicate(blind,converted,reference,mapping)
    for row in check['row_checks']:
        for axis in AXES:
            if row['assessments'].get(axis)!='supported':result['problems'].append('blocking_'+axis+':'+row['record_id'])
    result['valid']=not result['problems']
    return result


def adjudicate(blind, check, reference, mapping):
    problems=[]
    if not blind['image_legible']:problems.append('image_not_legible')
    labels=[x['label'] for x in blind['rows']]
    checks=check['row_checks'];ids=[x['record_id'] for x in checks]
    expected={str(x['record_id']):x for x in reference['rows']}
    if len(labels)!=len(set(labels)) or len(ids)!=len(set(ids)):problems.append('ambiguous_rows')
    if set(ids)!=set(expected) or set(expected)!={str(x['record_id']) for x in mapping}:problems.append('coverage_differs')
    bylabel={x['label']:x for x in blind['rows']}
    for row in checks:
        source=bylabel.get(row['image_label']);target=expected.get(row['record_id'])
        if not source or not target:problems.append('unmapped_image_row');continue
        if any(source[k]!=target[k] for k in ('events_treatment','n_treatment','events_control','n_control')):problems.append('blind_cell_disagreement:'+row['record_id'])
        if not row['cells_match'] or not row['mapping_supported'] or not row['source_locator'] or not row['mapping_evidence']:problems.append('row_unverified:'+row['record_id'])
    if not check['cells_match_source'] or not check['mapping_supported'] or check['problems']:problems.append('verifier_rejected')
    return {'valid':not problems,'problems':problems}


def run(manifest_path, output):
    m=json.loads(Path(manifest_path).read_text());output=Path(output)
    if output.exists():raise ValueError('Use new isolated output; reconcile uncertain submissions before continuation')
    if m.get('policy') not in {'reference_source_verification_v1','reference_source_verification_v2'} or not m.get('model','').strip():raise ValueError('Policy and explicit model required')
    for p,h in m['files_sha256'].items():
        if sha(p)!=h:raise ValueError('Frozen source differs: '+p)
    output.mkdir(parents=True)
    atomic_json(output/'started.json',{'manifest_sha256':sha(manifest_path),'model':m['model'],'max_adapter_invocations':2})
    context=Path(m['review_text']).read_text()
    v2=m['policy']=='reference_source_verification_v2'
    if v2:
        context+='\nORIGINAL SUPPLEMENT WITH XML BLOCK LOCATORS:\n'+Path(m['supplement_text']).read_text()
    prompt='Evaluator-only blind transcription. Read the attached original published forest image. Transcribe every study row and original arm headers exactly; no pooled totals. Use null for unreadable cells. Locator is visible row label, not invented pixel coordinates. Do not infer values from effects or prior knowledge. The supplied original review text is context only. No proposed manual cells or primary extracted results are supplied.\nORIGINAL REVIEW TEXT:\n'+context
    blind=model_json(prompt,READ,output/'blind',model=m['model'],max_attempts=1,images=[m['image']],timeout=300)
    atomic_json(output/'blind.json',blind)
    # Open evaluator targets only after independent source reading has completed.
    ref=json.loads(Path(m['reference']).read_text());contract=json.loads(Path(m['contract']).read_text())
    primary='\n'.join('ORIGINAL PRIMARY '+x['record_id']+'\n'+Path(x['text']).read_text() for x in m['primary_context'])
    prompt='Evaluator-only independent verification in a new conversation. Inspect attached published image and original review/primary contexts. Verify proposed PUBLISHED cells (not replace with primary cells), author/trial/arm identity, and exact primary outcome horizons in mappings. Distinguish published forest cells from primary denominators. Do not endorse if evidence ambiguous. Provide original text/source locators; mapping_evidence must be one exact verbatim original-text quotation anchoring trial identity or timing, without added commentary. No invented quotations/coordinates. Same-model reading may have correlated errors.\nBLIND IMAGE READING:\n'+json.dumps(blind)+'\nPROPOSED PUBLISHED CELLS:\n'+json.dumps(ref['rows'])+'\nPROPOSED MAPPING:\n'+json.dumps(contract['mapping'])+'\nORIGINAL REVIEW:\n'+context+'\n'+primary
    if v2:
        prompt+='\nTYPED VERIFICATION POLICY: Independently assess every row for cells, trial_identity, arms, timepoint, population, source_locator and outcome. Unsupported or unclear on ANY axis blocks. Matching integers do not establish identity or semantics. Use blocking_problems for any wrong/ambiguous source, row, identity, arm, outcome, population or timing. Observations are only known primary-versus-published value differences, follow-up limitations, or scope notes that do not undermine ALL supported axes. Do not put an unresolved semantic issue only in observations. Population must be supported for this frozen scientific contract, not an invented pure-inpatient subset; retain differences from the review caption explicitly. Published transcription verification does NOT mean agreement with primary values.\nFROZEN SCIENTIFIC CONTRACT:\n'+Path(m['scientific_protocol']).read_text()
    check=model_json(prompt,CHECK_V2 if v2 else CHECK,output/'verify',model=m['model'],max_attempts=1,images=[m['image']],timeout=300)
    atomic_json(output/'verification.json',check)
    receipts=[]
    for base in [output/'blind',output/'verify']:
        entries=list(base.glob('*/request.json'))
        if len(entries)!=1:raise ValueError('Unexpected request count')
        receipts.append(verify_entry(entries[0].parent,model=m['model'],backend='codex'))
    result=(adjudicate_v2 if v2 else adjudicate)(blind,check,ref,contract['mapping'])
    import unicodedata
    def norm(text):
        return ' '.join(unicodedata.normalize('NFKC',text).split())
    supplied=norm(context+'\n'+primary)
    for row in check['row_checks']:
        if not norm(row['mapping_evidence']) or norm(row['mapping_evidence']) not in supplied:
            result['problems'].append('mapping_quote_not_found:'+row['record_id'])
    result['valid']=not result['problems']
    result.update(policy='independent_reference_cells_v1',cell_reference_sha256=sha(m['reference']),mapping_sha256=hashlib.sha256(json.dumps(contract['mapping'],sort_keys=True).encode()).hexdigest(),independent_reviewer='Separate isolated '+m['model']+' request; same-model procedural separation only',method='blind image transcription then separate image/source verification with exact cell reconciliation',evidence_locator=m['image_locator'],request_receipts=receipts,manifest_sha256=sha(manifest_path),source_sha256=m['files_sha256'],limitations=['Same model can make correlated errors; this is not independent human expertise.','Model-provided source locators/evidence are not a guarantee of factual correctness.','Published-cell agreement does not resolve source-versus-review discrepancies.'])
    if any(sha(p)!=h for p,h in m['files_sha256'].items()):raise ValueError('Source changed during verification')
    atomic_json(output/'receipt.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(run(a.manifest,a.output),indent=2))

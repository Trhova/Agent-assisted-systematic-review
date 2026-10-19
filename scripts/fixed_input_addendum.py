"""Frozen fixed-input sensitivity: preserve baseline, admit only a complete new set."""
import argparse
import itertools
import json
import sys
from pathlib import Path

from scripts.audit_run import audit, same
from scripts.autonomous_review import validate_evidence
from scripts.continuous_derivations import derive
from scripts.family_adjudication import adjudicate as original_adjudicate
from scripts.family_evidence_tiers import POLICY as FAMILY_POLICY
from scripts.family_evidence_tiers import adjudicate
from scripts.import_model_cache import verify_entry
from scripts.meta_analysis import synthesize
from scripts.model_backend import atomic_json, model_json
from scripts.primary_image_queue import sha
from scripts.repair_source_candidate import gate_errors, repair_evidence
from scripts.trial_families import resolve

POLICY = 'fixed_input_postcutoff_addendum_v1'
REPAIR_POLICY = 'fixed_input_postcutoff_addendum_v2'
SCIENTIFIC_KEYS = ('outcome','unit','allowed_source_units','value_type','measure','model',
                   'timing_rule','dispersion_policy','summary_policy','multiarm_policy','dependence_rule')


def complete_set(baseline, candidate, old_links, new_links):
    ids = [r['record_id'] for r in baseline]
    if len(ids)!=len(set(ids)) or candidate['record_id'] in ids:
        raise ValueError('Duplicate report in fixed input set')
    wanted = {frozenset((rid,candidate['record_id'])) for rid in ids}
    actual = [frozenset((x['report_a'],x['report_b'])) for x in new_links]
    if set(actual)!=wanted or len(actual)!=len(wanted):
        raise ValueError('Exactly one assessment per new-versus-baseline pair required')
    resolution = resolve([*baseline,candidate],[*old_links,*new_links])
    expected_ids = set(ids)|{candidate['record_id']}
    supported = (not resolution['unresolved'] and
                 {r['record_id'] for r in resolution['rows']}==expected_ids and
                 all(x['relationship']=='distinct_trials' and x.get('independently_verified') for x in new_links))
    return {'supported':supported,'resolution':resolution,
            'rows':resolution['rows'] if supported else [],
            'reason':None if supported else 'Complete prespecified addendum not independent; no selective dropping or partial pool.'}


def load_supported_candidate(directory):
    """Replay prior repair and all its family calls without submitting new calls."""
    p=Path(directory);m=json.loads((p/'manifest.json').read_text());result=json.loads((p/'run/result.json').read_text())
    if any(sha(f)!=h for f,h in m['files_sha256'].items()):
        raise ValueError('Prior repaired-candidate pins changed')
    prior=Path(m['prior_request']);verify_entry(prior,model=m['model'],backend=m['backend'])
    calls=[]
    for folder in sorted((p/'run/model').iterdir(),key=lambda x:int(x.name)):
        requests=list(folder.glob('*/request.json'))
        if len(requests)!=1:raise ValueError('Ambiguous prior request')
        path=requests[0];receipt=verify_entry(path.parent,model=m['model'],backend=m['backend'])
        calls.append((json.loads(path.read_text()),json.loads((path.parent/'parsed.json').read_text()),receipt))
    if [x[2] for x in calls]!=result['calls']:raise ValueError('Candidate response ledger differs')
    source=json.loads(Path(m['source']).read_text());protocol=json.loads(Path(m['protocol']).read_text())
    old=json.loads((prior/'parsed.json').read_text())['rows'][0]
    row=repair_evidence(old,calls[0][1],source['text']);row['record_id']=m['record']['id']
    if protocol.get('dispersion_policy'):row=derive(row,source['text'],protocol,source['sha256'])
    if row!=result['row']:raise ValueError('Candidate scientific values changed')
    documents={rid:json.loads(Path(path).read_text())['text'] for rid,path in m['family_sources'].items()}
    index=2
    def replay(prompt,schema):
        nonlocal index
        request,value,_=calls[index];index+=1
        if request['prompt']!=prompt or request['schema']!=schema:raise ValueError('Family request replay differs')
        return value
    ids=sorted(documents)
    links=original_adjudicate([{'record_id':rid} for rid in ids],documents,replay,max_pairs=3)
    if index!=len(calls) or links!=result['family_links']:raise ValueError('Family response replay differs')
    from scripts.autonomous_review import publication_integrity_flags
    from scripts.report_chronology import assess
    c=m['chronology']
    historical=assess(c['html'],c['receipt'],m['record']['doi'],c['historical_cutoff'])
    updated=assess(c['html'],c['receipt'],m['record']['doi'],c['updated_cutoff'])
    flags=[publication_integrity_flags(r) for r in json.loads(Path(m['integrity_records']).read_text())]
    errors=gate_errors(row,source['text'],protocol,calls[1][1],any(flags),historical,updated,links,list(itertools.combinations(ids,2)))
    if errors or not result['input_supported']:raise ValueError('Prior candidate gates do not replay: '+str(errors))
    return row,source,protocol,{'requests_replayed':len(calls),'historical':historical,'updated':updated}


def run(manifest,output):
    m=json.loads(Path(manifest).read_text());output=Path(output)
    if m.get('policy') not in {POLICY,REPAIR_POLICY} or m.get('family_policy')!=FAMILY_POLICY or not m.get('model','').strip():
        raise ValueError('Explicit fixed-input/family policy and model required')
    if getattr(sys,'_asr_frozen_code',None)!=m['code_sha256']:raise ValueError('Frozen execution required')
    if output.exists():raise ValueError('New output required; reconcile uncertain submissions')
    def verify_pins():
        if any(sha(f)!=h for f,h in m['files_sha256'].items()):raise ValueError('Pinned input changed')
    verify_pins()
    candidate_directory=Path(m['candidate_directory'])
    for path in candidate_directory.rglob('*'):
        if path.is_file() and str(path) not in m['files_sha256']:
            raise ValueError('Candidate artifact not pinned')
    prior_manifest=json.loads((candidate_directory/'manifest.json').read_text())
    if any(m['files_sha256'].get(f)!=h for f,h in prior_manifest['files_sha256'].items()):
        raise ValueError('Candidate underlying evidence pins not carried forward')
    base=Path(m['baseline']);baseline_audit=audit(base)
    if not baseline_audit['valid']:raise ValueError('Baseline audit failed')
    for name in baseline_audit['artifact_sha256']:
        if str(base/name) not in m['files_sha256']:raise ValueError('Baseline audited artifact not pinned')
    baseline=json.loads((base/'trial_families.json').read_text())['rows']
    if [r['record_id'] for r in baseline]!=m['baseline_record_ids']:raise ValueError('Exact baseline membership/order differs')
    protocol=json.loads((base/'protocol.json').read_text())
    candidate,source,candidate_protocol,replay=load_supported_candidate(m['candidate_directory'])
    if any(protocol.get(k)!=candidate_protocol.get(k) for k in SCIENTIFIC_KEYS):raise ValueError('Scientific estimand/method differs')
    if candidate['record_id']!=m['candidate_record_id']:raise ValueError('Candidate identity differs')
    if validate_evidence(candidate,source['text'],protocol):raise ValueError('Candidate scientific evidence invalid')
    old_links=json.loads((base/'family_links.json').read_text())
    ids={r['record_id'] for r in baseline}
    old_links=[x for x in old_links if x['report_a'] in ids and x['report_b'] in ids]
    original_pool=json.loads((base/'synthesis.json').read_text())
    baseline_replay=synthesize(baseline,protocol['measure'],protocol['model'])
    if not same(original_pool,baseline_replay):raise ValueError('Baseline arithmetic differs')
    if not 1<=m['max_adapter_calls']<=12:raise ValueError('Bounded call budget required')
    output.mkdir(parents=True);atomic_json(output/'baseline_audit.json',baseline_audit)
    receipts=[]
    def call(prompt,schema):
        if len(receipts)>=m['max_adapter_calls']:raise ValueError('Call budget exhausted')
        phase=output/'model'/str(len(receipts)+1);receipts.append({'status':'started'})
        atomic_json(output/'calls.json',receipts)
        value=model_json(prompt,schema,phase,model=m['model'],max_attempts=1,timeout=300)
        requests=list(phase.glob('*/request.json'))
        if len(requests)!=1:raise ValueError('Unexpected request count')
        receipts[-1]=verify_entry(requests[0].parent,model=m['model'],backend='codex')
        atomic_json(output/'calls.json',receipts);return value
    seeds = None
    if m['policy'] == REPAIR_POLICY:
        previous=Path(m['previous_attempt'])
        for path in previous.rglob('*'):
            if path.is_file() and str(path) not in m['files_sha256']:
                raise ValueError('Previous attempt not fully pinned')
        previous_manifest=json.loads((previous/'manifest.json').read_text())
        if any(previous_manifest[k]!=m[k] for k in ('baseline','candidate_directory','baseline_record_ids','candidate_record_id','family_policy')):
            raise ValueError('Previous scientific input set differs')
        for path,checksum in previous_manifest['files_sha256'].items():
            if m['files_sha256'].get(path)!=checksum:raise ValueError('Previous input pins differ')
        if not (previous/'run/completion.json').exists():raise ValueError('Previous attempt incomplete/uncertain')
        old_calls=[]
        for folder in sorted((previous/'run/model').iterdir(),key=lambda x:int(x.name)):
            requests=list(folder.glob('*/request.json'))
            if len(requests)!=1:raise ValueError('Previous request ambiguous')
            path=requests[0];verify_entry(path.parent,model=m['model'],backend='codex')
            old_calls.append((json.loads(path.read_text()),json.loads((path.parent/'parsed.json').read_text())))
        index=0
        def replay_pair(prompt,schema):
            nonlocal index
            request,value=old_calls[index];index+=1
            if request['prompt']!=prompt or request['schema']!=schema:raise ValueError('Prior pair request differs')
            return value
        seeds=[]
        for row in baseline:
            rid=row['record_id'];text=json.loads((base/'sources'/rid/'text.json').read_text())['text']
            seeds+=adjudicate([row,candidate],{rid:text,candidate['record_id']:source['text']},replay_pair,max_pairs=1)
        if index!=len(old_calls) or seeds!=json.loads((previous/'run/new_family_links.json').read_text()):
            raise ValueError('Prior pair result replay differs')
        atomic_json(output/'prior_pair_replay.json',{'requests':len(old_calls),'verified':True})
    new_links=[]
    for row in baseline:
        rid=row['record_id'];document=json.loads((base/'sources'/rid/'text.json').read_text())
        if seeds is None:
            links=adjudicate([row,candidate],{rid:document['text'],candidate['record_id']:source['text']},call,max_pairs=1)
        else:
            from scripts.family_quote_repair import repair_link
            seed=next(x for x in seeds if x['report_a']==rid and x['report_b']==candidate['record_id'])
            links=[repair_link(seed,(document['text'],source['text']),call)]
        new_links+=links;atomic_json(output/'new_family_links.json',new_links)
    full=complete_set(baseline,candidate,old_links,new_links)
    atomic_json(output/'family_resolution.json',full)
    pool=synthesize(full['rows'],protocol['measure'],protocol['model']) if full['supported'] else None
    atomic_json(output/'sensitivity.json',pool)
    result={'policy':m['policy'],'scope':m['scope'],'baseline_record_ids':m['baseline_record_ids'],
            'candidate_record_id':candidate['record_id'],'baseline_synthesis':baseline_replay,
            'sensitivity_synthesis':pool,'candidate_replay':replay,'calls':receipts,
            'family_policy_new_pairs':FAMILY_POLICY,'existing_baseline_links_unchanged':True,
            'complete_updated_review':False,'historical_reproduction':False,
            'code_sha256':m['code_sha256'],'model':m['model'],'supported':full['supported']}
    verify_pins();atomic_json(output/'result.json',result)
    atomic_json(output/'completion.json',{'supported':full['supported'],'pins_unchanged':True,'new_adapter_calls':len(receipts),'new_pooled_analyses':int(pool is not None)})
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--output',required=True);a=p.parse_args()
    print(json.dumps(run(a.manifest,a.output),indent=2))

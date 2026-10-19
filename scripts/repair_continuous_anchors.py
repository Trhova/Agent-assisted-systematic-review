"""Source-only exact quotation repair for a preserved continuous extraction."""
import argparse
import copy
import json
import sys
from pathlib import Path

from scripts.autonomous_review import HEADER, VERIFY, validate_evidence
from scripts.continuous_derivations import derive
from scripts.family_adjudication import contains
from scripts.import_model_cache import verify_entry
from scripts.model_backend import atomic_json, digest, model_json
from scripts.primary_image_queue import sha

POLICY = 'continuous_exact_anchor_repair_v1'
FIELDS = ('evidence', 'dispersion_evidence_treatment', 'denominator_evidence_treatment',
          'dispersion_evidence_control', 'denominator_evidence_control')
SCHEMA = {'type':'object','additionalProperties':False,'required':list(FIELDS),
          'properties':{k:{'type':'array','items':{'type':'string'}} for k in FIELDS}}


def repair(original, proposal, source):
    if set(proposal) != set(FIELDS):
        raise ValueError('Only all five quotation fields may be repaired')
    result = copy.deepcopy(original)
    for key in FIELDS:
        quotes = proposal[key]
        if not isinstance(quotes,list) or not quotes or any(
            not isinstance(q,str) or not q.strip() or not contains(source,q) for q in quotes
        ):
            raise ValueError('Every quotation must match the exact source apart from whitespace')
        result[key] = copy.deepcopy(quotes)
    return result


def prior_candidate(request, parsed, source, protocol, record_id):
    if protocol.get('measure') not in {'MD','SMD'} or any(protocol.get(k) for k in ('summary_policy','multiarm_policy')):
        raise ValueError('Basic continuous source candidate required')
    scientific = {k:v for k,v in protocol.items() if k not in ('id','frozen_on','query','search_date_note')}
    prompt = request['prompt']
    if source not in prompt or ('\nPROTOCOL:\n'+json.dumps(scientific)+'\nBIBLIOGRAPHIC METADATA:\n') not in prompt:
        raise ValueError('Prior request must bind identical scientific contract and source')
    metadata=json.JSONDecoder().raw_decode(prompt.split('\nBIBLIOGRAPHIC METADATA:\n',1)[1])[0]
    if str(metadata.get('id')) != str(record_id):
        raise ValueError('Prior bibliographic record identity differs')
    if parsed.get('eligibility') != 'include' or len(parsed.get('rows',[])) != 1:
        raise ValueError('Exactly one preserved eligible candidate required')
    candidate = parsed['rows'][0]
    if not set(FIELDS) <= candidate.keys():
        raise ValueError('Original dispersion and denominator evidence required')
    return copy.deepcopy(candidate)


def run(manifest, output):
    m=json.loads(Path(manifest).read_text());output=Path(output)
    if m.get('policy')!=POLICY or not m.get('model','').strip() or m.get('backend')!='codex':
        raise ValueError('Explicit supported policy/model/backend required')
    if getattr(sys,'_asr_frozen_code',None)!=m['code_sha256']:
        raise ValueError('Frozen execution required')
    if output.exists():
        raise ValueError('New output required; reconcile uncertain submissions')
    def pinned(path):
        if str(path) not in m['files_sha256'] or sha(path)!=m['files_sha256'][str(path)]:
            raise ValueError('Required source/contract/request pin differs')
        return Path(path)
    for path in m['files_sha256']:
        pinned(path)
    doc=json.loads(pinned(m['source']).read_text());protocol=json.loads(pinned(m['protocol']).read_text())
    if digest(doc['text'])!=doc['sha256']:
        raise ValueError('Source text identity differs')
    prior=Path(m['prior_request'])
    for f in prior.iterdir():
        if f.is_file():
            pinned(f)
    prior_receipt=verify_entry(prior,model=m['model'],backend=m['backend'])
    request=json.loads((prior/'request.json').read_text());parsed=json.loads((prior/'parsed.json').read_text())
    original=prior_candidate(request,parsed,doc['text'],protocol,m['record_id'])
    output.mkdir(parents=True);receipts=[]
    def call(prompt,schema):
        if len(receipts)>=2:
            raise ValueError('Two adapter invocation budget exhausted')
        phase=output/'model'/str(len(receipts)+1)
        receipts.append({'status':'started'});atomic_json(output/'calls.json',receipts)
        value=model_json(prompt,schema,phase,model=m['model'],max_attempts=1,timeout=300)
        entries=list(phase.glob('*/request.json'))
        if len(entries)!=1:
            raise ValueError('Unexpected request count')
        receipts[-1]=verify_entry(entries[0].parent,model=m['model'],backend=m['backend'])
        atomic_json(output/'calls.json',receipts)
        return value
    proposal=call(HEADER+' Repair ONLY the five quotation arrays for this fixed continuous candidate. Use short contiguous literal snippets as they occur in SOURCE; separate fragments when intervening column text interrupts a sentence. Preserve punctuation, hyphenation and reading order. Do not add page labels, concatenate nonadjacent text, change scientific values or invent support. Empty arrays if unsupported. The next verifier must establish meaning, not only string matching.\nCANDIDATE:\n'+json.dumps(original)+'\nSOURCE:\n'+doc['text'],SCHEMA)
    atomic_json(output/'quote_proposal.json',proposal)
    errors=[];row=None;verification=None
    try:
        row=repair(original,proposal,doc['text']);row['record_id']=m['record_id']
        row=derive(row,doc['text'],protocol,doc['sha256'])
        errors=validate_evidence(row,doc['text'],protocol)
    except ValueError as error:
        errors.append(str(error))
    if not errors:
        verification=call(HEADER+' Independently verify EVERY scientific field against the entire original source and contract. Check eligible population/intervention/comparator, individual parallel randomization, actual arm-specific analyzed N, outcome and unit, endpoint versus change, original dispersion SD/SE and scope, selected timepoint, and exact evidence interpretation. Table rows need their population/header/footnote context. Separate literal narrative snippets do not establish that they belong together; inspect intervening text and reject ambiguous reconstruction. PP versus ITT populations and missing follow-up limitations must remain explicit. Any unsupported field or conflicting denominator requires valid=false. Verify deterministic SE-to-SD derivation only when explicitly authorized and supported.\nCONTRACT:\n'+json.dumps(protocol)+'\nCANDIDATE:\n'+json.dumps(row)+'\nSOURCE:\n'+doc['text'],VERIFY)
        atomic_json(output/'verification.json',verification)
        if not verification.get('valid') or verification.get('problems'):
            errors.append('Complete scientific verification failed')
    for path in m['files_sha256']:
        pinned(path)
    result={'policy':POLICY,'model':m['model'],'code_sha256':m['code_sha256'],
            'original_row':original,'row':row,'verification':verification,'validation_errors':errors,
            'source_input_supported':not errors,'accepted_for_pooling':False,'pooled':False,
            'pending_gates':['current publication integrity','historical eligibility/chronology confirmation','independence against every contributing trial','versioned review continuation'],
            'prior_request_receipt':prior_receipt,'request_receipts':receipts,'pins_unchanged':True,
            'scope':'Exact-source repair only; original review decisions unchanged; same-model errors may correlate.'}
    atomic_json(output/'result.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--output',required=True);a=p.parse_args()
    print(json.dumps(run(a.manifest,a.output),indent=2))

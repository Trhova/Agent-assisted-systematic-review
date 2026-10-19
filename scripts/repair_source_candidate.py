"""Bounded exact-anchor repair of a preserved candidate; no numerical pooling."""
import argparse
import copy
import json
import sys
from pathlib import Path

from scripts.autonomous_review import (
    HEADER,
    VERIFY,
    publication_integrity_flags,
    validate_evidence,
)
from scripts.continuous_derivations import derive
from scripts.family_adjudication import adjudicate, contains
from scripts.import_model_cache import verify_entry
from scripts.model_backend import atomic_json, digest, model_json
from scripts.primary_image_queue import sha
from scripts.report_chronology import assess
from scripts.trial_families import resolve

POLICY = 'exact_candidate_anchor_repair_v1'
QUOTES = {'type':'object','additionalProperties':False,'required':['evidence'],
          'properties':{'evidence':{'type':'array','items':{'type':'string'}}}}


def repair_evidence(original, proposal, source):
    """Only evidence can change; never silently discard an invalid quote."""
    if set(proposal) != {'evidence'} or not isinstance(proposal['evidence'], list):
        raise ValueError('Evidence-only repair required')
    if not proposal['evidence'] or any(not isinstance(q,str) or not contains(source,q) for q in proposal['evidence']):
        raise ValueError('Every repaired anchor must match exact source apart from whitespace')
    row = copy.deepcopy(original)
    row['evidence'] = proposal['evidence']
    return row


def gate_errors(row, source, protocol, verification, integrity, historical, updated, links, expected_pairs):
    errors = validate_evidence(row, source, protocol)
    if not verification.get('valid') or verification.get('problems'):
        errors.append('Independent candidate verification failed')
    if integrity:
        errors.append('Publication integrity unresolved')
    if historical.get('status') != 'after_cutoff' or updated.get('status') != 'on_or_before_cutoff':
        errors.append('Explicit post-cutoff addendum chronology not established')
    actual = {frozenset((x['report_a'],x['report_b'])) for x in links}
    if actual != {frozenset(p) for p in expected_pairs} or any(
        x['relationship'] != 'same_trial' or not x.get('independently_verified') for x in links
    ):
        errors.append('Declared companion family not independently established')
    return errors


def run(manifest, output):
    m = json.loads(Path(manifest).read_text()); output = Path(output)
    if m.get('policy') != POLICY or not m.get('model','').strip() or m.get('backend') != 'codex':
        raise ValueError('Explicit supported policy/model/backend required')
    if getattr(sys,'_asr_frozen_code',None) != m['code_sha256']:
        raise ValueError('Frozen execution required')
    if output.exists():
        raise ValueError('New output required; reconcile uncertain submissions')
    pins = m['files_sha256']
    def pinned(path):
        if str(path) not in pins or sha(path) != pins[str(path)]:
            raise ValueError('Required pinned input changed or absent')
        return Path(path)
    for path in pins:
        pinned(path)
    protocol = json.loads(pinned(m['protocol']).read_text())
    doc = json.loads(pinned(m['source']).read_text())
    if digest(doc['text']) != doc['sha256']:
        raise ValueError('Source text identity differs')
    prior = Path(m['prior_request'])
    for f in prior.iterdir():
        if f.is_file():
            pinned(f)
    prior_receipt = verify_entry(prior,model=m['model'],backend=m['backend'])
    old = json.loads((prior/'parsed.json').read_text())
    request = json.loads((prior/'request.json').read_text())
    if doc['text'] not in request['prompt'] or json.dumps(protocol) not in request['prompt']:
        raise ValueError('Prior request does not bind identical source and scientific contract')
    if old['eligibility'] != 'include' or len(old['rows']) != 1:
        raise ValueError('Exactly one previously eligible proposed candidate required')
    original = old['rows'][0]
    if protocol.get('summary_policy') or protocol.get('multiarm_policy') or protocol.get('measure') == 'RR':
        raise ValueError('Only basic continuous candidate supported')
    chronology = m['chronology']
    for key in ('html','receipt'):
        pinned(chronology[key])
    historical = assess(chronology['html'],chronology['receipt'],m['record']['doi'],chronology['historical_cutoff'])
    updated = assess(chronology['html'],chronology['receipt'],m['record']['doi'],chronology['updated_cutoff'])
    records = json.loads(pinned(m['integrity_records']).read_text())
    if {r['id'] for r in records} != set(m['family_sources']):
        raise ValueError('Integrity metadata must cover all declared family reports')
    documents = {}
    for rid,path in m['family_sources'].items():
        d = json.loads(pinned(path).read_text())
        if digest(d['text']) != d['sha256']:
            raise ValueError('Family source text identity differs')
        documents[rid] = d['text']
    if documents[m['record']['id']] != doc['text']:
        raise ValueError('Candidate family source differs')
    integrity = [{'record_id':r['id'],'flags':publication_integrity_flags(r)} for r in records]
    flags = [r for r in integrity if r['flags']]
    if not 2 <= m['max_adapter_calls'] <= 12:
        raise ValueError('Bounded call budget required')
    output.mkdir(parents=True)
    receipts = []
    def call(prompt,schema):
        if len(receipts) >= m['max_adapter_calls']:
            raise ValueError('Frozen adapter invocation budget exhausted')
        phase = output/'model'/str(len(receipts)+1)
        # Count invocation before submission; uncertain failure cannot be retried here.
        receipts.append({'status':'started'})
        atomic_json(output/'calls.json',receipts)
        value = model_json(prompt,schema,phase,model=m['model'],max_attempts=1,timeout=300)
        paths = list(phase.glob('*/request.json'))
        if len(paths) != 1:
            raise ValueError('Unexpected request count')
        receipts[-1] = verify_entry(paths[0].parent,model=m['model'],backend=m['backend'])
        atomic_json(output/'calls.json',receipts)
        return value
    proposal = call(HEADER+' Repair only evidence quotations for this fixed candidate. Return separate short contiguous verbatim snippets as they appear in SOURCE. Preserve literal reading order, punctuation and hyphenation. Do not join sentence fragments across intervening column text; use multiple snippets instead. No page labels or added quotation marks. If support is unavailable return an empty array. Scientific values cannot change.\nCANDIDATE:\n'+json.dumps(original)+'\nSOURCE:\n'+doc['text'],QUOTES)
    atomic_json(output/'quote_proposal.json',proposal)
    row = repair_evidence(original,proposal,doc['text'])
    row['record_id'] = m['record']['id']
    if protocol.get('dispersion_policy'):
        row = derive(row,doc['text'],protocol,doc['sha256'])
    verification = call(HEADER+' Independently verify every scientific field against the original source, not merely the quotation strings. Verify exact treatment/control, analyzed within-arm N, mean, SE versus SD, unadjusted arm-mean scope, units, timepoint, fasting outcome, endpoint versus change and parallel design. For deterministic dispersion_audit verify original SE and N and SD=SE*sqrt(N). Evidence snippets can be separate due PDF column order; do not infer missing numbers or methods. Any unsupported field or conflicting denominator requires valid=false.\nCONTRACT:\n'+json.dumps(protocol)+'\nCANDIDATE:\n'+json.dumps(row)+'\nSOURCE:\n'+doc['text'],VERIFY)
    atomic_json(output/'verification.json',verification)
    ids = sorted(documents)
    links = adjudicate([{'record_id':rid} for rid in ids],documents,call,max_pairs=3)
    pairs = [(a,b) for i,a in enumerate(ids) for b in ids[i+1:]]
    errors = gate_errors(row,doc['text'],protocol,verification,flags,historical,updated,links,pairs)
    family = resolve([row]) if not errors else {'rows':[],'unresolved':errors}
    result = {'policy':POLICY,'row':row,'original_evidence':original['evidence'],
              'validation_errors':errors,'input_supported':not errors,
              'historical_chronology':historical,'updated_chronology':updated,
              'integrity_metadata':integrity,'integrity_scope':'Indexed metadata snapshot only; absence of a flag is not proof of no misconduct.',
              'family_links':links,'quantitative_family_resolution':family,
              'report_family_ids':ids,'independent_effect_count':len(family['rows']),
              'accepted_for_pooling':False,'pooled':False,
              'scope':'One post-cutoff companion input; no complete updated search, other-trial independence or review reproduction claimed.',
              'prior_request_receipt':prior_receipt,'calls':receipts,'model':m['model'],'code_sha256':m['code_sha256']}
    atomic_json(output/'result.json',result)
    for path in pins:
        pinned(path)
    atomic_json(output/'completion.json',{'input_supported':not errors,'calls':len(receipts),'pins_unchanged':True,'numerical_runs':0})
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--output',required=True);a=p.parse_args()
    print(json.dumps(run(a.manifest,a.output),indent=2))

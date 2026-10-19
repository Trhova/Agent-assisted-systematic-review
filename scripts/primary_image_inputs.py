"""Opt-in pixel-grounded binary input admission; existing study/family gates remain."""
import argparse
import json
from pathlib import Path

from scripts.binary_outcomes import POLICY as BINARY
from scripts.binary_outcomes import counts
from scripts.import_model_cache import verify_entry
from scripts.model_backend import atomic_json, digest, model_json
from scripts.primary_image_queue import sha
from scripts.verify_reference_source import STATE, TEXT, obj

POLICY = 'primary_binary_image_inputs_v2'
SUPPORTED = {'primary_binary_image_inputs_v1', POLICY}
FIELDS = ('events_treatment', 'n_treatment', 'events_control', 'n_control')
AXES = ('cells', 'denominators', 'arms', 'outcome', 'timepoint', 'population', 'individual_parallel_design', 'source_identity', 'locator')
READ = obj({**{k: {'type': ['integer', 'null']} for k in FIELDS},
    'legible': {'type': 'boolean'}, 'treatment_label': TEXT, 'control_label': TEXT,
    'outcome_label': TEXT, 'timepoint_label': TEXT, 'pixel_locator': TEXT,
    'denominator_locator': TEXT, 'design_quote': TEXT,
    'limitations': {'type': 'array', 'items': TEXT}})
CHECK = obj({'assessments': obj({k: STATE for k in AXES}),
    'blocking_problems': {'type': 'array', 'items': TEXT},
    'limitations': {'type': 'array', 'items': TEXT}})


def norm(s):
    return ' '.join(s.split())


def load_manifest(path):
    m = json.loads(Path(path).read_text())
    if m.get('policy') not in SUPPORTED or not m.get('model', '').strip() or m.get('backend') != 'codex':
        raise ValueError('Explicit supported policy/model/backend required')
    for p, h in m['files_sha256'].items():
        if sha(p) != h: raise ValueError('Pinned evidence changed')
    for key in ('source', 'pdf', 'image', 'context', 'protocol', 'render_receipt'):
        if m[key] not in m['files_sha256']: raise ValueError('Required evidence is not pinned')
    doc = json.loads(Path(m['source']).read_text())
    if digest(doc['text']) != doc['sha256'] or sha(m['pdf']) != doc['pdf_sha256']:
        raise ValueError('Primary PDF/text identity differs')
    if not doc.get('identity', {}).get('verified'): raise ValueError('Unverified primary identity')
    provenance = doc['import_provenance']
    if str(provenance['record']['id']) != m['record_id']: raise ValueError('Primary report identity differs')
    folder = Path(m['source']).parent
    receipt_path = (folder/provenance['receipt_relative_path']).resolve()
    if str(receipt_path) not in m['files_sha256'] or sha(receipt_path) != provenance['receipt_sha256']:
        raise ValueError('Acquisition receipt missing or changed')
    acquisition = json.loads(receipt_path.read_text())
    selection = doc.get('page_selection')
    raw_path = (folder/selection['collection_relative_path']).resolve() if selection else Path(m['pdf'])
    if str(raw_path) not in m['files_sha256'] or acquisition.get('status') != 200 or acquisition['sha256'] != sha(raw_path):
        raise ValueError('Original acquisition chain differs')
    if selection and selection['collection_sha256'] != sha(raw_path): raise ValueError('Collection chain differs')
    render = json.loads(Path(m['render_receipt']).read_text())
    if render['pdf_sha256'] != sha(m['pdf']) or render['image_sha256'] != sha(m['image']) or render['page'] != m['page'] or render['crop'] != 'full_page':
        raise ValueError('Pixel/PDF locator chain differs')
    if type(m['page']) is not int or m['page'] < 1: raise ValueError('Invalid page')
    # Reproduce original page pixels, not merely two unrelated checksum claims.
    import io

    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(m['pdf'])
    image = pdf[m['page']-1].render(scale=render['scale']).to_pil()
    buf = io.BytesIO(); image.save(buf, format='PNG'); pdf.close()
    import hashlib
    if hashlib.sha256(buf.getvalue()).hexdigest() != sha(m['image']): raise ValueError('Pixels do not reproduce from original page')
    if selection:
        collection = pdfium.PdfDocument(raw_path)
        original = collection[selection['first_page'] + m['page'] - 2].render(scale=render['scale']).to_pil()
        parent_buf = io.BytesIO(); original.save(parent_buf, format='PNG'); collection.close()
        if parent_buf.getvalue() != buf.getvalue(): raise ValueError('Derived page differs from original collection')
    context = json.loads(Path(m['context']).read_text())
    if not context['segments']: raise ValueError('Primary methods context required')
    for segment in context['segments']:
        if context.get('parser') == 'pypdf_content_stream_v1':
            if m['policy'] != POLICY: raise ValueError('Revised context needs versioned policy')
            import pypdf
            if context.get('parser_version') != pypdf.__version__ or context.get('pdf_sha256') != sha(m['pdf']):
                raise ValueError('Context parser/source identity differs')
            if type(segment.get('page')) is not int or segment['page'] < 1: raise ValueError('Context page required')
            expected = pypdf.PdfReader(m['pdf']).pages[segment['page']-1].extract_text()
            if segment['text'] != expected: raise ValueError('Context differs from original PDF content stream')
            if segment['locator'] != f"Original report PDF page {segment['page']}": raise ValueError('Context page locator differs')
        elif not segment['locator'] or not norm(segment['text']) or norm(segment['text']) not in norm(doc['text']):
            raise ValueError('Context is not exact primary source text')
    protocol = json.loads(Path(m['protocol']).read_text())
    if protocol.get('image_input_policy') != m['policy'] or protocol.get('measure') != 'RR':
        raise ValueError('Explicit binary image admission contract required')
    return m, doc, context, protocol


def prompts(m, context, protocol, proposal=None):
    common = '\nFROZEN OUTCOME CONTRACT:\n'+json.dumps(protocol)+'\nORIGINAL PRIMARY METHODS CONTEXT:\n'+json.dumps(context)+'\nSOURCE LOCATOR: original report PDF page '+str(m['page'])+'; full page, no crop.'
    if proposal is None:
        return ('Read explicitly printed binary participant outcome counts from the original table image. Use outcome-specific arm denominators, not header randomized N unless explicitly applicable. Do not infer integers from percentages, digitize plotted marks, infer missing values or use adjusted OR as counts. Return null for unsupported values. Label pixel readings as visual observations, not textual quotations. Supply an exact design quotation from the provided original methods context. No external review or previous extracted values are supplied.'+common)
    return ('Independently inspect original pixels and primary context against the proposed reading. Every axis must be supported: exact event and denominator cells, arm direction, specified outcome/timepoint/population, individually randomized parallel design, identity and locators. Correct integers alone cannot resolve ambiguous semantics. Unsupported or unreadable evidence blocks admission. Report contextual limitations separately; do not infer missing data. Same-model correlated errors remain possible.'+common+'\nPROPOSAL:\n'+json.dumps(proposal))


def adjudicate(proposal, check, context):
    errors = list(check['blocking_problems'])
    if not proposal['legible']: errors.append('Image not legible')
    for axis in AXES:
        if check['assessments'].get(axis) != 'supported': errors.append('Unsupported '+axis)
    for key in ('treatment_label','control_label','outcome_label','timepoint_label','pixel_locator','denominator_locator'):
        if not proposal[key].strip(): errors.append('Missing '+key)
    quote = norm(proposal['design_quote'])
    if not quote or not any(quote in norm(x['text']) for x in context['segments']): errors.append('Design quote absent from original context')
    try: counts(proposal)
    except ValueError as e: errors.append(str(e))
    return errors


def row_from(m, protocol, proposal):
    return {**{k: proposal[k] for k in FIELDS}, 'record_id': m['record_id'],
        'study_id': m['record_id'], 'design': 'parallel', 'outcome': protocol['outcome'],
        'unit': protocol['unit'], 'value_type': BINARY,
        'timepoint_reported': proposal['timepoint_label'], 'evidence': [proposal['design_quote']],
        'event_components_treatment': [], 'event_components_control': [],
        'image_observations': {k: proposal[k] for k in ('treatment_label','control_label','outcome_label','pixel_locator','denominator_locator')},
        'limitations': proposal['limitations']}


def replay(manifest, output):
    m, doc, context, protocol = load_manifest(manifest); output = Path(output)
    proposal = json.loads((output/'proposal.json').read_text()); check = json.loads((output/'verification.json').read_text())
    receipts = []
    for phase, value, schema, prompt in [('read',proposal,READ,prompts(m,context,protocol)), ('verify',check,CHECK,prompts(m,context,protocol,proposal))]:
        entries = list((output/phase).glob('*/request.json'))
        if len(entries) != 1: raise ValueError('Exactly one request per phase required')
        path = entries[0]; request = json.loads(path.read_text())
        receipt = verify_entry(path.parent, model=m['model'], backend=m['backend'])
        if json.loads((path.parent/'parsed.json').read_text()) != value: raise ValueError('Saved reading differs from response')
        if request['prompt'] != prompt or request['schema'] != schema or [a['sha256'] for a in request.get('images',[])] != [sha(m['image'])]:
            raise ValueError('Request does not bind frozen source/contract/image')
        receipts.append(receipt)
    errors = adjudicate(proposal,check,context)
    return {'policy': m['policy'], 'admitted': not errors, 'errors': errors,
        'row': row_from(m,protocol,proposal) if not errors else None,
        'manifest_sha256': sha(manifest), 'source_text_sha256': doc['sha256'],
        'protocol_sha256': digest(protocol), 'request_receipts': receipts,
        'scope': 'Evidence input admission only; eligibility, integrity, family and pooling gates still required.',
        'limitations': check['limitations']+['Same-model procedural verification is not independent human expertise.']}


def validate_row(row, source, protocol):
    try:
        pointer = row['image_admission']; result = replay(pointer['manifest'],pointer['output'])
        if not result['admitted']: raise ValueError('Image input not admitted')
        if result['manifest_sha256'] != pointer['manifest_sha256'] or result['source_text_sha256'] != digest(source) or result['protocol_sha256'] != digest(protocol):
            raise ValueError('Image admission source/contract differs')
        clean = {k:v for k,v in row.items() if k != 'image_admission'}
        if clean != result['row']: raise ValueError('Image-admitted row changed')
        return []
    except (ValueError,KeyError,OSError,IndexError) as e:
        return ['Image evidence invalid: '+str(e)]


def run(manifest, output):
    m, _, context, protocol = load_manifest(manifest); output = Path(output)
    if output.exists(): raise ValueError('New output required; reconcile uncertain submissions')
    import sys
    if getattr(sys, '_asr_frozen_code', None) != m['code_sha256']: raise ValueError('Run through exact frozen code command')
    output.mkdir(parents=True)
    proposal = model_json(prompts(m,context,protocol), READ, output/'read', model=m['model'], images=[Path(m['image'])], max_attempts=1, timeout=300)
    atomic_json(output/'proposal.json',proposal)
    check = model_json(prompts(m,context,protocol,proposal), CHECK, output/'verify', model=m['model'], images=[Path(m['image'])], max_attempts=1, timeout=300)
    atomic_json(output/'verification.json',check)
    result = replay(manifest,output); atomic_json(output/'admission.json',result)
    if result['admitted']:
        row = {**result['row'], 'image_admission': {'manifest':str(Path(manifest).resolve()),'output':str(output.resolve()),'manifest_sha256':sha(manifest)}}
        atomic_json(output/'input_row.json',row)
        from scripts.autonomous_review import validate_evidence
        source = json.loads(Path(m['source']).read_text())['text']
        errors = validate_evidence(row,source,protocol)
        atomic_json(output/'consumer_validation.json', {'errors':errors,'accepted_input':not errors,'pooling_performed':False})
        if errors: raise ValueError('Normal input validator rejected admission')
    atomic_json(output/'completion.json', {'admitted':result['admitted'],'adapter_calls':2,'numerical_runs':0,'pins_unchanged':True})
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(run(a.manifest,a.output),indent=2))

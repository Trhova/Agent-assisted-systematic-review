"""Replay source-verification receipts against exact image request artifacts."""
import json
from pathlib import Path
from scripts.import_model_cache import verify_entry
from scripts.model_backend import digest
from scripts.evaluate_contract import sha
from scripts.verify_reference_source import adjudicate, adjudicate_v2


def validate_receipt(receipt_path, manifest_path):
    import unicodedata
    def norm(text):return ' '.join(unicodedata.normalize('NFKC',text).split())
    receipt_path,manifest_path=Path(receipt_path),Path(manifest_path)
    receipt=json.loads(receipt_path.read_text());m=json.loads(manifest_path.read_text())
    if m.get('policy') == 'reference_original_text_verification_v1':
        from scripts.verify_reference_text import validate_receipt as validate_text
        return validate_text(receipt_path, manifest_path)
    if receipt.get('manifest_sha256')!=sha(manifest_path):raise ValueError('Reference manifest binding differs')
    for path,h in m['files_sha256'].items():
        if sha(path)!=h:raise ValueError('Verification source changed')
    if receipt.get('source_sha256')!=m['files_sha256']:raise ValueError('Receipt source map differs')
    root=receipt_path.parent;results=[];verified=[]
    for phase,name in [('blind','blind.json'),('verify','verification.json')]:
        entries=list((root/phase).glob('*/request.json'))
        if len(entries)!=1:raise ValueError('Unexpected reference request count')
        folder=entries[0].parent;verified.append(verify_entry(folder,model=m['model'],backend='codex'))
        request=json.loads(entries[0].read_text())
        if request.get('images')!=[{'sha256':sha(m['image']),'modality':'image/png'}]:raise ValueError('Source image binding differs')
        parsed=json.loads((folder/'parsed.json').read_text());saved=json.loads((root/name).read_text())
        if digest(parsed)!=digest(saved):raise ValueError('Saved verification differs from actual model response')
        results.append(parsed)
    if verified!=receipt.get('request_receipts'):raise ValueError('Response provenance differs')
    reference=json.loads(Path(m['reference']).read_text());mapping=json.loads(Path(m['contract']).read_text())['mapping']
    import hashlib
    if receipt.get('cell_reference_sha256')!=sha(m['reference']) or receipt.get('mapping_sha256')!=hashlib.sha256(json.dumps(mapping,sort_keys=True).encode()).hexdigest():raise ValueError('Reference or mapping binding differs')
    v2=m['policy']=='reference_source_verification_v2'
    replay=(adjudicate_v2 if v2 else adjudicate)(*results,reference,mapping)
    source=norm(Path(m['review_text']).read_text()+'\n'+'\n'.join(Path(x['text']).read_text() for x in m['primary_context']))
    if v2:source+=' '+norm(Path(m['supplement_text']).read_text())
    for row in results[1]['row_checks']:
        if not norm(row['mapping_evidence']) or norm(row['mapping_evidence']) not in source:replay['problems'].append('mapping_quote_not_found:'+row['record_id'])
    replay['valid']=not replay['problems']
    if replay['valid'] is not receipt.get('valid') or replay['problems']!=receipt.get('problems'):raise ValueError('Reference verification decision replay differs')
    return {'valid':replay['valid'],'problems':replay['problems'],'receipt_sha256':sha(receipt_path),'model':m['model'],'request_count':len(verified),'limitation':'Separate requests from the same model; correlated errors remain possible.'}

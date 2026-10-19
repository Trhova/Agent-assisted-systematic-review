"""Versioned read-only evaluation; source traceability is not verification accuracy."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.audit_run import audit as artifact_audit
from scripts.benchmark_input_audit import audit as cell_audit
from scripts.model_backend import atomic_json

POLICY = 'evaluator_input_contract_v2'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot(run):
    return {str(p): sha(p) for p in Path(run).rglob('*') if p.is_file()}


def claims(comparison, cells, mapping_complete, trust, scope, integrity):
    """Separate observed agreement from independently verified evidence."""
    numerical = comparison.get('numerically_matches') is True and comparison.get('semantic_agreement', {}).get('agrees') is True
    coverage = not comparison.get('missing_studies', ['unknown']) and not comparison.get('extra_studies', ['unknown']) and comparison.get('k_observed') == comparison.get('k_expected')
    input_status = ('not_assessed' if cells is None else
                    'disagreement_in_transcribed_cells' if not cells['all_reported_cells_agree'] else
                    'agreement_in_transcribed_cells')
    verified = trust == 'independently_verified' and mapping_complete and cells is not None
    inputs_agree = cells['all_reported_cells_agree'] if verified else None
    reproduced = bool(integrity and numerical and coverage and verified and inputs_agree and comparison.get('reproduced') is True)
    return dict(numerical_agreement=numerical, report_coverage_agreement=coverage,
                trial_arm_time_mapping='complete' if mapping_complete else 'unresolved',
                reference_evidence_trust=trust, input_observation=input_status,
                verified_input_agreement=inputs_agree,
                verified_contributor_agreement=coverage if verified else None,
                scoped_reproduction=reproduced,
                complete_review_reproduction='not_established',
                prospective_validation='not_established', evaluation_scope=scope,
                reproduced=reproduced)


def evaluate(run, contract_path):
    run, contract_path = Path(run).resolve(), Path(contract_path).resolve()
    before = snapshot(run)
    c = json.loads(contract_path.read_text())
    if c.get('policy') != POLICY:
        raise ValueError('Unsupported evaluator policy')
    if c.get('scope') not in {'published_subgroup_development', 'whole_review_development'}:
        raise ValueError('Explicit supported development scope required')
    required = {'status.json', 'protocol.json', 'accepted.json', 'benchmark_comparison.json', 'trial_families.json', 'family_links.json', 'synthesis.json'}
    if not required <= c.get('run_sha256', {}).keys():
        raise ValueError('Missing frozen run pins')
    for name, expected in c['run_sha256'].items():
        path=(run/name).resolve()
        if not path.is_relative_to(run) or sha(path) != expected:
            raise ValueError('Frozen run checksum differs: '+name)
    status=json.loads((run/'status.json').read_text())
    if status.get('status') not in {'complete','incomplete','failed'}:
        raise ValueError('Source run must be finished')
    comparison=json.loads((run/'benchmark_comparison.json').read_text())
    accepted=json.loads((run/'accepted.json').read_text())
    mapping=c.get('mapping', [])
    ids=[str(x['record_id']) for x in mapping]
    families=[x['reference_trial_id'] for x in mapping]
    if len(ids)!=len(set(ids)) or len(families)!=len(set(families)):
        raise ValueError('Ambiguous report/family mapping')
    observed={str(x['record_id']):x for x in accepted}
    if len(observed)!=len(accepted):
        raise ValueError('Repeated accepted report requires explicit arm resolution')
    mapping_complete=set(ids)==set(observed) and bool(mapping)
    for item in mapping:
        row=observed.get(str(item['record_id']))
        keys=('study_id','timepoint_reported','treatment','control')
        if not row or any(not item.get(k) or item[k]!=row.get(k) for k in keys) or not item.get('reference_locator'):
            mapping_complete=False
    cells=None
    trust='unverified'
    validated=None
    ref=c.get('cell_reference')
    if ref:
        if sha(ref['path']) != ref['sha256']:
            raise ValueError('Frozen cell reference checksum differs')
        cells=cell_audit(run, ref['path'])
        trust='manual_transcription_unverified'
        verification=c.get('independent_verification')
        if verification:
            if sha(verification['path'])!=verification['sha256']:
                raise ValueError('Verification receipt checksum differs')
            v=json.loads(Path(verification['path']).read_text())
            if c.get('model_verification_manifest'):
                from scripts.validate_reference_receipt import validate_receipt
                manifest=c['model_verification_manifest']
                if sha(manifest['path'])!=manifest['sha256']:
                    raise ValueError('Model verification manifest checksum differs')
                validated=validate_receipt(verification['path'],manifest['path'])
            if (validated and validated['valid']
                and v.get('policy') == 'reference_original_text_verification_v1'
                and v.get('reference_sha256') == ref['sha256']
                and v.get('mapping_canonical_sha256') == hashlib.sha256(json.dumps(mapping,sort_keys=True).encode()).hexdigest()):
                trust='independently_verified'
            # This is a supplied evidence attestation, never inferred from a hash.
            if (v.get('policy')=='independent_reference_cells_v1' and v.get('valid') is True
                and v.get('cell_reference_sha256')==ref['sha256']
                and v.get('mapping_sha256')==hashlib.sha256(json.dumps(mapping,sort_keys=True).encode()).hexdigest()
                and v.get('independent_reviewer') and v.get('method') and v.get('evidence_locator')):
                if validated and validated['valid']:
                    trust='independently_verified'
                elif not c.get('model_verification_manifest') and not v.get('request_receipts'):
                    trust='independently_verified'
                # Model receipts require actual request/response/source replay, not just attestation.
    integrity=artifact_audit(run)
    result=claims(comparison,cells,mapping_complete,trust,c['scope'],integrity['valid'])
    result.update(policy=POLICY, run=str(run),contract_sha256=sha(contract_path),
                  scientific_code_sha256=status.get('code_sha256'),
                  cell_reconciliation=cells,artifact_integrity=integrity,
                  verification_receipt_validation=validated,
                  legacy_comparator_reproduced=comparison.get('reproduced'),
                  limitations=['Independent verification is an explicit supplied attestation, not independently guaranteed by this evaluator.',
                               'No whole-review or prospective-validation claim is established by this development contract.',
                               'Mappings and published cells remain evaluator-only; accepted scientific inputs are never changed.'])
    result['source_run_unchanged']=before==snapshot(run)
    if not result['source_run_unchanged']:
        raise ValueError('Source run changed during evaluation')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run');p.add_argument('contract');p.add_argument('--output',required=True);a=p.parse_args()
    out=Path(a.output).resolve()
    if out.exists() or out.is_relative_to(Path(a.run).resolve()):
        raise ValueError('Use a new output outside preserved run')
    atomic_json(out,evaluate(a.run,a.contract))

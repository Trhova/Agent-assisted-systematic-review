"""Read-only binary-cell reconciliation; rounded pooled agreement is insufficient."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.binary_outcomes import counts
from scripts.model_backend import atomic_json

FIELDS = ('events_treatment', 'n_treatment', 'events_control', 'n_control')


def reconcile(observed, reference):
    def index(rows):
        result = {}
        for row in rows:
            rid = str(row['record_id'])
            if rid in result:
                raise ValueError('Ambiguous repeated report identity; resolve trial/arm mapping first')
            counts(row)
            result[rid] = row
        return result
    actual, expected = index(observed), index(reference)
    differences = [{'record_id': rid, 'field': field,
                    'observed_primary_input': actual[rid][field], 'published_input': expected[rid][field]}
                   for rid in sorted(actual.keys() & expected.keys()) for field in FIELDS
                   if actual[rid][field] != expected[rid][field]]
    missing, extra = sorted(expected.keys()-actual.keys()), sorted(actual.keys()-expected.keys())
    return {'differences': differences, 'missing_from_run': missing, 'extra_in_run': extra,
            'all_reported_cells_agree': bool(expected) and not (differences or missing or extra),
            'limitations': ['Reference cells are separately transcribed published evidence; this comparison does not independently validate that transcription.',
                           'Cell agreement alone does not establish eligible population, timing, trial independence, risk of bias or review completeness.',
                           'Disagreement is retained without choosing reference or primary values to force numerical agreement.']}


def audit(run, reference_path):
    run, reference_path = Path(run), Path(reference_path)
    inputs = [run/'status.json', run/'protocol.json', run/'accepted.json', reference_path]
    before = {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}
    status = json.loads((run/'status.json').read_text())
    if status.get('status') not in {'complete','incomplete','failed'}:
        raise ValueError('Source run must be finished')
    protocol = json.loads((run/'protocol.json').read_text())
    ref = json.loads(reference_path.read_text())
    if ref.get('policy') != 'published_binary_input_audit_v1':
        raise ValueError('Unsupported cell reference policy')
    for key in ('outcome','unit','value_type','measure','model'):
        if key not in ref or ref[key] != protocol.get(key):
            raise ValueError('Reference semantic mismatch: '+key)
    if ref['measure'] != 'RR' or ref['value_type'] != 'binary_rr_mh_fixed_v1':
        raise ValueError('Only supported binary participant cells can be reconciled')
    evidence = ref['published_evidence']
    if hashlib.sha256(Path(evidence['path']).read_bytes()).hexdigest()!=evidence['sha256']:
        raise ValueError('Published evidence checksum differs')
    accepted = json.loads((run/'accepted.json').read_text())
    result = reconcile(accepted,ref['rows'])
    result.update(policy=ref['policy'],run=str(run.resolve()),reference=str(reference_path.resolve()),
                  input_sha256=before, published_evidence=evidence,
                  source_run_unchanged=all(hashlib.sha256(f.read_bytes()).hexdigest()==before[str(f)] for f in inputs))
    if not result['source_run_unchanged']:
        raise ValueError('Audit inputs changed during read-only reconciliation')
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');p.add_argument('reference');p.add_argument('--output',required=True);a=p.parse_args()
    output=Path(a.output).resolve()
    if output.is_relative_to(Path(a.run).resolve()) or output.exists():
        raise ValueError('Use new output outside preserved run')
    atomic_json(output,audit(a.run,a.reference))

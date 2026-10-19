"""Exercise new reports on preserved real runs; verify every original file."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.model_backend import atomic_json, digest
from scripts.outcome_availability import export
from scripts.report_review import export as review_export
from scripts.run_frozen import bundle


def hashes(run):
    return {str(p.relative_to(run)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(run.rglob('*')) if p.is_file()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', default='benchmarks/audits/outcome_availability_v1.json')
    p.add_argument('--output', default='data/benchmarks/outcome_availability_v1')
    args = p.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('Experiment output already exists; preserve the previous observation')
    config = json.loads(Path(args.config).read_text())
    output.mkdir(parents=True)
    _, code = bundle('scripts', 'data/benchmarks/code_bundles')
    atomic_json(output / 'configuration.json', {'configuration': config, 'configuration_sha256': digest(config), 'code_sha256': code,
                                               'experiment_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    results = []
    for case in config['cases']:
        run = Path(case['run'])
        before = hashes(run)
        report = export(run, output / case['id'] / 'availability')
        review_export(run, output / case['id'] / 'review_export')
        after = hashes(run)
        atomic_json(output / case['id'] / 'original_hashes.json', before)
        if after != before:
            raise RuntimeError('Preserved original run changed during reporting')
        results.append({'id': case['id'], 'original_files_unchanged': len(before),
                        'counts': report['counts'], 'continuation_records': [q['record_id'] for q in report['continuation_queue']],
                        'run_status_unchanged': report['run_status_unchanged'],
                        'numerical_decisions_unchanged': True})
    atomic_json(output / 'results.json', {'code_sha256': code, 'cases': results,
                                        'scope': 'Actual read-only exports, not new clinical reproduction or adjudication'})
    print(json.dumps(results))


if __name__ == '__main__':
    main()

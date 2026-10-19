"""Prespecified exact binary complement; never impute missing event status."""
import copy
import re

from scripts.model_backend import digest

POLICY = 'binary_known_status_complement_v1'


def schema(base):
    result = copy.deepcopy(base)
    row = result['properties']['rows']['items']
    fields = {'opposite_events': {'type': 'integer'}, 'known_status_n': {'type': 'integer'},
              'complete_binary_partition': {'type': 'boolean'},
              'opposite_event_definition': {'type': 'string'}, 'target_event_definition': {'type': 'string'},
              'population_and_timepoint': {'type': 'string'},
              'evidence': {'type': 'array', 'items': {'type': 'string'}}}
    item = {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}
    for arm in ('treatment', 'control'):
        key = 'complement_' + arm
        row['properties'][key] = {'anyOf': [{'type': 'null'}, item]}
        row['required'].append(key)
    return result


INSTRUCTIONS = '''PRESPECIFIED EXACT BINARY COMPLEMENT: set complement_treatment/control=null for directly reported target counts. If ONLY the opposite event count is reported, supply its original integer and the explicitly supported same-population/same-timepoint denominator with known binary status, complete_binary_partition=true only if source evidence supports exhaustion of those two categories, exact definitions and quotations. Target events may be null; deterministic code computes known_status_n minus opposite_events. Never subtract from randomized/baseline N unless source establishes that precise outcome population and complete observed binary status. Missing status, different timepoints, overlapping categories or percentage rounding prohibit conversion. Do not invert an RR to reverse event definition. Include all denominator/follow-up limitations. Independent verifier must check the partition, not just arithmetic.'''


def derive(row, source, protocol, source_hash):
    if protocol.get('binary_complement_policy') != POLICY or protocol.get('measure') != 'RR':
        raise ValueError('Exact complement requires prespecified binary policy')
    output = copy.deepcopy(row)
    audit = {}
    norm = lambda text: re.sub(r'\s+', ' ', text).strip()
    for arm in ('treatment', 'control'):
        spec = row.get('complement_' + arm)
        if spec is None:
            continue
        n, opposite = spec['known_status_n'], spec['opposite_events']
        if type(n) is not int or type(opposite) is not int or not 0 <= opposite <= n or n <= 0:
            raise ValueError('Invalid original complement integers')
        if n != row.get('n_' + arm) or spec['complete_binary_partition'] is not True:
            raise ValueError('Complement denominator/partition not established')
        if row.get('event_components_' + arm):
            raise ValueError('Cannot combine partition sum and complement')
        if any(not spec.get(k, '').strip() for k in ('opposite_event_definition', 'target_event_definition', 'population_and_timepoint')):
            raise ValueError('Missing complement outcome/population/time semantics')
        if not spec['evidence'] or any(not q.strip() or norm(q) not in norm(source) for q in spec['evidence']):
            raise ValueError('Complement evidence absent from source')
        target = n - opposite
        if row.get('events_' + arm) not in (None, target):
            raise ValueError('Proposed target count differs from exact complement')
        output['events_' + arm] = target
        audit[arm] = {'original': spec, 'derived_events': target, 'transformation': 'known_status_n - opposite_events',
                      'source_sha256': source_hash, 'policy': POLICY, 'original_sha256': digest(spec)}
    output['complement_audit'] = audit
    return output

import copy

import pytest

from scripts.summary_derivations import POLICY, derive, estimate


def test_published_metafor_quartile_example():
    # External reference example, not values from the target benchmark.
    mean, sd = estimate(4, 6, 10, 20)
    assert mean == pytest.approx(6.719500)
    assert sd == pytest.approx(4.787076, abs=1e-6)


@pytest.mark.parametrize('args', [(4, 6, 10, 4), (4, 6, 10, True), (6, 4, 10, 20), (4, 4, 4, 20), (4, float('nan'), 10, 20)])
def test_rejects_unidentifiable_or_invalid_summaries(args):
    with pytest.raises(ValueError):
        estimate(*args)


def fixture_row():
    row = {'unit': 'days', 'value_type': 'endpoint'}
    for arm in ('treatment', 'control'):
        row.update({f'{k}_{arm}': v for k, v in dict(n=20, mean=None, sd=None, q1=4, median=6, q3=10, summary_type='median_IQR', summary_evidence=['Median 6 (IQR 4–10)'], denominator_evidence=['Analyzed n=20'], source_locator='Table 2').items()})
    return row


def test_derived_values_preserve_originals_and_require_opt_in():
    row = fixture_row()
    original = copy.deepcopy(row)
    source = 'Analyzed n=20. Median 6 (IQR 4–10)'
    result = derive(row, source, {'summary_policy': POLICY}, 'a'*64)
    assert row == original
    assert result['summary_audit'][0]['original_statistics']['mean'] is None
    assert result['summary_audit'][0]['estimated'] is True
    assert result['summary_audit'][0]['source_sha256'] == 'a'*64
    with pytest.raises(ValueError):
        derive(row, source, {}, 'a'*64)
    row['denominator_evidence_treatment'] = ['Randomized n=20']
    with pytest.raises(ValueError):
        derive(row, source, {'summary_policy': POLICY}, 'a'*64)


def test_quote_repair_does_not_change_statistics_or_hide_rejections():
    from scripts.summary_derivations import derive_with_quote_repair

    row = fixture_row()
    row['summary_evidence_treatment'] = ['Table 2: Median 6 (IQR 4–10)']
    calls = []

    def call(prompt, schema):
        calls.append(prompt)
        return {f: (['Median 6 (IQR 4–10)', 'invented quote'] if f.startswith('summary') else ['Analyzed n=20']) for f in schema['required']}

    result = derive_with_quote_repair(row, 'Analyzed n=20. Median 6 (IQR 4–10)', {'summary_policy': POLICY}, 'a'*64, call)
    assert len(calls) == 1
    assert result['mean_treatment'] == pytest.approx(6.7195)
    assert result['discarded_transformation_evidence']['summary_evidence_treatment'] == ['invented quote']
    assert row['summary_evidence_treatment'] == ['Table 2: Median 6 (IQR 4–10)']


def test_mixed_arm_summary_definitions_are_outside_this_policy():
    row = fixture_row()
    row['summary_type_control'] = 'mean_SD'
    with pytest.raises(ValueError, match='Mixed arm'):
        derive(row, 'Analyzed n=20. Median 6 (IQR 4–10)', {'summary_policy': POLICY}, 'a'*64)

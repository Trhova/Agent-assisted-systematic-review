import statistics

import pytest

from scripts.multiarm import POLICY, combine, comparison


def arm(id, values, role="treatment"):
    return {
        "arm_id": id,
        "n": len(values),
        "mean": statistics.mean(values),
        "sd": statistics.stdev(values),
        "independently_verified": True,
        "evidence": ["fixture raw observations"],
        "study_id": "trial",
        "outcome": "ALT",
        "unit": "U/L",
        "value_type": "endpoint",
        "timepoint_reported": "12 weeks",
        "role": role,
    }


def test_combined_variance_matches_actual_disjoint_observations():
    a = [1, 2, 6]
    b = [9, 11, 13, 20]
    result = combine([arm("a", a), arm("b", b)])
    assert result["n"] == 7
    assert result["mean"] == pytest.approx(statistics.mean(a + b))
    assert result["sd"] == pytest.approx(statistics.stdev(a + b))


def test_control_used_once_and_policy_required():
    arms = [arm("a", [1, 2, 3]), arm("b", [3, 5, 8]), arm("c", [8, 9, 10], "control")]
    result = comparison(arms, POLICY, "Independently randomized disjoint groups")
    assert result["n_treatment"] == 6 and result["n_control"] == 3
    with pytest.raises(ValueError, match="prespecified"):
        comparison(arms, None, "supported")
    with pytest.raises(ValueError, match="both sides"):
        comparison(arms + [arms[-1]], POLICY, "supported")

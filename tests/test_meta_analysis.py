import math

import pytest

from scripts.meta_analysis import effect, pool, synthesize


def row(id="a", **changes):
    return dict(
        study_id=id,
        outcome="ALT",
        unit="U/L",
        value_type="endpoint",
        n_treatment=20,
        n_control=20,
        mean_treatment=10,
        mean_control=12,
        sd_treatment=2,
        sd_control=2,
        **changes,
    )


def test_known_fixed_result_and_homogeneity():
    a = effect(row())
    b = effect(row("b"))
    result = pool([a, b], "fixed")
    assert result["estimate"] == -2
    assert result["se"] == pytest.approx(math.sqrt(0.2))
    assert result["tau2"] == 0 and result["I2"] == 0


def test_random_effects_hand_calculation():
    a = effect(row())
    b = effect(row("b"))
    b["effect"] = 2
    r = pool([a, b], "random")
    assert r["Q"] == pytest.approx(20)
    assert r["tau2"] == pytest.approx(7.6)
    assert r["se"] == pytest.approx(2)
    assert r["I2"] == pytest.approx(95)


def test_standardized_effect_and_negative_sd():
    r = effect(row(), "SMD")
    assert r["effect"] == pytest.approx(-1 * (1 - 3 / 151))
    assert r["variance"] == pytest.approx(0.1 + r["effect"] ** 2 / (2 * (40 - 3.94)))
    invalid = row()
    invalid["sd_control"] = -1
    with pytest.raises(ValueError):
        effect(invalid)


def test_dependence_and_scale_rejected():
    a = effect(row())
    with pytest.raises(ValueError, match="Dependent"):
        pool([a, a])
    b = effect(row("b"))
    b["value_type"] = "change"
    with pytest.raises(ValueError, match="value_type"):
        pool([a, b])
    b = effect(row("b"))
    b["variance"] = float("nan")
    with pytest.raises(ValueError):
        pool([a, b])


def test_sensitivity_and_missing_sample_size():
    assert (
        len(synthesize([row("a"), row("b"), row("c")], "MD", "fixed")["leave_one_out"])
        == 3
    )
    r = row()
    r["n_control"] = None
    with pytest.raises(ValueError):
        effect(r)


def test_published_forest_recalculation_matches_revman_rounding():
    """Secondary-source regression, explicitly not independent reproduction."""
    import json
    from pathlib import Path

    fixture = json.loads(
        Path("benchmarks/references/li2016_fbg_forest.json").read_text()
    )
    rows = [
        {**r, "outcome": "FBG", "unit": "source units", "value_type": "endpoint"}
        for r in fixture["rows"]
    ]
    result = synthesize(rows, "SMD", "random")
    assert round(result["estimate"], 2) == -0.61
    assert round(result["ci_low"], 2) == -0.92
    assert round(result["ci_high"], 2) == -0.30
    assert round(result["I2"]) == 66

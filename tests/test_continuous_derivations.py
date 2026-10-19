import copy
import math

import pytest

from scripts.benchmark_validity import semantic_agreement
from scripts.continuous_derivations import (
    MIXED_MD,
    POLICY,
    allowed_value_types,
    derive,
    extraction_schema,
)
from scripts.meta_analysis import synthesize


def test_protocol_outcome_is_canonical_but_source_unit_is_preserved():
    from scripts.autonomous_review import EXTRACT

    schema = extraction_schema(EXTRACT, {"outcome": "ALT"})
    fields = schema["properties"]["rows"]["items"]["properties"]
    assert fields["outcome"]["enum"] == ["ALT"]
    assert (
        fields["unit"] == EXTRACT["properties"]["rows"]["items"]["properties"]["unit"]
    )
    assert "enum" not in EXTRACT["properties"]["rows"]["items"]["properties"]["outcome"]


def example():
    r = {
        "study_id": "a",
        "outcome": "FBG",
        "unit": "mg/dL",
        "value_type": "endpoint",
        "mean_treatment": 145.4,
        "mean_control": 163.3,
    }
    for a, v in [("treatment", 9.5), ("control", 12)]:
        r.update(
            {
                f"n_{a}": 27,
                f"sd_{a}": None,
                f"reported_dispersion_{a}": v,
                f"dispersion_type_{a}": "SE",
                f"dispersion_scope_{a}": "unadjusted_arm_mean",
                f"dispersion_evidence_{a}": ["Data are means ± SE."],
                f"denominator_evidence_{a}": ["27 per arm at week 8"],
                f"source_locator_{a}": "Table 3, week 8",
            }
        )
    return r


SOURCE = "Data are means ± SE. 27 per arm at week 8"
P = {"dispersion_policy": POLICY, "value_type": "endpoint", "measure": "SMD"}


def test_se_conversion_preserves_original_and_unequal_denominators():
    r = example()
    r["n_control"] = 18
    source = SOURCE + " Control 18 at week 8"
    r["denominator_evidence_control"] = ["Control 18 at week 8"]
    x = derive(r, source, P, "sourcehash")
    assert x["sd_treatment"] == pytest.approx(9.5 * math.sqrt(27))
    assert x["sd_control"] == pytest.approx(12 * math.sqrt(18))
    assert r["sd_control"] is None
    assert x["dispersion_audit"][1]["source_sha256"] == "sourcehash"
    assert x["dispersion_audit"][0]["original_value"] == 9.5


@pytest.mark.parametrize(
    "field,value",
    [
        ("dispersion_scope_treatment", "between_arm_difference"),
        ("dispersion_scope_treatment", "adjusted_estimate"),
        ("n_treatment", True),
        ("n_treatment", None),
        ("denominator_evidence_treatment", "not in source"),
        ("source_locator_treatment", ""),
        ("sd_treatment", 9.5),
    ],
)
def test_unsafe_derivation_rejected(field, value):
    r = example()
    r[field] = value
    with pytest.raises(ValueError):
        derive(r, SOURCE, P, "hash")


def test_frozen_protocol_rejects_se():
    with pytest.raises(ValueError, match="not prespecified"):
        derive(example(), SOURCE, {"value_type": "endpoint"}, "hash")


def test_explicit_md_policy_allows_change_preserves_semantics():
    a = example()
    a.update(sd_treatment=20, sd_control=20, outcome="ALT", unit="U/L")
    b = copy.deepcopy(a)
    b.update(study_id="b", value_type="change", mean_treatment=-20, mean_control=-2)
    with pytest.raises(ValueError, match="value_type"):
        synthesize([a, b], "MD", "fixed")
    x = synthesize([a, b], "MD", "fixed", value_type_policy=MIXED_MD)
    assert [r["value_type"] for r in x["effects"]] == ["endpoint", "change"]
    protocol = {
        "outcome": "ALT",
        "unit": "U/L",
        "value_type": MIXED_MD,
        "measure": "MD",
        "model": "fixed",
    }
    assert semantic_agreement(protocol, protocol, x)["agrees"]
    with pytest.raises(ValueError, match="MD"):
        synthesize([a, b], "SMD", "fixed", value_type_policy=MIXED_MD)
    with pytest.raises(ValueError):
        allowed_value_types({"value_type": MIXED_MD, "measure": "SMD"})


def test_quote_repair_is_bounded_and_cannot_change_statistics():
    from scripts.continuous_derivations import derive_with_quote_repair

    row = example()
    row["denominator_evidence_treatment"] = ["Page 3: 27 per arm at week 8"]
    calls = []

    def call(prompt, schema):
        calls.append(prompt)
        out = {f: example()[f] for f in schema["required"]}
        out["n_treatment"] = 999  # Even an extra backend field cannot modify numbers.
        return out

    result = derive_with_quote_repair(row, SOURCE, P, "hash", call)
    assert len(calls) == 1
    assert result["n_treatment"] == 27
    assert (
        result["original_transformation_evidence"]["denominator_evidence_treatment"]
        == row["denominator_evidence_treatment"]
    )
    assert result["sd_treatment"] == pytest.approx(9.5 * math.sqrt(27))


def test_quote_repair_missing_support_still_fails():
    from scripts.continuous_derivations import derive_with_quote_repair

    row = example()
    row["denominator_evidence_treatment"] = ["unsupported"]
    with pytest.raises(ValueError, match="evidence absent"):
        derive_with_quote_repair(
            row,
            SOURCE,
            P,
            "hash",
            lambda prompt, schema: {f: [] for f in schema["required"]},
        )


def test_quote_repair_retains_rejected_extras_without_accepting_them_as_evidence():
    from scripts.continuous_derivations import derive_with_quote_repair

    row = example()
    row["denominator_evidence_treatment"] = ["unsupported initial quote"]

    def call(prompt, schema):
        return {f: example()[f] + ["unsupported extra"] for f in schema["required"]}

    result = derive_with_quote_repair(row, SOURCE, P, "hash", call)
    for arm in ("treatment", "control"):
        field = "denominator_evidence_" + arm
        assert result[field] == ["27 per arm at week 8"]
        assert result["discarded_transformation_evidence"][field] == [
            "unsupported extra"
        ]
    assert result["n_treatment"] == 27

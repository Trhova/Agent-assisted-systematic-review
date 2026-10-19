import math
import pytest
from scripts.binary_outcomes import POLICY, counts, effect, extraction_schema, synthesize
from scripts.autonomous_review import EXTRACT, validate_evidence
from scripts.meta_analysis import synthesize as dispatch
from scripts.trial_families import resolve


def row(s, a, n1, c, n0):
    return dict(study_id=s, record_id=s, outcome="mortality", unit="dimensionless",
                value_type=POLICY, events_treatment=a, n_treatment=n1,
                events_control=c, n_control=n0, design="parallel",
                timepoint_reported="28 days", evidence=["primary evidence"])


def test_mh_hand_computed_two_stratum_example_and_dispatch():
    rows = [row("a", 1, 10, 2, 10), row("b", 4, 20, 2, 20)]
    result = dispatch(rows, "RR", "mantel_haenszel_fixed")
    assert result["estimate"] == pytest.approx(1.25)
    assert result["se"] ** 2 == pytest.approx(.39)
    assert result["weights"] == pytest.approx([.5, .5])
    assert result["ci_low"] == pytest.approx(math.exp(math.log(1.25)-1.95996398454*math.sqrt(.39)))
    reverse = synthesize([row(r["study_id"], r["events_control"], r["n_control"], r["events_treatment"], r["n_treatment"]) for r in rows], "mantel_haenszel_fixed")
    assert reverse["estimate"] == pytest.approx(1/result["estimate"])
    assert reverse["ci_high"] == pytest.approx(1/result["ci_low"])


@pytest.mark.parametrize("a,n1,c,n0", [(True,10,1,10), (1.5,10,1,10),(-1,10,1,10),(11,10,1,10),(1,0,1,10),(1,10,None,10)])
def test_invalid_counts_rejected(a,n1,c,n0):
    with pytest.raises(ValueError): counts(row("a",a,n1,c,n0))


def test_prespecified_zero_policy_retains_originals_and_noninformative_ledger():
    r = row("zero",0,10,2,10)
    e = effect(r)
    assert e["binary_audit"]["original_counts"] == [0,10,2,10]
    assert e["binary_audit"]["analysis_counts"] == [.5,11,2.5,11]
    result = synthesize([r,row("other",2,10,3,10),row("doublezero",0,20,0,20)],"mantel_haenszel_fixed")
    assert result["k"] == 2 and len(result["noninformative_studies"]) == 1
    with pytest.raises(ValueError,match="informative"):
        synthesize([r,row("doublezero",0,20,0,20)],"mantel_haenszel_fixed")


def test_binary_schema_validation_and_components():
    schema = extraction_schema(EXTRACT)["properties"]["rows"]["items"]
    assert "mean_treatment" not in schema["properties"]
    r = row("a",4,50,1,55);r["event_components_treatment"]=[3,1]
    protocol=dict(measure="RR", outcome="mortality", unit="dimensionless",value_type=POLICY)
    assert validate_evidence(r,"primary evidence",protocol) == []
    r["event_components_treatment"]=[3,2]
    assert any("components" in e for e in validate_evidence(r,"primary evidence",protocol))


def test_binary_family_counts_and_method_contract_not_silently_mixed():
    rows = [row("a",1,10,2,10),row("b",3,10,2,10)]
    rows[1]["study_id"]="a"
    assert resolve(rows)["unresolved"]
    with pytest.raises(ValueError,match="Dependent"):
        synthesize(rows,"mantel_haenszel_fixed")
    with pytest.raises(ValueError,match="policy"):
        synthesize(rows,"random")

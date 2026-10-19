import json

import pytest
from jsonschema import ValidationError

from scripts.autonomous_review import compare, flatten_xml, validate_evidence
from scripts.model_backend import atomic_json, digest, model_json


def test_jats_preserves_table_cells_and_omits_references():
    text = flatten_xml(
        "<article><body><sec><title>Results</title><table-wrap><table><tr><td>ALT</td><td>10 ± 2</td></tr></table></table-wrap></sec></body><back><ref-list>LEAKED REVIEW</ref-list></back></article>"
    )
    assert "ALT | 10 ± 2" in text
    assert "LEAKED" not in text


def test_evidence_and_design_guard():
    r = dict(
        evidence=["invented"],
        design="crossover",
        outcome="ALT",
        unit="U/L",
        value_type="endpoint",
        limitations=[],
    )
    for key in (
        "n_treatment",
        "n_control",
        "mean_treatment",
        "mean_control",
        "sd_treatment",
        "sd_control",
        "timepoint_weeks",
    ):
        r[key] = None
    errors = validate_evidence(
        r, "actual", dict(outcome="ALT", unit="U/L", value_type="endpoint")
    )
    assert len(errors) == 9


def test_incomplete_run_cannot_pass_benchmark(tmp_path):
    ref = dict(estimate=-2, ci_low=-3, ci_high=-1, k=4, absolute_tolerance=0.02)
    atomic_json(tmp_path / "ref.json", ref)
    atomic_json(tmp_path / "status.json", {"status": "incomplete"})
    atomic_json(tmp_path / "synthesis.json", ref)
    compare(tmp_path, tmp_path / "ref.json")
    assert (
        json.loads((tmp_path / "benchmark_comparison.json").read_text())["reproduced"]
        is False
    )


def test_cache_validated_and_bound_to_prompt(tmp_path):
    schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }
    req = {
        "prompt": "a",
        "schema": schema,
        "backend": "codex",
        "model": None,
        "version": 1,
    }
    atomic_json(tmp_path / digest(req) / "parsed.json", {"ok": True})
    assert model_json("a", schema, tmp_path) == {"ok": True}
    atomic_json(tmp_path / digest(req) / "parsed.json", {"bad": 1})
    with pytest.raises(ValidationError):
        model_json("a", schema, tmp_path)


@pytest.mark.parametrize("discover_extra", [False, True])
@pytest.mark.parametrize("integrity_flag", [False, True])
@pytest.mark.parametrize("fail_verification", [False, True])
@pytest.mark.parametrize("small_collection", [False, True])
def test_pipeline_fixture_runs_all_stages_without_reference_leakage(
    tmp_path,
    monkeypatch,
    discover_extra,
    integrity_flag,
    fail_verification,
    small_collection,
):
    import yaml

    import scripts.autonomous_review as runner

    protocol = {
        "id": "secret_reference_name",
        "query": "fixture",
        "eligibility": "parallel trials",
        "outcome": "ALT",
        "unit": "U/L",
        "value_type": "endpoint",
        "measure": "MD",
        "model": "fixed",
    }
    path = tmp_path / "protocol.yaml"
    path.write_text(yaml.safe_dump(protocol))
    records = [{"id": x, "title": x, "publication_types": []} for x in ("one", "two")]
    if integrity_flag:
        records[0]["publication_types"] = ["Retracted Publication"]
    collection = {"id": "collection", "title": "Proceedings", "publication_types": []}
    search_records = [collection, records[0]] if discover_extra else records
    monkeypatch.setattr(runner, "search", lambda p, w: {"records": search_records})

    def fulltext(record, work, model=None):
        if record["id"] == "collection":
            return {
                "text": "x" * (1000 if small_collection else 400001),
                "sha256": digest("x" * (1000 if small_collection else 400001)),
            }
        return {"text": record["id"] + " 10 12 2 20", "sha256": record["id"]}

    monkeypatch.setattr(runner, "fulltext", fulltext)
    if discover_extra:
        monkeypatch.setattr(
            "scripts.document_segments.triage",
            lambda *a, **kw: {
                "status": "triaged",
                "completed_segments": 1,
                "total_segments": 1,
                "candidates": [{"title": "two"}],
            },
        )
        monkeypatch.setattr(
            "scripts.resolve_candidates.resolve_candidates",
            lambda *a, **kw: {
                "records": [records[1]],
                "status": "resolved",
            },
        )

    def fake(prompt, schema, *args, **kwargs):
        assert "secret_reference_name" not in prompt
        if "records" in schema["properties"]:
            return {
                "records": [
                    {"id": rid, "decision": "include", "reason": "fixture"}
                    for rid in schema["properties"]["records"]["items"]["properties"][
                        "id"
                    ]["enum"]
                ]
            }
        if "relationship" in schema["properties"]:
            return {
                "relationship": "distinct_trials",
                "evidence_a": "one 10 12 2 20",
                "evidence_b": "two 10 12 2 20",
                "reason": "fixture distinct cohorts",
            }
        if "reason" in schema["properties"] and "valid" in schema["properties"]:
            return {"valid": True, "reason": "fixture verified"}
        if schema is runner.VERIFY:
            if fail_verification:
                raise TimeoutError("Verification unavailable")
            assert "Contextual reporting note" in prompt
            assert "PROTOCOL (also verify full eligibility" in prompt
            assert "FROZEN INDEXED BIBLIOGRAPHIC METADATA" in prompt
            assert "parallel trials" in prompt
            return {"valid": True, "problems": []}
        id = "one" if "one 10" in prompt else "two"
        if list(schema["properties"]) == ["evidence"]:
            return {"evidence": [id + " 10 12 2 20", "unsupported annotation"]}
        return {
            "eligibility": "include",
            "reason": "fixture",
            "missing": [],
            "rows": [
                dict(
                    study_id=id,
                    outcome="ALT",
                    unit="U/L",
                    value_type="endpoint",
                    timepoint_weeks=12,
                    timepoint_reported="12 weeks",
                    n_treatment=20,
                    n_control=20,
                    mean_treatment=10,
                    mean_control=12,
                    sd_treatment=2,
                    sd_control=2,
                    design="parallel",
                    treatment="A",
                    control="B",
                    evidence=["Page 1: " + id + " 10 12 2 20"],
                    limitations=["Contextual reporting note"],
                )
            ],
        }

    monkeypatch.setattr(runner, "model_json", fake)
    for record in records:
        atomic_json(
            tmp_path
            / "runs"
            / protocol["id"]
            / digest(protocol)[:12]
            / "sources"
            / record["id"]
            / "text.json",
            {"text": record["id"] + " 10 12 2 20"},
        )
    work, status = runner.run(path, tmp_path / "runs", "codex", None)
    if fail_verification:
        assert status["status"] == "incomplete"
        assert status["counts"]["accepted_effects"] == 0
        extracted = json.loads((work / "extractions.json").read_text())
        assert len(extracted) == len({x["id"] for x in extracted})
        assert status["counts"]["fulltexts_attempted"] == len(extracted)
        assert not (work / "synthesis.json").exists()
        return
    if integrity_flag:
        assert status["status"] == "incomplete"
        assert status["counts"]["independent_effects"] == 1
        assert not (work / "synthesis.json").exists()
        held = next(
            x
            for x in json.loads((work / "extractions.json").read_text())
            if x["id"] == "one"
        )
        assert held["status"] == "publication_integrity_unresolved"
        assert held["result"]["rows"]
        assert all(
            any(
                "Publication integrity unresolved" in e
                for e in row["validation_errors"]
            )
            for row in held["result"]["rows"]
        )
        assert held["publication_integrity_flags"] == ["Retracted Publication"]
        return
    assert status["status"] == "complete"
    assert json.loads((work / "synthesis.json").read_text())["estimate"] == -2
    assert "code_sha256" in status
    if discover_extra:
        assert status["counts"]["supplemental_records"] == 1
        assert status["counts"]["fulltexts_attempted"] == 3
    atomic_json(work / "rob2_draft.json", {"source_checked": 2})
    monkeypatch.setattr(runner, "fulltext", lambda r, w, model=None: None)
    _, retry = runner.run(path, tmp_path / "runs", "codex", None)
    assert retry["status"] == "incomplete"
    assert not (work / "synthesis.json").exists()
    assert not (work / "rob2_draft.json").exists()
    assert len(list((work / "attempts").glob("*/rob2_draft.json"))) == 1
    archives = list((work / "attempts").glob("*/synthesis.json"))
    assert len(archives) == 1
    assert json.loads(archives[0].read_text())["estimate"] == -2


def test_screening_repairs_duplicate_ids_without_silently_dropping_records():
    from scripts.autonomous_review import screen_batch

    calls = []

    def model(prompt, schema):
        calls.append(prompt)
        ids = ["a", "a"] if len(calls) == 1 else ["a", "b"]
        return {
            "records": [
                {"id": x, "decision": "unclear", "reason": "fixture"} for x in ids
            ]
        }

    result = screen_batch([{"id": "a"}, {"id": "b"}], "test eligibility", model)
    assert [r["id"] for r in result] == ["a", "b"]
    assert len(calls) == 2 and "Previous response" in calls[-1]


def test_enzyme_unit_alias_is_restricted_to_enzyme_activity():
    from scripts.autonomous_review import canonical_unit

    assert canonical_unit("ALT", "IU/L") == "U/L"
    assert canonical_unit("AST", "UI/L") == "U/L"
    assert canonical_unit("insulin", "IU/L") == "IU/L"


def test_jats_identity_rejects_wrong_article_even_with_valid_body():
    from scripts.autonomous_review import validate_jats_identity

    xml = '<article><front><article-meta><article-id pub-id-type="pmid">123</article-id></article-meta></front><body>Valid looking trial text</body></article>'
    assert validate_jats_identity({"id": "123"}, xml)["verified_identifiers"] == [
        "pmid"
    ]
    with pytest.raises(ValueError, match="does not match"):
        validate_jats_identity({"id": "456"}, xml)


def test_indexed_publication_integrity_flags_are_explicit_and_case_insensitive():
    from scripts.autonomous_review import publication_integrity_flags

    assert publication_integrity_flags(
        {"publication_types": ["Randomized Controlled Trial", "Retracted Publication"]}
    ) == ["Retracted Publication"]
    assert publication_integrity_flags(
        {"publication_types": ["Expression of Concern"]}
    ) == ["Expression of Concern"]
    assert (
        publication_integrity_flags({"publication_types": ["Published Erratum"]}) == []
    )


def test_resume_never_relabels_cached_decisions_as_new_protocol_or_model(tmp_path):
    from scripts.autonomous_review import validate_resume_context

    atomic_json(
        tmp_path / "initialization.json",
        {
            "execution_context": {
                "protocol_sha256": "frozen",
                "backend": "codex",
                "model": None,
            }
        },
    )
    atomic_json(tmp_path / "screening.json", [])
    validate_resume_context(tmp_path, "frozen", "codex", None)
    with pytest.raises(ValueError, match="fresh workdir"):
        validate_resume_context(tmp_path, "changed", "codex", None)
    with pytest.raises(ValueError, match="fresh workdir"):
        validate_resume_context(tmp_path, "frozen", "codex", "different-model")
    (tmp_path / "initialization.json").unlink()
    with pytest.raises(ValueError, match="lacks execution provenance"):
        validate_resume_context(tmp_path, "frozen", "codex", None)

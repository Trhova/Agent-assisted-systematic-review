import json
import sys
from pathlib import Path

import pytest

from scripts import verify_reference_text as v
from scripts.qualify_benchmark_method import sha


@pytest.fixture
def setup(tmp_path, monkeypatch):
    source = tmp_path / "review.txt"
    source.write_text("Trial A. Treated 4/20; control 5/21. day14.")
    reference = tmp_path / "ref.json"
    reference.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "record_id": "A",
                        "events_treatment": 4,
                        "n_treatment": 20,
                        "events_control": 5,
                        "n_control": 21,
                    }
                ]
            }
        )
    )
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps([{"record_id": "A"}]))
    protocol = tmp_path / "protocol.txt"
    protocol.write_text("day14 outcome")
    manifest = tmp_path / "manifest.json"
    m = {
        "policy": v.POLICY,
        "model": "gpt-6-astra",
        "code_sha256": "code",
        "review_text": str(source),
        "source_locator": "Table1 day14",
        "reference": str(reference),
        "mapping": str(mapping),
        "scientific_protocol": str(protocol),
        "primary_context": [],
        "files_sha256": {
            str(p): sha(p) for p in (source, reference, mapping, protocol)
        },
    }
    manifest.write_text(json.dumps(m))
    monkeypatch.setattr(sys, "_asr_frozen_code", "code", raising=False)
    calls = []

    def respond(prompt, schema, out, **kwargs):
        calls.append(prompt)
        folder = Path(out) / "request"
        folder.mkdir(parents=True)
        (folder / "request.json").write_text("{}")
        if len(calls) == 1:
            return {
                "text_readable": True,
                "treatment_header": "Treated",
                "control_header": "control",
                "rows": [
                    {
                        "label": "A",
                        "events_treatment": 4,
                        "n_treatment": 20,
                        "events_control": 5,
                        "n_control": 21,
                        "locator": "Table1 A",
                    }
                ],
                "limitations": [],
            }
        return {
            "blocking_problems": [],
            "observations": [],
            "row_checks": [
                {
                    "record_id": "A",
                    "image_label": "A",
                    "source_locator": "Table1 A",
                    "mapping_evidence": "Trial A.",
                    "assessments": {
                        x: "supported"
                        for x in v.CHECK_V2["properties"]["row_checks"]["items"][
                            "properties"
                        ]["assessments"]["properties"]
                    },
                }
            ],
            "limitations": [],
        }

    def fake(prompt, schema, out, **kwargs):
        result = respond(prompt, schema, out, **kwargs)
        folder = Path(out) / "request"
        (folder / "request.json").write_text(json.dumps({"prompt": prompt}))
        (folder / "parsed.json").write_text(json.dumps(result))
        return result

    monkeypatch.setattr(v, "model_json", fake)
    monkeypatch.setattr(v, "verify_entry", lambda *a, **k: {"verified_fixture": True})
    return manifest, tmp_path / "output", calls, reference


def test_text_only_blind_and_receipt(setup):
    manifest, out, calls, _ = setup
    r = v.run(manifest, out)
    assert r["valid"] and r["modality"] == "text" and len(calls) == 2
    assert "PROPOSED PUBLISHED CELLS" not in calls[0]
    assert "PROPOSED PUBLISHED CELLS" in calls[1]


def test_altered_cell_blocks_even_with_positive_verifier(setup):
    manifest, out, _, reference = setup
    r = json.loads(reference.read_text())
    r["rows"][0]["events_treatment"] = 8
    reference.write_text(json.dumps(r))
    m = json.loads(manifest.read_text())
    m["files_sha256"][str(reference)] = sha(reference)
    manifest.write_text(json.dumps(m))
    assert not v.run(manifest, out)["valid"]


def test_source_drift_blocks_before_calls(setup):
    manifest, out, calls, reference = setup
    reference.write_text("{}")
    with pytest.raises(ValueError):
        v.run(manifest, out)
    assert not calls


def test_wrong_code_blocks(setup, monkeypatch):
    manifest, out, calls, _ = setup
    monkeypatch.setattr(sys, "_asr_frozen_code", "different")
    with pytest.raises(ValueError):
        v.run(manifest, out)
    assert not calls


def test_omitted_consumed_pin_blocks(setup):
    manifest, out, calls, reference = setup
    m = json.loads(manifest.read_text())
    del m["files_sha256"][str(reference)]
    manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError):
        v.run(manifest, out)
    assert not calls


def test_receipt_replay_validates_actual_text_response(setup):
    manifest, out, _, _ = setup
    v.run(manifest, out)
    assert v.validate_receipt(out / "receipt.json", manifest)["valid"]
    saved = json.loads((out / "blind.json").read_text())
    saved["rows"][0]["events_treatment"] = 8
    (out / "blind.json").write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="model response"):
        v.validate_receipt(out / "receipt.json", manifest)


def test_receipt_replay_rejects_wrong_modality_or_context(setup):
    manifest, out, _, _ = setup
    v.run(manifest, out)
    p = out / "verify/request/request.json"
    request = json.loads(p.read_text())
    request["images"] = [{"sha256": "unseen"}]
    p.write_text(json.dumps(request))
    with pytest.raises(ValueError, match="modality"):
        v.validate_receipt(out / "receipt.json", manifest)
    request.pop("images")
    request["prompt"] = request["prompt"].replace("day14 outcome", "wrong contract")
    p.write_text(json.dumps(request))
    with pytest.raises(ValueError, match="context"):
        v.validate_receipt(out / "receipt.json", manifest)


def test_false_receipt_cannot_be_relabelled_valid(setup):
    manifest, out, _, reference = setup
    r = json.loads(reference.read_text());r["rows"][0]["events_treatment"] = 8
    reference.write_text(json.dumps(r))
    m = json.loads(manifest.read_text());m["files_sha256"][str(reference)] = sha(reference)
    manifest.write_text(json.dumps(m))
    assert not v.run(manifest, out)["valid"]
    p = out / "receipt.json";r = json.loads(p.read_text());r.update(valid=True, problems=[])
    p.write_text(json.dumps(r))
    with pytest.raises(ValueError, match="replay"):
        v.validate_receipt(p, manifest)


def test_receipt_rejects_changed_code_claim(setup):
    manifest, out, _, _ = setup
    v.run(manifest, out)
    p = out / "receipt.json";r = json.loads(p.read_text());r["code_sha256"] = "different"
    p.write_text(json.dumps(r))
    with pytest.raises(ValueError, match="code identity"):
        v.validate_receipt(p, manifest)

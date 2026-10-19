from pathlib import Path
from types import SimpleNamespace

import yaml

from scripts.benchmark_suite import suite
from scripts.model_backend import atomic_json, digest


def fixture(tmp_path):
    cases = []
    for name in ["first", "second"]:
        p = tmp_path / (name + ".yaml")
        protocol = {"id": name, "query": "frozen"}
        p.write_text(yaml.safe_dump(protocol))
        r = tmp_path / (name + ".json")
        reference = {
            "estimate": -1,
            "ci_low": -2,
            "ci_high": 0,
            "k": 2,
            "absolute_tolerance": 0.02,
        }
        atomic_json(r, reference)
        cases.append(
            {
                "id": name,
                "protocol": str(p),
                "protocol_sha256": digest(protocol),
                "reference": str(r),
                "reference_sha256": digest(reference),
            }
        )
    config = tmp_path / "suite.yaml"
    config.write_text(yaml.safe_dump({"id": "fixture", "cases": cases}))
    return config, cases


def test_orchestration_never_passes_reference_to_review_and_continues_failures(
    tmp_path, monkeypatch
):
    config, _cases = fixture(tmp_path)
    work = tmp_path / "runs"
    seen = []

    def run(command, **kwargs):
        assert all("reference" not in arg for arg in command)
        protocol = yaml.safe_load(
            Path(command[command.index("--protocol") + 1]).read_text()
        )
        seen.append(protocol["id"])
        directory = work / protocol["id"] / digest(protocol)[:12]
        atomic_json(
            directory / "status.json",
            {
                "status": "incomplete",
                "protocol_sha256": digest(protocol),
                "counts": {},
                "code_sha256": command[4],
            },
        )
        return SimpleNamespace(returncode=2)

    monkeypatch.setattr("scripts.benchmark_suite.subprocess.run", run)
    monkeypatch.setattr("scripts.rob2_draft.assess_run", lambda *a, **k: {})
    result = suite(config, work, model="test-pinned-model")
    assert seen == ["first", "second"]
    assert result["status"] == "not_reproduced"
    assert all(not c["reproduced"] for c in result["cases"])
    assert (work / "suite_report.md").exists()


def test_existing_evaluation_rejects_running_or_changed_reference(
    tmp_path, monkeypatch
):
    config, cases = fixture(tmp_path)
    mapping = {}
    for case in cases:
        run = tmp_path / case["id"]
        mapping[case["id"]] = str(run)
        atomic_json(
            run / "status.json",
            {
                "status": "running" if case["id"] == "first" else "incomplete",
                "protocol_sha256": case["protocol_sha256"],
            },
        )
    Path(cases[1]["reference"]).write_text("{}")
    monkeypatch.setattr(
        "scripts.benchmark_suite.subprocess.run",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("evaluation must not execute models")
        ),
    )
    result = suite(config, tmp_path / "evaluation", existing=mapping)
    assert "active review" in result["cases"][0]["error"]
    assert "reference checksum" in result["cases"][1]["error"]


def test_failed_launcher_cannot_reuse_stale_success(tmp_path, monkeypatch):
    config, cases = fixture(tmp_path)
    work = tmp_path / "runs"
    for case in cases:
        atomic_json(
            work / case["id"] / case["protocol_sha256"][:12] / "status.json",
            {"status": "complete", "protocol_sha256": case["protocol_sha256"]},
        )
    monkeypatch.setattr(
        "scripts.benchmark_suite.subprocess.run",
        lambda *a, **k: SimpleNamespace(returncode=2),
    )
    report = suite(config, work, model="test-pinned-model")
    assert all("fresh status" in c["error"] for c in report["cases"])
    assert not any(c["reproduced"] for c in report["cases"])


def test_invalid_evaluator_pins_prevent_any_model_submission(tmp_path, monkeypatch):
    import hashlib
    config, cases = fixture(tmp_path)
    cases[0]["reference_sha256"] = hashlib.sha256(
        Path(cases[0]["reference"]).read_bytes()
    ).hexdigest()  # Raw-file hash is not the canonical reference digest.
    cases[1]["evaluation_contract"] = cases[1]["reference"]
    cases[1]["evaluation_contract_sha256"] = "0" * 64
    config.write_text(yaml.safe_dump({"id": "bad-pins", "cases": cases}))
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid evaluator pin must stop before a model submission")
    monkeypatch.setattr("scripts.benchmark_suite.subprocess.run", forbidden)
    monkeypatch.setattr("scripts.rob2_draft.assess_run", forbidden)
    report = suite(config, tmp_path / "runs", model="explicit-test-model")
    assert "reference checksum" in report["cases"][0]["error"]
    assert "evaluation contract checksum" in report["cases"][1]["error"]

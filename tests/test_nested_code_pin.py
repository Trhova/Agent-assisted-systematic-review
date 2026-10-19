import subprocess

from scripts.run_frozen import bundle, command


def test_nested_cli_uses_pin_over_repository_cwd_and_rejects_tampering(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "__init__.py").write_text("")
    (source / "probe.py").write_text("print('PINNED')")
    root, identity = bundle(source, tmp_path / "bundles")
    cwd = tmp_path / "cwd"
    (cwd / "scripts").mkdir(parents=True)
    (cwd / "scripts" / "__init__.py").write_text("")
    (cwd / "scripts" / "probe.py").write_text("raise RuntimeError('WRONG PACKAGE')")
    argv = command(root, identity, "scripts.probe", [])
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)
    assert result.returncode == 0 and result.stdout.strip() == "PINNED"
    (root / "scripts" / "probe.py").write_text("print('TAMPERED')")
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)
    assert result.returncode != 0
    assert "TAMPERED" not in result.stdout
    assert "checksum differs" in result.stderr


def test_suite_code_pin_rejected_before_any_child(tmp_path, monkeypatch):
    import yaml

    from scripts.benchmark_suite import suite

    config = tmp_path / "suite.yaml"
    config.write_text(
        yaml.safe_dump({"prespecified_code_sha256": "wrong", "cases": []})
    )
    monkeypatch.setattr(
        "scripts.benchmark_suite.subprocess.run",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not launch")),
    )
    import pytest

    with pytest.raises(ValueError, match="code checksum"):
        suite(config, tmp_path / "run", model="explicit")


def test_child_drift_blocks_rob_and_evaluation(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import yaml

    from scripts.benchmark_suite import suite
    from scripts.model_backend import atomic_json, digest

    reference_path = tmp_path / "reference.json"
    atomic_json(reference_path, {})
    protocol = {"id": "case"}
    protocol_path = tmp_path / "protocol.yaml"
    protocol_path.write_text(yaml.safe_dump(protocol))
    config = tmp_path / "suite.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "id": "suite",
                "cases": [
                    {
                        "id": "case",
                        "protocol": str(protocol_path),
                        "protocol_sha256": digest(protocol),
                        "reference": str(reference_path),
                        "reference_sha256": digest({}),
                    }
                ],
            }
        )
    )
    work = tmp_path / "run"

    def child(*args, **kwargs):
        atomic_json(
            work / "case" / digest(protocol)[:12] / "status.json",
            {"status": "incomplete", "code_sha256": "wrong"},
        )
        return SimpleNamespace(returncode=2)

    def forbidden(*args, **kwargs):
        raise AssertionError("dependent call must not occur")

    monkeypatch.setattr("scripts.benchmark_suite.subprocess.run", child)
    monkeypatch.setattr("scripts.rob2_draft.assess_run", forbidden)
    monkeypatch.setattr("scripts.benchmark_suite.evaluate", forbidden)
    result = suite(config, work, model="explicit")
    assert "child code checksum differs" in result["cases"][0]["error"]

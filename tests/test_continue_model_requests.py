import fcntl
import json
from pathlib import Path

import pytest

from scripts.continue_model_requests import continue_one, failure
from scripts.model_backend import atomic_json, digest, request_identity


def setup(tmp_path):
    req = request_identity("prompt", {"type": "object"}, "codex", "pinned")
    key = digest(req)
    folder = tmp_path / "failed" / key
    atomic_json(folder / "request.json", req)
    atomic_json(
        folder / "1000000000.response.json",
        {
            "response_received_epoch": 1,
            "returncode": 1,
            "stdout": json.dumps(
                {"type": "turn.failed", "error": {"message": "503 Service Unavailable"}}
            ),
        },
    )
    policy = {
        "model": "pinned",
        "cooldown_seconds": 900,
        "max_outer_attempts": 1,
        "allow_new_adapter_calls": True,
    }
    return folder, req, policy


def success(target, req, value):
    folder = Path(target) / digest(req)
    atomic_json(folder / "request.json", req)
    atomic_json(folder / "parsed.json", value)
    atomic_json(
        folder / "2000000000.response.json",
        {
            "returncode": 0,
            "stdout": json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": json.dumps(value)},
                }
            ),
        },
    )


def test_confirmed_failure_recovers_once_and_reuses_across_output_dirs(tmp_path):
    folder, req, policy = setup(tmp_path)
    calls = []

    def adapter(prompt, schema, output, **kwargs):
        calls.append(kwargs)
        assert kwargs["max_attempts"] == 1
        success(output, req, {"valid": False, "problems": ["scientific rejection"]})

    ledger = tmp_path / "ledger"
    first = continue_one(
        folder, tmp_path / "a", policy, [], ledger, caller=adapter, now=lambda: 1000
    )
    second = continue_one(
        folder, tmp_path / "b", policy, [], ledger, caller=adapter, now=lambda: 1000
    )
    assert first["state"] == "recovered_verified_success"
    assert second["state"] == "reused_verified_success" and len(calls) == 1
    # Success is transport/schema success, never conversion of negative science.
    assert (
        json.loads((tmp_path / "b" / folder.name / "parsed.json").read_text())["valid"]
        is False
    )


def test_cooldown_retry_after_and_live_lock_block_submission(tmp_path):
    folder, req, policy = setup(tmp_path)
    p = folder / "1000000000.response.json"
    r = json.loads(p.read_text())
    r["headers"] = {"Retry-After": "2000"}
    atomic_json(p, r)

    def forbidden(*a, **k):
        raise AssertionError("must not submit")

    ledger = tmp_path / "ledger"
    assert (
        continue_one(
            folder,
            tmp_path / "a",
            policy,
            [],
            ledger,
            caller=forbidden,
            now=lambda: 1000,
        )["state"]
        == "deferred_cooldown"
    )
    with (ledger / (folder.name + ".lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        assert (
            continue_one(
                folder,
                tmp_path / "b",
                policy,
                [],
                ledger,
                caller=forbidden,
                now=lambda: 3000,
            )["state"]
            == "blocked_live_request"
        )


def test_uncertain_timeout_blocks_future_submission_even_new_output(tmp_path):
    folder, req, policy = setup(tmp_path)
    calls = []

    def timeout(*a, **k):
        calls.append(1)
        raise TimeoutError("unknown completion")

    ledger = tmp_path / "ledger"
    first = continue_one(
        folder, tmp_path / "a", policy, [], ledger, caller=timeout, now=lambda: 1000
    )
    second = continue_one(
        folder, tmp_path / "b", policy, [], ledger, caller=timeout, now=lambda: 99999
    )
    assert first["state"] == "blocked_uncertain_submission"
    assert (
        second["state"] == "blocked_uncertain_previous_submission" and len(calls) == 1
    )


def test_missing_receipt_schema_result_and_later_exception_not_retryable(tmp_path):
    folder, req, policy = setup(tmp_path)
    p = folder / "1000000000.response.json"
    p.unlink()
    assert not failure(folder)["retryable"]
    atomic_json(p, {"returncode": 0, "stdout": ""})
    assert not failure(folder)["retryable"]
    atomic_json(
        p,
        {
            "returncode": 1,
            "stdout": json.dumps({"type": "turn.failed", "error": {"message": "429"}}),
        },
    )
    atomic_json(folder / "3000000000.error.json", {"type": "TimeoutExpired"})
    assert failure(folder)["kind"] == "uncertain_later_exception"


def test_changed_request_and_forged_cache_rejected(tmp_path):
    folder, req, policy = setup(tmp_path)
    success(tmp_path / "success", req, {})
    atomic_json(tmp_path / "success" / folder.name / "parsed.json", {"forged": True})
    with pytest.raises(ValueError):
        continue_one(
            folder, tmp_path / "a", policy, [tmp_path / "success"], tmp_path / "ledger"
        )
    atomic_json(folder / "request.json", req | {"model": "other"})
    with pytest.raises(ValueError):
        continue_one(folder, tmp_path / "b", policy, [], tmp_path / "ledger")


def test_adapter_single_attempt_timeout_never_retries(tmp_path, monkeypatch):
    import subprocess

    from scripts.model_backend import model_json

    calls = []

    def timeout(*args, **kwargs):
        calls.append(1)
        raise subprocess.TimeoutExpired("codex", 300)

    monkeypatch.setattr("scripts.model_backend.subprocess.run", timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        model_json(
            "prompt",
            {"type": "object"},
            tmp_path / "model",
            model="pinned",
            max_attempts=1,
        )
    assert len(calls) == 1


def test_http_date_retry_after_uses_response_epoch(tmp_path):
    folder, req, policy = setup(tmp_path)
    p = folder / "1000000000.response.json"
    r = json.loads(p.read_text())
    r["headers"] = {"Retry-After": "Thu, 01 Jan 1970 00:33:21 GMT"}
    atomic_json(p, r)
    assert failure(folder)["retry_after_seconds"] == 2000


def test_terminal_permanent_error_not_masked_by_earlier_503(tmp_path):
    folder, req, policy = setup(tmp_path)
    p = folder / "1000000000.response.json"
    atomic_json(
        p,
        {
            "returncode": 1,
            "stdout": json.dumps({"type": "error", "message": "503 temporary"})
            + "\n"
            + json.dumps(
                {"type": "turn.failed", "error": {"message": "401 Unauthorized"}}
            ),
            "stderr": "retry503",
        },
    )
    assert not failure(folder)["retryable"]


def test_legacy_timing_uses_receipt_mtime_not_request_start(tmp_path):
    import os

    folder, req, policy = setup(tmp_path)
    p = folder / "1000000000.response.json"
    r = json.loads(p.read_text())
    r.pop("response_received_epoch")
    atomic_json(p, r)
    os.utime(p, (300, 300))
    assert failure(folder)["last_response_epoch"] == 300


def test_cache_only_mode_refuses_new_adapter_call(tmp_path, monkeypatch):
    from scripts.model_backend import model_json

    monkeypatch.setenv("ASR_MODEL_CACHE_ONLY", "1")

    def forbidden(*a, **k):
        raise AssertionError("network must not occur")

    monkeypatch.setattr("scripts.model_backend.subprocess.run", forbidden)
    with pytest.raises(RuntimeError, match="cache-only"):
        model_json("new prompt", {"type": "object"}, tmp_path / "cache", model="pinned")


def test_failed_retry_budget_survives_output_variation(tmp_path):
    folder, req, policy = setup(tmp_path)
    calls = []

    def fail(prompt, schema, target, **kwargs):
        calls.append(1)
        atomic_json(target / folder.name / "request.json", req)
        atomic_json(
            target / folder.name / "2000000000.response.json",
            {
                "returncode": 1,
                "response_received_epoch": 1000,
                "stdout": json.dumps(
                    {
                        "type": "turn.failed",
                        "error": {"message": "503 Service Unavailable"},
                    }
                ),
            },
        )
        raise RuntimeError("backend failed")

    ledger = tmp_path / "ledger"
    assert (
        continue_one(
            folder, tmp_path / "a", policy, [], ledger, caller=fail, now=lambda: 1000
        )["state"]
        == "failed_retry"
    )
    assert (
        continue_one(
            folder, tmp_path / "b", policy, [], ledger, caller=fail, now=lambda: 99999
        )["state"]
        == "blocked_retry_budget"
    )
    assert len(calls) == 1


def test_malformed_retry_after_blocks_automatic_resubmission(tmp_path):
    folder, req, policy = setup(tmp_path)
    p = folder / "1000000000.response.json"
    for bad in ["-1", "NaN", "0.5", "not a date"]:
        r = json.loads(p.read_text())
        r["headers"] = {"Retry-After": bad}
        atomic_json(p, r)
        assert failure(folder)["kind"] == "unparsed_retry_after"
        assert not failure(folder)["retryable"]

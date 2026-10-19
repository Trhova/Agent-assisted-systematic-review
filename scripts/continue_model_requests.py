"""Bounded, durable continuation of confirmed transient Codex request failures."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import re
import shutil
import time
from pathlib import Path

from scripts.import_model_cache import import_cache, verify_entry
from scripts.model_backend import atomic_json, digest, model_json


def file_hashes(root):
    root = Path(root)
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def failure(folder):
    folder = Path(folder)
    receipts = sorted(folder.glob("*.response.json"))
    if not receipts:
        return {"kind": "uncertain_no_response", "retryable": False}
    latest = receipts[-1]
    r = json.loads(latest.read_text())
    events = []
    for line in r.get("stdout", "").splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    if any(
        e.get("item", {}).get("type")
        in {"command_execution", "mcp_tool_call", "web_search"}
        for e in events
    ):
        return {"kind": "tool_policy_violation", "retryable": False}
    if r.get("returncode") == 0 or any(
        e.get("item", {}).get("type") == "agent_message" for e in events
    ):
        return {"kind": "scientific_or_validation_result", "retryable": False}
    terminal = [e for e in events if e.get("type") == "turn.failed"]
    terminal_error = json.dumps(terminal[-1].get("error", "")) if terminal else ""
    transient = bool(terminal) and bool(re.search(r"\b(?:429|503)\b", terminal_error))
    received = r.get("response_received_epoch")
    timing_basis = "response_received_epoch"
    if not isinstance(received, (int, float)):
        received = latest.stat().st_mtime
        timing_basis = "legacy_preserved_file_mtime_conservative"
    retry_after = r.get("retry_after_seconds")
    if retry_after is None:
        retry_after = r.get("headers", {}).get("Retry-After")
    try:
        import math

        seconds = float(retry_after or 0)
        if not math.isfinite(seconds) or seconds < 0 or not seconds.is_integer():
            raise ValueError("Invalid delay-seconds")
        retry_after = seconds
    except (TypeError, ValueError):
        from email.utils import parsedate_to_datetime

        try:
            retry_after = max(
                0,
                parsedate_to_datetime(str(retry_after)).timestamp() - received,
            )
        except (ValueError, TypeError, OverflowError):
            return {"kind": "unparsed_retry_after", "retryable": False}
    errors = sorted(folder.glob("*.error.json"))
    if errors and errors[-1].name.split(".")[0] > latest.name.split(".")[0]:
        return {"kind": "uncertain_later_exception", "retryable": False}
    return {
        "kind": "confirmed_transient_backend_failure"
        if transient
        else "unclassified_failure",
        "retryable": transient,
        "last_response_epoch": received,
        "retry_after_seconds": retry_after,
        "response": latest.name,
        "timing_basis": timing_basis,
        "terminal_error": terminal_error,
    }


def continue_one(
    folder,
    target,
    policy,
    success_roots,
    ledger_root,
    *,
    caller=model_json,
    now=time.time,
):
    folder, target, ledger_root = Path(folder), Path(target), Path(ledger_root)
    request = json.loads((folder / "request.json").read_text())
    key = digest(request)
    if (
        key != folder.name
        or request.get("model") != policy["model"]
        or request.get("backend") != "codex"
        or request.get("allow_web")
        or request.get("version") != 1
    ):
        raise ValueError("Request identity/model/backend/tool contract differs")
    ledger_root.mkdir(parents=True, exist_ok=True)
    with (ledger_root / (key + ".lock")).open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"request_sha256": key, "state": "blocked_live_request"}
        ledger = ledger_root / (key + ".json")
        prior = json.loads(ledger.read_text()) if ledger.exists() else {}
        # A verified completed identical request resolves uncertainty without resubmission.
        for root in [*success_roots, prior.get("successful_cache", "")]:
            if not root:
                continue
            candidate = Path(root) / key
            if (candidate / "parsed.json").exists():
                proof = verify_entry(candidate, model=policy["model"], backend="codex")
                shutil.copytree(candidate, target / key)
                result = {
                    "request_sha256": key,
                    "state": "reused_verified_success",
                    "source": str(candidate),
                    "proof": proof,
                    "new_model_calls": 0,
                }
                atomic_json(
                    ledger,
                    prior
                    | {
                        "state": "verified_success",
                        "successful_cache": str(target.resolve()),
                        "last_result": result,
                    },
                )
                return result
        if not policy.get("allow_new_adapter_calls", False):
            return {"request_sha256": key, "state": "blocked_cache_only"}
        why = failure(folder)
        if not why["retryable"]:
            return {
                "request_sha256": key,
                "state": "blocked_nonretryable_or_uncertain",
                "failure": why,
            }
        if prior.get("state") == "submitting":
            return {
                "request_sha256": key,
                "state": "blocked_uncertain_previous_submission",
            }
        attempts = prior.get("outer_attempts", 0)
        if attempts >= policy["max_outer_attempts"]:
            return {"request_sha256": key, "state": "blocked_retry_budget"}
        not_before = max(
            why["last_response_epoch"]
            + max(policy["cooldown_seconds"], why["retry_after_seconds"]),
            prior.get("not_before_epoch", 0),
        )
        if now() < not_before:
            return {
                "request_sha256": key,
                "state": "deferred_cooldown",
                "not_before_epoch": not_before,
            }
        atomic_json(
            ledger,
            {
                "state": "submitting",
                "outer_attempts": attempts + 1,
                "request_sha256": key,
                "output": str(target.resolve()),
                "started_epoch": now(),
            },
        )
        try:
            caller(
                request["prompt"],
                request["schema"],
                target,
                backend="codex",
                model=policy["model"],
                max_attempts=1,
            )
            proof = verify_entry(target / key, model=policy["model"], backend="codex")
            result = {
                "request_sha256": key,
                "state": "recovered_verified_success",
                "proof": proof,
                "new_model_calls": 1,
            }
            atomic_json(
                ledger,
                {
                    "state": "verified_success",
                    "outer_attempts": attempts + 1,
                    "successful_cache": str(target.resolve()),
                    "last_result": result,
                },
            )
            return result
        except Exception as error:
            why_new = failure(target / key)
            state = "confirmed_failed" if why_new["retryable"] else "submitting"
            atomic_json(
                ledger,
                {
                    "state": state,
                    "outer_attempts": attempts + 1,
                    "not_before_epoch": now()
                    + max(
                        policy["cooldown_seconds"],
                        why_new.get("retry_after_seconds", 0),
                    ),
                    "error": str(error),
                    "failure": why_new,
                },
            )
            return {
                "request_sha256": key,
                "state": "failed_retry"
                if state == "confirmed_failed"
                else "blocked_uncertain_submission",
                "error": str(error),
                "failure": why_new,
            }


def run(manifest, output):
    p = json.loads(Path(manifest).read_text())
    if (
        p.get("policy") != "bounded_model_continuation_v1"
        or p.get("backend") != "codex"
        or not p.get("model")
    ):
        raise ValueError("Explicit supported policy/backend/model required")
    if p["max_outer_attempts"] != 1 or p["cooldown_seconds"] < 900:
        raise ValueError("Policy permits one outer attempt and at least15min cooldown")
    actual = digest({x.name: x.read_text() for x in Path(__file__).parent.glob("*.py")})
    if (
        p["code_sha256"] != actual
        or file_hashes(p["source_cache"]) != p["source_sha256"]
    ):
        raise ValueError("Pinned code or source cache changed")
    for root, hashes in p["success_sha256"].items():
        if file_hashes(root) != hashes:
            raise ValueError("Pinned successful cache changed")
    if set(p["success_caches"]) != set(p["success_sha256"]):
        raise ValueError("All successful cache roots must be pinned")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    atomic_json(output / "manifest.json", p)
    imported = import_cache(
        p["source_cache"], output / "model", model=p["model"], backend="codex"
    )
    results = []
    for key in p["failed_requests"]:
        if (output / "model" / key).exists():
            raise ValueError("Requested recovery is already successful in source")
        result = continue_one(
            Path(p["source_cache"]) / key,
            output / "model",
            p,
            p["success_caches"],
            p["ledger_root"],
        )
        results.append(result)
        atomic_json(output / "progress.json", results)
    report = {
        "policy": p["policy"],
        "results": results,
        "source_successes_imported": len(imported["verified"]),
        "source_unchanged": file_hashes(p["source_cache"]) == p["source_sha256"],
        "usable_success_cache": str((output / "model").resolve()),
        "limitation": "Successful model requests are not scientific acceptance; downstream source/eligibility/method checks still apply. One outer retry permits one adapter invocation; CLI may retry transport internally.",
    }
    atomic_json(output / "continuation.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.manifest, args.output), indent=2))

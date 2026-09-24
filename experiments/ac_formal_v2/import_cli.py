from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
from typing import Any

from experiments.ac_formal_v2.common import (
    BASE,
    CASE_IDS,
    EXPERIMENT_ID,
    PROVIDERS,
    assert_collection_freeze_tag,
    assert_frozen_source_hashes,
    append_jsonl,
    load_json,
    read_jsonl,
)
from experiments.ac_formal_v2.collect import _merge_provider_logs


NOT_AVAILABLE = "not_available_cli"
CALL_PATHS = {"gpt": "codex_cli_exec", "claude": "claude_code_cli_print"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_commit() -> str | None:
    result = subprocess.run(
        ["git", "-C", str(BASE.parents[1]), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def claude_text(raw: dict[str, Any]) -> str:
    value = raw.get("result")
    return value if isinstance(value, str) else ""


def claude_model_name(raw: dict[str, Any]) -> str:
    usage = raw.get("modelUsage")
    if isinstance(usage, dict) and usage:
        return ",".join(sorted(str(name) for name in usage))
    return raw.get("model") if isinstance(raw.get("model"), str) else NOT_AVAILABLE


def _jsonl_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing or empty required CLI file: {path}")
    rows = read_jsonl(path)
    if not rows:
        raise RuntimeError(f"no records in required CLI log: {path}")
    return rows


def _case_schedule() -> dict[tuple[str, str, int], dict[str, Any]]:
    rows = load_json(BASE / "config" / "schedule.json")["calls"]
    return {(row["case_id"], row["provider"], row["run_id"]): row for row in rows}


def _prompt(case_id: str) -> dict[str, Any]:
    path = BASE / "frozen" / "prompts" / f"{case_id}.json"
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing or empty frozen prompt: {path}")
    return load_json(path)


def _records_for(
    provider: str,
    expected: dict[tuple[str, str, int], dict[str, Any]],
    commit: str | None,
) -> list[dict[str, Any]]:
    source_dir = BASE / "cli_raw" / EXPERIMENT_ID / provider
    log_rows = _jsonl_records(source_dir / "run_log.jsonl")
    logs: dict[tuple[str, str, int], dict[str, Any]] = {}
    for item in log_rows:
        key = (str(item.get("case_id")), provider, int(item.get("run_id", 0)))
        if key in logs or key not in expected:
            raise RuntimeError(f"unexpected or duplicate {provider} run-log key: {key}")
        logs[key] = item
    provider_schedule = {key: row for key, row in expected.items() if key[1] == provider}
    if set(logs) != set(provider_schedule):
        raise RuntimeError(f"{provider} run log does not contain its exact 18 scheduled calls")

    result = []
    for key, row in sorted(provider_schedule.items(), key=lambda pair: pair[1]["schedule_index"]):
        case_id, _provider, run_id = key
        log = logs[key]
        artifact_path = source_dir / f"{case_id}_run{run_id}.json"
        if not artifact_path.is_file() or artifact_path.stat().st_size == 0:
            raise RuntimeError(f"missing or empty required CLI artifact: {artifact_path}")
        file_bytes = artifact_path.read_bytes()
        prompt = _prompt(case_id)
        if log.get("schedule_index") != row["schedule_index"]:
            raise RuntimeError(f"{provider} schedule index mismatch for {key}")
        if log.get("prompt_text_hash") != prompt.get("prompt_text_hash"):
            raise RuntimeError(f"{provider} prompt hash mismatch for {key}")
        if provider == "gpt":
            artifact = json.loads(file_bytes.decode("utf-8"))
            if artifact.get("prompt_text_hash") != prompt.get("prompt_text_hash"):
                raise RuntimeError(f"GPT artifact prompt hash mismatch for {key}")
            if artifact.get("case_hash") != prompt.get("case_hash"):
                raise RuntimeError(f"GPT artifact case hash mismatch for {key}")
            if artifact.get("run_id") != run_id or artifact.get("schedule_index") != row["schedule_index"]:
                raise RuntimeError(f"GPT artifact schedule identity mismatch for {key}")
            if not isinstance(artifact.get("raw_response"), str):
                raise RuntimeError(f"GPT raw CLI response missing for {key}")
            if sha256_bytes(artifact["raw_response"].encode("utf-8")) != artifact.get("raw_response_hash"):
                raise RuntimeError(f"GPT raw CLI response hash mismatch for {key}")
            raw_response = artifact["raw_response"]
            raw_text = artifact.get("raw_text") if isinstance(artifact.get("raw_text"), str) else ""
            model_returned = artifact.get("model_returned") or NOT_AVAILABLE
            usage = artifact.get("usage")
            finish_reason = artifact.get("finish_reason") or NOT_AVAILABLE
            timestamp_start = artifact.get("timestamp_start_utc")
            timestamp_end = artifact.get("timestamp_end_utc")
            latency_ms = artifact.get("latency_ms")
            params_sent = {
                "model": artifact.get("model_requested"),
                "reasoning_effort": artifact.get("reasoning_effort"),
                "max_output_tokens": artifact.get("max_output_tokens"),
                "model_instructions": "codex_cli_default_unmodified",
                "sandbox": "read-only",
                "shell_tool": False,
                "web_search": False,
            }
            attempts = artifact.get("attempts", [])
            provider_payload = {"events": artifact.get("events", [])}
            provider_payload_hash = artifact.get("raw_response_hash")
            parse_status = "NOT_RUN_IMPORT"
            raw_response_hash = artifact["raw_response_hash"]
            thread_id = artifact.get("thread_id")
            cli_version = artifact.get("cli_version")
            adapter_version = artifact.get("provider_adapter_version") or artifact.get("runner_version")
            provider_config_version = artifact.get("provider_config_version", "codex-cli-gpt6-isolated-v1")
        else:
            raw_response = file_bytes.decode("utf-8", "replace")
            try:
                artifact = json.loads(raw_response)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid Claude CLI JSON artifact for {key}") from exc
            if not isinstance(artifact, dict):
                raise RuntimeError(f"Claude CLI artifact is not an object for {key}")
            raw_text = claude_text(artifact)
            if log.get("stdout_sha256") != sha256_bytes(file_bytes):
                raise RuntimeError(f"Claude raw CLI response hash mismatch for {key}")
            model_returned = claude_model_name(artifact)
            usage = artifact.get("usage") or log.get("usage")
            finish_reason = artifact.get("stop_reason") or NOT_AVAILABLE
            timestamp_start = log.get("timestamp_start_utc")
            timestamp_end = log.get("timestamp_end_utc")
            latency_ms = log.get("latency_ms")
            params_sent = {
                "model": log.get("model_requested"),
                "cli_flags": log.get("cli_flags"),
                "system_prompt": "empty",
                "tools": "disabled",
            }
            attempts = log.get("attempts", [])
            provider_payload = artifact
            provider_payload_hash = sha256_bytes(file_bytes)
            parse_status = "NOT_RUN_IMPORT"
            raw_response_hash = sha256_bytes(file_bytes)
            thread_id = log.get("thread_id", NOT_AVAILABLE)
            cli_version = log.get("cli_version")
            adapter_version = log.get("runner_version", NOT_AVAILABLE)
            provider_config_version = "claude-code-cli-v1"

        log_provider = log.get("provider", provider)
        provider_matches = log_provider == provider or (provider == "claude" and log_provider == "anthropic")
        if log.get("case_id") != case_id or log.get("run_id") != run_id or not provider_matches:
            raise RuntimeError(f"CLI run-log identity mismatch for {key}")
        result.append({
            "experiment_id": EXPERIMENT_ID,
            "experiment_status": "FORMAL",
            "case_id": case_id,
            "case_type": prompt["case_type"],
            "condition": "offline_runtime_replay",
            "run_id": run_id,
            "schedule_index": row["schedule_index"],
            "schedule_seed": row["schedule_seed"],
            "provider": provider,
            "api_format": CALL_PATHS[provider],
            "model_requested": row["model_requested"],
            "model_returned": model_returned if isinstance(model_returned, str) and model_returned else NOT_AVAILABLE,
            "response_id": "not_available_cli",
            "thread_id": thread_id or NOT_AVAILABLE,
            "cli_version": cli_version or NOT_AVAILABLE,
            "call_path": CALL_PATHS[provider],
            "timestamp_start_utc": timestamp_start,
            "timestamp_end_utc": timestamp_end,
            "latency_ms": latency_ms,
            "case_hash": prompt["case_hash"],
            "fixture_hash": prompt["fixture_hash"],
            "policy_hash": prompt["policy_hash"],
            "prompt_text_hash": prompt["prompt_text_hash"],
            "api_request_hash": None,
            "http_status": None,
            "provider_status": finish_reason,
            "response_status": None,
            "incomplete_details": None,
            "output_item_types": None,
            "reasoning_tokens": usage.get("reasoning_tokens") if isinstance(usage, dict) else None,
            "output_tokens": (usage.get("output_tokens") or usage.get("outputTokens")) if isinstance(usage, dict) else None,
            "extraction_status": "SUCCESS" if raw_text else "EMPTY_OUTPUT",
            "extraction_path": "codex_cli.agent_message" if provider == "gpt" else "claude_cli.result",
            "raw_response_hash": raw_response_hash,
            "provider_payload_hash": provider_payload_hash,
            "sanitized_request": {"model": row["model_requested"], "prompt_text_hash": prompt["prompt_text_hash"]},
            "params_sent": params_sent,
            "params_unsupported": [],
            "sampling_parameters": "not_set_provider_default",
            "finish_reason": finish_reason,
            "usage": usage,
            "raw_response": raw_response,
            "raw_response_body": raw_response,
            "provider_payload": provider_payload,
            "raw_text": raw_text,
            "raw_model_text": raw_text,
            "raw_model_text_hash": sha256_bytes(raw_text.encode("utf-8")),
            "parse_status": parse_status,
            "parsed_candidate": None,
            "attempts": attempts,
            "transport_failure": bool(log.get("transport_failure")),
            "live_runtime": None,
            "git_commit": commit,
            "runtime_version": "authoritative-contract-v1.1",
            "validator_version": "consistency-validator-v1.1",
            "provider_adapter": adapter_version or NOT_AVAILABLE,
            "provider_config": provider_config_version,
            "grounding_hash": None,
            "experiment_notes": None,
        })
    return result


def import_and_merge() -> dict[str, int]:
    assert_collection_freeze_tag()
    assert_frozen_source_hashes(load_json(BASE / "manifest.json"))
    schedule = _case_schedule()
    if len(schedule) != 54:
        raise RuntimeError("frozen schedule must contain 54 cells")
    expected_keys = {(case_id, run_id) for case_id in CASE_IDS for run_id in (1, 2, 3)}
    commit = git_commit()
    imported = {provider: _records_for(provider, schedule, commit) for provider in ("gpt", "claude")}

    raw_dir = BASE / "raw" / EXPERIMENT_ID
    deepseek_path = raw_dir / "calls_deepseek.jsonl"
    deepseek = _jsonl_records(deepseek_path)
    deepseek_keys = {(row.get("case_id"), row.get("run_id")) for row in deepseek if row.get("provider") == "deepseek"}
    if len(deepseek) != 18 or deepseek_keys != expected_keys:
        raise RuntimeError("DeepSeek formal file must contain exactly the 18 scheduled calls")

    for provider in ("gpt", "claude"):
        target = raw_dir / f"calls_{provider}.jsonl"
        if target.exists():
            raise RuntimeError(f"refusing to overwrite imported provider file: {target}")
    merged_target = raw_dir / "calls.jsonl"
    if merged_target.exists():
        raise RuntimeError(f"refusing to overwrite merged calls file: {merged_target}")

    for provider, rows in imported.items():
        target = raw_dir / f"calls_{provider}.jsonl"
        for row in rows:
            append_jsonl(target, row)
    merged = _merge_provider_logs(raw_dir, smoke=False)
    all_keys = {(row.get("case_id"), row.get("provider"), row.get("run_id")) for row in merged}
    expected = {(case_id, provider, run_id) for case_id in CASE_IDS for provider, _ in PROVIDERS for run_id in (1, 2, 3)}
    if len(merged) != 54 or all_keys != expected:
        raise RuntimeError("merged calls did not match the exact 54 frozen schedule cells")
    return {"gpt": len(imported["gpt"]), "claude": len(imported["claude"]), "merged": len(merged)}


def main() -> int:
    try:
        result = import_and_merge()
    except Exception as exc:
        print(f"IMPORT_STOPPED: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

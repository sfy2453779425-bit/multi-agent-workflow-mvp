from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any

from experiments.ac_formal_v2.common import (
    BASE,
    EXPERIMENT_ID,
    ROOT,
    assert_collection_freeze_tag,
    assert_frozen_source_hashes,
    load_json,
    sha256_json,
    sha256_text,
)


MODEL = "gpt-6-astra"
REASONING_EFFORT = "low"
MAX_OUTPUT_TOKENS = 1024
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (15, 45)
PROBE_PROMPT = "Reply with the single word OK."
RUNNER_VERSION = "codex-cli-runner-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_codex_output(stdout: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors.append("non-JSON line in Codex JSONL output")
            continue
        if not isinstance(event, dict):
            errors.append("non-object event in Codex JSONL output")
            continue
        events.append(event)

    messages: list[str] = []
    model_returned = "not_available_cli"
    thread_id = "not_available_cli"
    event_errors: list[str] = []
    usage = None
    finish_reason = "not_available_cli"
    for event in events:
        kind = event.get("type")
        if kind == "thread.started" and isinstance(event.get("thread_id"), str):
            thread_id = event["thread_id"]
        item = event.get("item")
        if kind == "item.completed" and isinstance(item, dict) and item.get("type") == "agent_message":
            if isinstance(item.get("text"), str):
                messages.append(item["text"])
            elif isinstance(item.get("content"), list):
                parts = [part.get("text", "") for part in item["content"] if isinstance(part, dict)]
                messages.append("".join(part for part in parts if isinstance(part, str)))
        for key in ("model", "model_name"):
            if isinstance(event.get(key), str) and event[key]:
                model_returned = event[key]
        if kind == "turn.completed":
            usage = event.get("usage", event.get("token_usage"))
            finish_reason = event.get("status") or "completed"
        elif kind in {"turn.failed", "error"}:
            error = event.get("error")
            message = error.get("message") if isinstance(error, dict) else error
            finish_reason = message if isinstance(message, str) else kind
            event_errors.append(str(finish_reason))

    return {
        "events": events,
        "raw_text": messages[-1] if messages else "",
        "model_returned": model_returned,
        "thread_id": thread_id,
        "usage": usage,
        "finish_reason": finish_reason,
        "event_error_text": " ".join(event_errors),
        "parse_status": "CLI_JSONL_PARSE_FAILED" if errors else ("CLI_OUTPUT_PRESENT" if messages else "CLI_OUTPUT_EMPTY"),
        "parse_errors": errors,
    }


def retryable_cli_failure(error_text: str) -> bool:
    text = error_text.lower()
    if re.search(r"\b(?:429|5\d\d)\b", text):
        return True
    if re.search(r"\b4\d\d\b", text):
        return False
    return any(marker in text for marker in (
        "network error", "connection timed out", "timed out", "connection reset",
        "connection refused", "failed to connect", "could not resolve", "dns error",
        "socket hang up", "tls handshake", "temporary failure in name resolution",
    ))


def fatal_cli_failure(error_text: str) -> bool:
    return bool(re.search(r"\b4\d\d\b", error_text) and not re.search(r"\b429\b", error_text))


def _redact_error(value: str) -> str:
    value = re.sub(r"(?i)sk-[A-Za-z0-9_-]{16,}", "[REDACTED]", value)
    value = re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", value)
    return value[:1000]


def _codex_executable() -> str:
    found = shutil.which("codex")
    if found:
        return found
    fallback_root = Path.home() / "AppData" / "Local" / "OpenAI" / "Codex" / "bin"
    matches = sorted(fallback_root.glob("*/codex.exe")) if fallback_root.exists() else []
    if matches:
        return str(matches[-1])
    raise RuntimeError("Codex CLI executable not found")


def _auth_file() -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
    path = codex_home / "auth.json"
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("Codex CLI login file is unavailable; no credentials were read from chat")
    return path


def _clean_env(codex_home: Path) -> dict[str, str]:
    keep = (
        "PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "OS",
        "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
        "TEMP", "TMP", "PROCESSOR_ARCHITECTURE",
    )
    env = {key: os.environ[key] for key in keep if key in os.environ}
    env["CODEX_HOME"] = str(codex_home)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _isolated_call(exe: str, prompt: str, cli_version: str) -> dict[str, Any]:
    source_auth = _auth_file()
    started_utc = utc_now()
    started = time.perf_counter()
    attempt_results: list[dict[str, Any]] = []

    for attempt_no in range(1, MAX_ATTEMPTS + 1):
        with tempfile.TemporaryDirectory(prefix="acv2_codex_") as temporary:
            root = Path(temporary)
            codex_home = root / "codex_home"
            workdir = root / "empty_workdir"
            codex_home.mkdir()
            workdir.mkdir()
            shutil.copy2(source_auth, codex_home / "auth.json")
            config = "\n".join((
                f"model = {_toml_string(MODEL)}",
                f"model_reasoning_effort = {_toml_string(REASONING_EFFORT)}",
                f"model_max_output_tokens = {MAX_OUTPUT_TOKENS}",
                'approval_policy = "never"',
                'sandbox_mode = "read-only"',
                'web_search = "disabled"',
                "",
                "[history]",
                'persistence = "none"',
                "",
                "[features]",
                "shell_tool = false",
                "multi_agent = false",
                "",
            ))
            (codex_home / "config.toml").write_text(config, encoding="utf-8")
            command = [
                exe, "--no-daemon", "--ask-for-approval", "never", "exec",
                "--model", MODEL, "--sandbox", "read-only", "--ephemeral",
                "--skip-git-repo-check", "--ignore-rules", "--json", "--cd", str(workdir), "-",
            ]
            try:
                proc = subprocess.run(
                    command,
                    input=prompt.encode("utf-8"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=workdir,
                    env=_clean_env(codex_home),
                    timeout=600,
                    check=False,
                )
                stdout_bytes = proc.stdout or b""
                stdout = stdout_bytes.decode("utf-8", "replace")
                stderr = proc.stderr.decode("utf-8", "replace")
                exit_code = proc.returncode
                timed_out = False
            except subprocess.TimeoutExpired as exc:
                stdout_bytes = exc.stdout or b""
                if isinstance(stdout_bytes, str):
                    stdout_bytes = stdout_bytes.encode("utf-8")
                stdout = stdout_bytes.decode("utf-8", "replace")
                stderr = "Codex CLI request timed out"
                exit_code = None
                timed_out = True

            extracted = extract_codex_output(stdout)
            error_text = _redact_error(" ".join(value for value in (stderr, extracted["event_error_text"]) if value))
            retryable = timed_out or retryable_cli_failure(error_text)
            attempt_results.append({
                "attempt_no": attempt_no,
                "exit_code": exit_code,
                "timed_out": timed_out,
                "retryable_transport_error": retryable,
                "error_message": error_text or None,
                "raw_stdout": stdout,
                "raw_stdout_hash": sha256_bytes(stdout_bytes),
                "parse_status": extracted["parse_status"],
            })
            if exit_code == 0 and extracted["parse_status"] == "CLI_OUTPUT_PRESENT":
                return {
                    **extracted,
                    "raw_response": stdout,
                    "raw_response_hash": sha256_bytes(stdout_bytes),
                    "attempts": attempt_results,
                    "transport_failure": False,
                    "cli_exit_code": exit_code,
                    "started_utc": started_utc,
                    "ended_utc": utc_now(),
                    "latency_ms": round((time.perf_counter() - started) * 1000),
                    "cli_version": cli_version,
                    "cli_command": command,
                    "isolation": {
                        "fresh_process": True,
                        "fresh_empty_workdir": True,
                        "fresh_codex_home": True,
                        "empty_default_instructions_override": False,
                        "system_instructions": "codex_cli_default_unmodified",
                        "sandbox": "read-only",
                        "shell_tool": False,
                        "web_search": False,
                        "mcp_config": "absent",
                    },
                }
            if not retryable or attempt_no == MAX_ATTEMPTS:
                return {
                    **extracted,
                    "raw_response": stdout,
                    "raw_response_hash": sha256_bytes(stdout_bytes),
                    "attempts": attempt_results,
                    "transport_failure": retryable,
                    "cli_exit_code": exit_code,
                    "started_utc": started_utc,
                    "ended_utc": utc_now(),
                    "latency_ms": round((time.perf_counter() - started) * 1000),
                    "cli_version": cli_version,
                    "cli_command": command,
                    "isolation": {
                        "fresh_process": True,
                        "fresh_empty_workdir": True,
                        "fresh_codex_home": True,
                        "empty_default_instructions_override": False,
                        "system_instructions": "codex_cli_default_unmodified",
                        "sandbox": "read-only",
                        "shell_tool": False,
                        "web_search": False,
                        "mcp_config": "absent",
                    },
                    "fatal_cli_error": fatal_cli_failure(error_text),
                }
        if attempt_no < MAX_ATTEMPTS:
            time.sleep(BACKOFF_SECONDS[attempt_no - 1])
    raise AssertionError("unreachable retry loop")


def _cli_version(exe: str) -> str:
    proc = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30, check=False)
    if proc.returncode != 0:
        raise RuntimeError("Codex CLI version check failed")
    return proc.stdout.strip()


def _git_commit() -> str | None:
    result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def _load_prompt(case_id: str) -> dict[str, Any]:
    prompt = load_json(BASE / "frozen" / "prompts" / f"{case_id}.json")
    messages = prompt.get("messages")
    if not isinstance(messages, list) or not messages or messages[0].get("role") != "user":
        raise RuntimeError(f"{case_id}: frozen first message missing")
    text = messages[0].get("content")
    digest = sha256_text(text) if isinstance(text, str) else None
    if digest != prompt.get("prompt_text_hash"):
        raise RuntimeError(f"{case_id}: frozen prompt hash mismatch")
    return prompt


def _check_frozen() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    assert_collection_freeze_tag()
    manifest = load_json(BASE / "manifest.json")
    assert_frozen_source_hashes(manifest)
    schedule_file = load_json(BASE / "config" / "schedule.json")
    schedule = schedule_file["calls"]
    config = load_json(BASE / "config" / "freeze_config.json")
    if sha256_json(schedule) != schedule_file.get("schedule_hash"):
        raise RuntimeError("FREEZE_VIOLATION: schedule hash mismatch")
    rows = sorted((row for row in schedule if row["provider"] == "gpt"), key=lambda row: row["schedule_index"])
    gpt_config = config.get("provider", {}).get("gpt", {})
    if (len(rows) != 18 or config["models"].get("gpt") != MODEL
            or gpt_config.get("api_format") != "codex_cli_exec"
            or gpt_config.get("reasoning_effort") != REASONING_EFFORT
            or gpt_config.get("max_output_tokens") != MAX_OUTPUT_TOKENS):
        raise RuntimeError("FREEZE_VIOLATION: expected 18 scheduled GPT-6 calls")
    for row in rows:
        if row["model_requested"] != MODEL:
            raise RuntimeError("FREEZE_VIOLATION: GPT schedule model differs from frozen config")
        _load_prompt(row["case_id"])
    return manifest, rows


def _write_exclusive(path: Path, artifact: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(artifact, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _append_log(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if not path.exists() else "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _run_one(exe: str, version: str, prompt: str) -> dict[str, Any]:
    return _isolated_call(exe, prompt, version)


def run_probe() -> dict[str, Any]:
    exe = _codex_executable()
    version = _cli_version(exe)
    result = _run_one(exe, version, PROBE_PROMPT)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = BASE / "cli_raw" / "_probe" / f"gpt_probe_{stamp}.json"
    artifact = {
        "experiment_status": "PROBE",
        "probe_prompt": PROBE_PROMPT,
        "runner_version": RUNNER_VERSION,
        "model_requested": MODEL,
        **result,
    }
    _write_exclusive(path, artifact)
    _append_log(BASE / "cli_raw" / "_probe" / "gpt_run_log.jsonl", {
        "artifact": path.name,
        "model_requested": MODEL,
        "model_returned": result["model_returned"],
        "cli_version": version,
        "finish_reason": result["finish_reason"],
        "output_nonempty": bool(result["raw_text"]),
        "transport_failure": result["transport_failure"],
        "attempts": [
            {key: attempt.get(key) for key in ("attempt_no", "exit_code", "timed_out", "retryable_transport_error", "error_message")}
            for attempt in result["attempts"]
        ],
    })
    return {"model_requested": MODEL, "model_returned": result["model_returned"], "cli_version": version,
            "finish_reason": result["finish_reason"], "output_nonempty": bool(result["raw_text"]),
            "transport_failure": result["transport_failure"], "artifact": str(path)}


def run_formal() -> dict[str, Any]:
    manifest, rows = _check_frozen()
    exe = _codex_executable()
    version = _cli_version(exe)
    output = BASE / "cli_raw" / EXPERIMENT_ID / "gpt"
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("GPT CLI output already exists; refusing to overwrite or retry")
    output.mkdir(parents=True, exist_ok=True)
    log_path = output / "run_log.jsonl"
    completed = 0
    for row in rows:
        prompt_record = _load_prompt(row["case_id"])
        result = _run_one(exe, version, prompt_record["messages"][0]["content"])
        artifact = {
            "experiment_id": EXPERIMENT_ID,
            "experiment_status": "FORMAL",
            "case_id": row["case_id"],
            "case_type": prompt_record["case_type"],
            "run_id": row["run_id"],
            "schedule_index": row["schedule_index"],
            "schedule_seed": row["schedule_seed"],
            "provider": "gpt",
            "call_path": "codex_cli_exec",
            "runner_version": RUNNER_VERSION,
            "cli_version": version,
            "model_requested": MODEL,
            "provider_config_version": "codex-cli-gpt6-isolated-v1",
            "model_returned": result["model_returned"],
            "response_id": "not_available_cli",
            "thread_id": result["thread_id"],
            "prompt_text_hash": prompt_record["prompt_text_hash"],
            "case_hash": prompt_record["case_hash"],
            "fixture_hash": prompt_record["fixture_hash"],
            "policy_hash": prompt_record["policy_hash"],
            "timestamp_start_utc": result["started_utc"],
            "timestamp_end_utc": result["ended_utc"],
            "latency_ms": result["latency_ms"],
            "finish_reason": result["finish_reason"],
            "usage": result["usage"],
            "raw_response": result["raw_response"],
            "raw_response_hash": result["raw_response_hash"],
            "raw_text": result["raw_text"],
            "raw_text_hash": sha256_text(result["raw_text"]),
            "parse_status": result["parse_status"],
            "parse_errors": result["parse_errors"],
            "events": result["events"],
            "cli_exit_code": result["cli_exit_code"],
            "attempts": result["attempts"],
            "transport_failure": result["transport_failure"],
            "cli_command": result["cli_command"],
            "isolation": result["isolation"],
            "reasoning_effort": REASONING_EFFORT,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "sampling_parameters": "not_set_provider_default",
            "temperature": "not_set_provider_default",
            "top_p": "not_set_provider_default",
            "seed": "not_set_provider_default",
            "provider_adapter_version": RUNNER_VERSION,
            "fatal_cli_error": result.get("fatal_cli_error", False),
            "git_commit": _git_commit(),
        }
        artifact_path = output / f"{row['case_id']}_run{row['run_id']}.json"
        _write_exclusive(artifact_path, artifact)
        _append_log(log_path, {
            "experiment_id": EXPERIMENT_ID,
            "case_id": row["case_id"],
            "run_id": row["run_id"],
            "schedule_index": row["schedule_index"],
            "prompt_text_hash": prompt_record["prompt_text_hash"],
            "model_requested": MODEL,
            "model_returned": result["model_returned"],
            "cli_version": version,
            "timestamp_start_utc": result["started_utc"],
            "timestamp_end_utc": result["ended_utc"],
            "latency_ms": result["latency_ms"],
            "finish_reason": result["finish_reason"],
            "usage": result["usage"],
            "parse_status": result["parse_status"],
            "transport_failure": result["transport_failure"],
            "attempts": [
                {key: attempt.get(key) for key in ("attempt_no", "exit_code", "timed_out", "retryable_transport_error", "error_message")}
                for attempt in result["attempts"]
            ],
        })
        completed += 1
        print(json.dumps({"schedule_index": row["schedule_index"], "case_id": row["case_id"], "run_id": row["run_id"],
                          "output_nonempty": bool(result["raw_text"]), "finish_reason": result["finish_reason"],
                          "transport_failure": result["transport_failure"]}, ensure_ascii=False))
        if result["transport_failure"] or result.get("fatal_cli_error"):
            raise RuntimeError("GPT CLI transport/HTTP failure recorded; stopping remaining scheduled calls")
    return {"completed": completed, "planned": len(rows), "output_dir": str(output)}


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--probe", action="store_true")
    mode.add_argument("--formal", action="store_true")
    args = parser.parse_args()
    try:
        result = run_formal() if args.formal else run_probe()
    except Exception as exc:
        print(type(exc).__name__ + ": " + _redact_error(str(exc)))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

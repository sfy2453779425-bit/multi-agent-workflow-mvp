from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


V3_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = V3_ROOT.parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
V2_ROOT = PACKAGE_ROOT / "v2"
EXPERIMENT_ID = "builder_v3_threeway_20260925"
CASE_DOMAINS = {"outfit": "Outfit", "presentation": "Presentation", "customer_support": "Customer Support"}
SYSTEMS = ("GPT-CLI", "Claude-CLI", "Builder")
REPORT_SYSTEMS = ("GPT-CLI", "Claude-CLI", "Builder", "ChatGPT-web-0916")
GPT_MODEL = "gpt-6-astra"
CLAUDE_MODEL = "claude-opus-5-5"
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (15, 45)
CALL_TIMEOUT_SECONDS = 600
RETRY_MARKERS = (
    "network error", "connection timed out", "timed out", "connection reset",
    "connection refused", "failed to connect", "could not resolve", "dns error",
    "socket hang up", "tls handshake", "temporary failure in name resolution",
)
ENV_KEEP = (
    "PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "OS",
    "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
    "TEMP", "TMP", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS",
)
SECRET_RE = re.compile(
    r"(?i)\bsk-[A-Za-z0-9_-]{24,}|\bsk-ant-[A-Za-z0-9_-]{20,}|"
    r"\bAIza[0-9A-Za-z_-]{30,}|\bAKIA[0-9A-Z]{16}\b|"
    r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b|github_pat_[A-Za-z0-9_]{30,}"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def build_schedule(cases: list[str], systems: list[str] | tuple[str, ...], runs: int) -> list[dict[str, Any]]:
    rows = []
    for run in range(1, runs + 1):
        for case_id in cases:
            for system in systems:
                rows.append({"schedule_index": len(rows) + 1, "case_id": case_id, "run": run, "system": system})
    return rows


def _message_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(part.get("text", "") for part in value if isinstance(part, dict) and isinstance(part.get("text"), str))
    return ""


def parse_codex_output(raw: str) -> dict[str, Any]:
    events = []
    errors = []
    for line in raw.splitlines():
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

    messages = []
    model_returned = "not_available_cli"
    usage = None
    finish_reason = "not_available_cli"
    provider_errors = []
    for event in events:
        for key in ("model", "model_name"):
            if isinstance(event.get(key), str) and event[key]:
                model_returned = event[key]
        item = event.get("item")
        if event.get("type") == "item.completed" and isinstance(item, dict) and item.get("type") == "agent_message":
            text = item.get("text") if isinstance(item.get("text"), str) else _message_text(item.get("content"))
            if text:
                messages.append(text)
        if event.get("type") == "turn.completed":
            usage = event.get("usage", event.get("token_usage"))
            finish_reason = event.get("status") or "completed"
        if event.get("type") in {"turn.failed", "error"}:
            error = event.get("error")
            if isinstance(error, dict):
                provider_errors.append(str(error.get("message", error.get("code", "provider error"))))
                if isinstance(error.get("status_code"), int):
                    provider_errors.append(str(error["status_code"]))
            elif error is not None:
                provider_errors.append(str(error))
            finish_reason = provider_errors[-1] if provider_errors else event.get("type")
    return {
        "events": events,
        "text": messages[-1] if messages else "",
        "model_returned": model_returned,
        "usage": usage if isinstance(usage, dict) else None,
        "finish_reason": finish_reason,
        "provider_error_text": " ".join(provider_errors),
        "parse_status": "CLI_JSONL_PARSE_FAILED" if errors else ("CLI_OUTPUT_PRESENT" if messages else "CLI_OUTPUT_EMPTY"),
        "parse_errors": errors,
    }


def parse_claude_output(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"payload": None, "text": "", "model_returned": [], "usage": None,
                "finish_reason": "not_available_cli", "provider_error_text": "",
                "parse_status": "CLI_OUTPUT_NOT_JSON", "parse_errors": ["Claude CLI stdout is not JSON"]}
    if not isinstance(payload, dict):
        payload = {}
    model_usage = payload.get("modelUsage")
    model_returned = sorted(model_usage) if isinstance(model_usage, dict) else []
    if not model_returned and isinstance(payload.get("model"), str):
        model_returned = [payload["model"]]
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else None
    api_status = payload.get("api_error_status")
    error_text = ""
    if payload.get("is_error"):
        error_text = str(api_status or payload.get("error", payload.get("subtype", "CLI error")))
    finish_reason = payload.get("stop_reason") or payload.get("subtype") or ("completed" if not payload.get("is_error") else "error")
    result = payload.get("result")
    text = result if isinstance(result, str) else ""
    return {
        "payload": payload,
        "text": text,
        "model_returned": model_returned,
        "usage": usage,
        "finish_reason": finish_reason,
        "provider_error_text": error_text,
        "parse_status": "CLI_OUTPUT_PRESENT" if text else ("CLI_OUTPUT_EMPTY" if not payload.get("is_error") else "CLI_ERROR"),
        "parse_errors": [],
    }


def retryable_transport_error(text: str, timed_out: bool = False) -> bool:
    if timed_out:
        return True
    if re.search(r"(?i)\b(?:429|5\d\d)\b", text):
        return True
    if re.search(r"(?i)\b4\d\d\b", text):
        return False
    return any(marker in text.lower() for marker in RETRY_MARKERS)


def _redact_error(value: str) -> str:
    value = SECRET_RE.sub("[REDACTED]", value)
    value = re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", value)
    return value[:1200]


def _json_write_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_freeze_json(path: Path, value: Any) -> None:
    serialized = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == serialized:
        return
    path.write_text(serialized, encoding="utf-8", newline="\n")


def _write_bytes_exclusive(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def _write_freeze_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != value:
            raise RuntimeError(f"frozen input already exists with different bytes: {path.name}")
        return
    _write_bytes_exclusive(path, value)


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _git(source_root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(source_root), *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"git command failed: {' '.join(args)}")
    return result.stdout.strip()


def _load_source_runner(source_root: Path):
    path = source_root / "experiments" / "baseline_comparison" / "runner.py"
    if not path.is_file():
        raise FileNotFoundError(f"source Builder runner missing: {path}")
    src = source_root / "src"
    if str(src) in sys.path:
        sys.path.remove(str(src))
    sys.path.insert(0, str(src))
    spec = importlib.util.spec_from_file_location("acv3_source_baseline_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the current Builder runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _case_relative_path(case_id: str) -> Path:
    domain = "outfit" if case_id.startswith("outfit_") else "presentation" if case_id.startswith("presentation_") else "customer_support"
    return Path("fixtures") / domain / f"{case_id}.json"


def _load_v2_inputs() -> tuple[dict[str, Any], dict[str, Path]]:
    manifest = json.loads((V2_ROOT / "manifest.json").read_text(encoding="utf-8"))
    files = {case_id: Path(manifest["fixture_files"][case_id]) for case_id in manifest["cases"]}
    return manifest, files


def _cli_status(command: str, args: list[str]) -> tuple[bool, str]:
    result = subprocess.run([command, *args], capture_output=True, text=True, timeout=30, check=False)
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    logged_in = bool(re.search(r"(?i)\"?loggedIn\"?\s*:\s*true|logged\s+in|authenticated", combined))
    logged_out = bool(re.search(r"(?i)\"?loggedIn\"?\s*:\s*false|not\s+logged|unauthori[sz]ed|\b401\b", combined))
    return result.returncode == 0 and logged_in and not logged_out, "authenticated" if logged_in and not logged_out else "not_authenticated_or_unknown"


def _cli_version(command: str) -> str:
    result = subprocess.run([command, "--version"], capture_output=True, text=True, timeout=30, check=False)
    if result.returncode:
        raise RuntimeError(f"cannot read CLI version for {Path(command).name}")
    return (result.stdout or result.stderr).strip().splitlines()[0]


def freeze_experiment(source_root: str | Path) -> dict[str, Any]:
    if any(path.is_file() for folder in ("raw", "builder_runs") for path in (V3_ROOT / folder).rglob("*")):
        raise RuntimeError("collection already started; refusing to rewrite v3 freeze")
    source = Path(source_root).resolve()
    v2_manifest, fixture_paths = _load_v2_inputs()
    cases = list(v2_manifest["cases"])
    if len(cases) != 10:
        raise RuntimeError(f"expected the ten v2 frozen cases, found {len(cases)}")
    codex = shutil.which("codex")
    claude = shutil.which("claude")
    if not codex or not claude:
        raise RuntimeError("Codex CLI or Claude CLI is unavailable; no model call was made")
    gpt_authenticated, _ = _cli_status(codex, ["login", "status"])
    claude_authenticated, _ = _cli_status(claude, ["auth", "status"])
    if not gpt_authenticated or not claude_authenticated:
        raise RuntimeError("a model CLI is not authenticated; no login was attempted and no model call was made")
    codex_version = _cli_version(codex)
    claude_version = _cli_version(claude)
    source_runner = _load_source_runner(source)
    source_hashes = source_runner.builder_source_hashes()

    fixture_hashes = {}
    prompt_hashes = {}
    for case_id in cases:
        source_fixture = PACKAGE_ROOT / fixture_paths[case_id]
        raw_fixture = source_fixture.read_bytes()
        fixture = json.loads(raw_fixture.decode("utf-8"))
        canonical_fixture_hash = canonical_hash(fixture)
        expected_fixture_hash = v2_manifest["fixture_versions"][case_id]["sha256"]
        if canonical_fixture_hash != expected_fixture_hash:
            raise RuntimeError(f"FREEZE_VIOLATION: fixture hash differs for {case_id}")
        prompt_rel = Path(v2_manifest["prompt_files"]["chatgpt"][case_id])
        source_prompt = V2_ROOT / prompt_rel
        raw_prompt = source_prompt.read_bytes()
        prompt_hash = sha256_bytes(raw_prompt)
        expected_prompt_hash = v2_manifest["prompt_versions"][case_id]["sha256"]
        if prompt_hash != expected_prompt_hash:
            raise RuntimeError(f"FREEZE_VIOLATION: prompt hash differs for {case_id}")
        if sha256_bytes(source_runner.render_prompt(source_runner.load_fixture(case_id, root=PACKAGE_ROOT,
                case_files={case_id: fixture_paths[case_id]})).encode("utf-8")) != expected_prompt_hash:
            raise RuntimeError(f"FREEZE_VIOLATION: rendered prompt differs for {case_id}")
        fixture_target = V3_ROOT / "frozen" / "cases" / f"{case_id}.json"
        prompt_target = V3_ROOT / "frozen" / "prompts" / f"{case_id}.md"
        _write_freeze_bytes(fixture_target, raw_fixture)
        _write_freeze_bytes(prompt_target, raw_prompt)
        fixture_hashes[case_id] = {
            "fixture_version": fixture["fixture_version"],
            "canonical_sha256": canonical_fixture_hash,
            "raw_file_sha256": sha256_bytes(raw_fixture),
            "source_manifest_sha256": expected_fixture_hash,
        }
        prompt_hashes[case_id] = {
            "prompt_version": v2_manifest["prompt_versions"][case_id]["version"],
            "sha256": prompt_hash,
            "source_manifest_sha256": expected_prompt_hash,
            "source_file": str(prompt_rel).replace("\\", "/"),
        }

    schedule = build_schedule(cases, SYSTEMS, 3)
    schedule_hash = canonical_hash(schedule)
    _write_freeze_json(V3_ROOT / "schedule.json", {"calls": schedule, "sha256": schedule_hash})
    scoring_files = (
        "experiments/baseline_comparison/evaluation/scoring.py",
        "experiments/baseline_comparison/evaluation/versioned_analysis.py",
    )
    parser_hashes = {path: sha256_bytes((PACKAGE_ROOT.parents[1] / path).read_bytes()) for path in scoring_files}
    collection_hashes = {name: sha256_bytes((V3_ROOT / name).read_bytes())
                         for name in ("experiment.py", "test_experiment.py", "README.md")}
    fixture_versions = {case: {"version": data["fixture_version"], "sha256": data["canonical_sha256"]}
                        for case, data in fixture_hashes.items()}
    prompt_versions = {case: {"version": data["prompt_version"], "sha256": data["sha256"]}
                       for case, data in prompt_hashes.items()}
    source_status = _git(source, "status", "--short", "--branch")
    source_commit = _git(source, "rev-parse", "HEAD")
    source_branch = _git(source, "branch", "--show-current")
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "phase": "three-way pilot v3",
        "created_at_utc": utc_now(),
        "scope": "10 frozen cases x 3 runs x GPT-CLI / Claude-CLI / Builder; historical ChatGPT web results are separately labeled.",
        "v2_reference": {"experiment_id": v2_manifest["experiment_id"], "manifest_path": "../v2/manifest.json",
                         "v2_archive_commit": _git(REPO_ROOT, "rev-parse", "HEAD")},
        "cases": cases,
        "runs_per_case": 3,
        "builder_version": "current-runtime-v1.2-source-snapshot",
        "fixture_versions": fixture_versions,
        "prompt_versions": prompt_versions,
        "fixture_files": {case: f"frozen/cases/{case}.json" for case in cases},
        "prompt_files": {slug: {case: f"frozen/prompts/{case}.md" for case in cases}
                         for slug in ("gpt-cli", "claude-cli")},
        "systems": list(REPORT_SYSTEMS),
        "fixture_hashes": fixture_hashes,
        "prompt_hashes": prompt_hashes,
        "schedule_hash": schedule_hash,
        "builder": {
            "version_label": "current source from runtime-v1.2 checkout (dirty snapshot)",
            "source_root": str(source),
            "git_branch": source_branch,
            "git_commit": source_commit,
            "git_status_at_freeze": source_status.splitlines(),
            "source_hashes": source_hashes,
            "calls_model": False,
        },
        "providers": {
            "GPT-CLI": {"model_requested": GPT_MODEL, "cli": str(Path(codex).name), "cli_version": codex_version,
                        "call_path": "codex exec", "reasoning": "CLI default; no effort override", "output_limit": "not set",
                        "model_returned_recorded": True, "system_instructions": "Codex CLI defaults retained; project rules ignored in isolated temp workdir",
                        "sandbox": "read-only", "shell_tools": "disabled", "web_search": "disabled",
                        "fresh_session": "one ephemeral process and empty temporary CODEX_HOME/workdir per call"},
            "Claude-CLI": {"model_requested": CLAUDE_MODEL, "cli": str(Path(claude).name), "cli_version": claude_version,
                           "call_path": "claude -p --output-format json", "system_prompt": "empty", "tools": "none",
                           "setting_sources": "none", "session_persistence": "disabled", "output_limit": "not set",
                           "fresh_session": "one process and clean temporary workdir per call"},
            "Builder": {"execution": "local frozen-fixture workflow run", "calls_model": False},
            "ChatGPT-web-0916": {"source": "v2 historical 30 records", "model": "GPT-5.6 Sol",
                                 "interface": "ChatGPT web", "sampling_parameters": "unavailable",
                                 "exact_backend_revision": "unavailable"},
        },
        "evaluation": {"version": "evaluation-v2", "source_hashes": parser_hashes,
                       "metrics_and_parser_modified": False},
        "collection_tool_hashes": collection_hashes,
        "limitations": [
            "Codex CLI includes its default system instructions and is not identical to ChatGPT web.",
            "Claude Code CLI is not identical to the Claude web product.",
            "No human evaluation was conducted; language naturalness and user preference are not measured.",
            "Configuration cost is not measured in this experiment and is supplemented by the workflow reuse test.",
        ],
    }
    _write_freeze_json(V3_ROOT / "frozen" / "fixture_hashes.json", fixture_hashes)
    _write_freeze_json(V3_ROOT / "frozen" / "prompt_hashes.json", prompt_hashes)
    _write_freeze_json(V3_ROOT / "manifest.json", manifest)
    return {"experiment_id": EXPERIMENT_ID, "cases": len(cases), "schedule_rows": len(schedule),
            "schedule_hash": schedule_hash, "gpt_cli_version": codex_version, "claude_cli_version": claude_version}


def verify_freeze() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest_path = V3_ROOT / "manifest.json"
    schedule_path = V3_ROOT / "schedule.json"
    if not manifest_path.is_file() or not schedule_path.is_file():
        raise FileNotFoundError("v3 freeze is missing; run freeze first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schedule_file = json.loads(schedule_path.read_text(encoding="utf-8"))
    schedule = schedule_file["calls"]
    if canonical_hash(schedule) != manifest["schedule_hash"] or schedule_file["sha256"] != manifest["schedule_hash"]:
        raise RuntimeError("FREEZE_VIOLATION: schedule hash changed")
    v2_manifest, _ = _load_v2_inputs()
    if manifest["cases"] != v2_manifest["cases"]:
        raise RuntimeError("FREEZE_VIOLATION: case list differs from v2")
    for case_id in manifest["cases"]:
        fixture_path = V3_ROOT / "frozen" / "cases" / f"{case_id}.json"
        prompt_path = V3_ROOT / "frozen" / "prompts" / f"{case_id}.md"
        fixture_bytes = fixture_path.read_bytes()
        fixture = json.loads(fixture_bytes.decode("utf-8"))
        expected_fixture = manifest["fixture_hashes"][case_id]
        if canonical_hash(fixture) != expected_fixture["canonical_sha256"] or sha256_bytes(fixture_bytes) != expected_fixture["raw_file_sha256"]:
            raise RuntimeError(f"FREEZE_VIOLATION: fixture changed for {case_id}")
        prompt_hash = sha256_bytes(prompt_path.read_bytes())
        if prompt_hash != manifest["prompt_hashes"][case_id]["sha256"]:
            raise RuntimeError(f"FREEZE_VIOLATION: prompt changed for {case_id}")
        if expected_fixture["canonical_sha256"] != v2_manifest["fixture_versions"][case_id]["sha256"]:
            raise RuntimeError(f"FREEZE_VIOLATION: fixture no longer matches v2 for {case_id}")
        if prompt_hash != v2_manifest["prompt_versions"][case_id]["sha256"]:
            raise RuntimeError(f"FREEZE_VIOLATION: prompt no longer matches v2 for {case_id}")
        if manifest["prompt_versions"][case_id]["sha256"] != prompt_hash:
            raise RuntimeError(f"FREEZE_VIOLATION: prompt version map differs for {case_id}")
        if manifest["fixture_versions"][case_id]["sha256"] != expected_fixture["canonical_sha256"]:
            raise RuntimeError(f"FREEZE_VIOLATION: fixture version map differs for {case_id}")
    source = Path(manifest["builder"]["source_root"])
    source_runner = _load_source_runner(source)
    if source_runner.builder_source_hashes() != manifest["builder"]["source_hashes"]:
        raise RuntimeError("FREEZE_VIOLATION: Builder source hash changed")
    parser_root = PACKAGE_ROOT.parents[1]
    for rel, digest in manifest["evaluation"]["source_hashes"].items():
        if sha256_bytes((parser_root / rel).read_bytes()) != digest:
            raise RuntimeError("FREEZE_VIOLATION: evaluation-v2 parser source changed")
    for name, digest in manifest.get("collection_tool_hashes", {}).items():
        if sha256_bytes((V3_ROOT / name).read_bytes()) != digest:
            raise RuntimeError(f"FREEZE_VIOLATION: collection tool changed: {name}")
    return manifest, schedule


def _gpt_auth_file() -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
    auth = codex_home / "auth.json"
    if not auth.is_file() or auth.stat().st_size == 0:
        raise RuntimeError("Codex CLI login state is unavailable; no credentials were read from conversation")
    return auth


def _gpt_environment(codex_home: Path) -> dict[str, str]:
    env = {key: os.environ[key] for key in ENV_KEEP if key in os.environ}
    env["CODEX_HOME"] = str(codex_home)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _claude_environment() -> dict[str, str]:
    return {key: os.environ[key] for key in ENV_KEEP if key in os.environ}


def _call_with_retries(provider: str, executable: str, prompt: bytes, cli_version: str) -> dict[str, Any]:
    attempt_rows = []
    prior_raw = []
    last_result: dict[str, Any] = {}
    for attempt_no in range(1, MAX_ATTEMPTS + 1):
        with tempfile.TemporaryDirectory(prefix=f"acv3_{provider.lower().replace('-', '_')}_") as temp:
            root = Path(temp)
            workdir = root / "empty_workdir"
            workdir.mkdir()
            if provider == "GPT-CLI":
                codex_home = root / "codex_home"
                codex_home.mkdir()
                shutil.copy2(_gpt_auth_file(), codex_home / "auth.json")
                config = "\n".join((
                    f'model = "{GPT_MODEL}"', 'approval_policy = "never"', 'sandbox_mode = "read-only"',
                    'web_search = "disabled"', "", "[history]", 'persistence = "none"', "",
                    "[features]", "shell_tool = false", "multi_agent = false", "",
                ))
                (codex_home / "config.toml").write_text(config, encoding="utf-8")
                command = [executable, "--no-daemon", "--ask-for-approval", "never", "exec", "--model", GPT_MODEL,
                           "--sandbox", "read-only", "--ephemeral", "--skip-git-repo-check", "--ignore-rules",
                           "--json", "--cd", str(workdir), "-"]
                env = _gpt_environment(codex_home)
            else:
                command = [executable, "-p", "--model", CLAUDE_MODEL, "--output-format", "json", "--system-prompt", "",
                           "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence"]
                env = _claude_environment()
            started = datetime.now(timezone.utc)
            clock = time.perf_counter()
            timed_out = False
            try:
                proc = subprocess.run(command, input=prompt, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      cwd=workdir, env=env, timeout=CALL_TIMEOUT_SECONDS, check=False)
                raw = proc.stdout or b""
                stderr = proc.stderr.decode("utf-8", "replace")
                exit_code = proc.returncode
            except subprocess.TimeoutExpired as exc:
                raw = exc.stdout or b""
                if isinstance(raw, str):
                    raw = raw.encode("utf-8")
                stderr = "CLI request timed out"
                exit_code = None
                timed_out = True
            ended = datetime.now(timezone.utc)
            elapsed = round((time.perf_counter() - clock) * 1000)
        decoded = raw.decode("utf-8", "replace")
        parsed = parse_codex_output(decoded) if provider == "GPT-CLI" else parse_claude_output(decoded)
        error_text = _redact_error(" ".join(part for part in (stderr, parsed.get("provider_error_text", "")) if part))
        retry = retryable_transport_error(error_text, timed_out=timed_out)
        row = {"attempt_no": attempt_no, "exit_code": exit_code, "timed_out": timed_out,
               "retryable_transport_error": retry, "error_message": error_text or None,
               "raw_stdout_sha256": sha256_bytes(raw), "raw_stdout_bytes": len(raw),
               "parse_status": parsed["parse_status"]}
        attempt_rows.append(row)
        if attempt_no < MAX_ATTEMPTS and retry:
            prior_raw.append((attempt_no, raw))
            time.sleep(BACKOFF_SECONDS[attempt_no - 1])
            continue
        last_result = {
            **parsed,
            "raw_stdout": raw,
            "raw_stdout_sha256": sha256_bytes(raw),
            "attempts": attempt_rows,
            "transport_failure": retry,
            "fatal_auth_error": bool(re.search(r"(?i)\b401\b", error_text)),
            "cli_exit_code": exit_code,
            "timestamp_start_utc": started.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "timestamp_end_utc": ended.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "latency_ms": elapsed,
            "cli_version": cli_version,
            "prior_raw": prior_raw,
        }
        break
    return last_result


def _output_tokens(usage: Any) -> int | None:
    if not isinstance(usage, dict):
        return None
    for key in ("output_tokens", "outputTokens", "output_token_count"):
        value = usage.get(key)
        if isinstance(value, int):
            return value
    return None


def _relative(path: Path) -> str:
    return path.resolve().relative_to(V3_ROOT.resolve()).as_posix()


def _run_log_keys(path: Path) -> set[tuple[str, int]]:
    if not path.is_file():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        keys.add((str(row.get("case_id")), int(row.get("run", 0))))
    return keys


def collect_cli() -> dict[str, Any]:
    manifest, schedule = verify_freeze()
    codex = shutil.which("codex")
    claude = shutil.which("claude")
    if not codex or not claude:
        raise RuntimeError("a CLI executable is unavailable; no model call was made")
    versions = {"GPT-CLI": _cli_version(codex), "Claude-CLI": _cli_version(claude)}
    if versions["GPT-CLI"] != manifest["providers"]["GPT-CLI"]["cli_version"] or versions["Claude-CLI"] != manifest["providers"]["Claude-CLI"]["cli_version"]:
        raise RuntimeError("FREEZE_VIOLATION: CLI version changed after freeze")
    for provider, exe, args in (("GPT-CLI", codex, ["login", "status"]), ("Claude-CLI", claude, ["auth", "status"])):
        authenticated, _ = _cli_status(exe, args)
        if not authenticated:
            raise RuntimeError(f"{provider} is not authenticated; no login was attempted")
    completed = 0
    for row in schedule:
        provider = row["system"]
        if provider not in {"GPT-CLI", "Claude-CLI"}:
            continue
        case_id, run = row["case_id"], int(row["run"])
        prompt_path = V3_ROOT / "frozen" / "prompts" / f"{case_id}.md"
        prompt = prompt_path.read_bytes()
        prompt_hash = sha256_bytes(prompt)
        if prompt_hash != manifest["prompt_hashes"][case_id]["sha256"]:
            raise RuntimeError(f"FREEZE_VIOLATION: prompt changed for {case_id}")
        slug = "gpt" if provider == "GPT-CLI" else "claude"
        stem = f"{case_id}_run{run}"
        out_dir = V3_ROOT / "raw" / slug
        raw_path = out_dir / f"{stem}.raw"
        meta_path = out_dir / f"{stem}.json"
        log_path = out_dir / "run_log.jsonl"
        if meta_path.exists() and raw_path.exists():
            old = json.loads(meta_path.read_text(encoding="utf-8"))
            if old.get("prompt_text_hash") != prompt_hash or sha256_bytes(raw_path.read_bytes()) != old.get("raw_stdout_sha256"):
                raise RuntimeError(f"existing raw artifact integrity failure: {stem}")
            keyset = _run_log_keys(log_path)
            if (case_id, run) not in keyset:
                _append_jsonl(log_path, {key: old.get(key) for key in (
                    "experiment_id", "system", "case_id", "run", "schedule_index", "model_requested",
                    "model_returned", "cli_version", "timestamp_start_utc", "timestamp_end_utc", "latency_ms",
                    "finish_reason", "output_tokens", "parse_status", "raw_stdout_sha256", "attempts", "transport_failure")})
            continue
        if meta_path.exists() or raw_path.exists():
            raise RuntimeError(f"incomplete raw artifact exists for {stem}; refusing to overwrite")
        executable = codex if provider == "GPT-CLI" else claude
        result = _call_with_retries(provider, executable, prompt, versions[provider])
        for attempt_no, attempt_raw in result.pop("prior_raw"):
            _write_bytes_exclusive(out_dir / "attempts" / f"{stem}_attempt{attempt_no}.raw", attempt_raw)
        _write_bytes_exclusive(raw_path, result["raw_stdout"])
        output_tokens = _output_tokens(result.get("usage"))
        model_returned = result.get("model_returned", "not_available_cli")
        if provider == "Claude-CLI" and not model_returned:
            model_returned = "not_available_cli"
        metadata = {
            "experiment_id": EXPERIMENT_ID, "experiment_status": "FORMAL", "system": provider,
            "case_id": case_id, "case_type": manifest["fixture_hashes"][case_id]["fixture_version"],
            "run": run, "run_id": f"{provider}_{case_id}_run{run}", "schedule_index": row["schedule_index"],
            "model_requested": GPT_MODEL if provider == "GPT-CLI" else CLAUDE_MODEL,
            "model_returned": model_returned, "cli_version": versions[provider],
            "call_path": "codex exec" if provider == "GPT-CLI" else "claude -p --output-format json",
            "prompt_text_hash": prompt_hash, "fixture_hash": manifest["fixture_hashes"][case_id]["canonical_sha256"],
            "fixture_file_sha256": manifest["fixture_hashes"][case_id]["raw_file_sha256"],
            "timestamp_start_utc": result["timestamp_start_utc"], "timestamp_end_utc": result["timestamp_end_utc"],
            "latency_ms": result["latency_ms"], "finish_reason": result["finish_reason"],
            "usage": result["usage"], "output_tokens": output_tokens, "output_limit": "not set",
            "reasoning_effort": "CLI default; not overridden" if provider == "GPT-CLI" else "not applicable / CLI default",
            "raw_stdout_path": _relative(raw_path), "raw_stdout_sha256": result["raw_stdout_sha256"],
            "raw_stdout_bytes": len(result["raw_stdout"]), "raw_text": result["text"],
            "raw_text_sha256": sha256_bytes(result["text"].encode("utf-8")),
            "parse_status": result["parse_status"], "parse_errors": result["parse_errors"],
            "attempts": result["attempts"], "transport_failure": result["transport_failure"],
            "cli_exit_code": result["cli_exit_code"], "fatal_auth_error": result["fatal_auth_error"],
            "isolation": manifest["providers"][provider],
            "sampling_parameters": "not explicitly set by this experiment",
        }
        _json_write_exclusive(meta_path, metadata)
        log_row = {key: metadata[key] for key in (
            "experiment_id", "system", "case_id", "run", "schedule_index", "model_requested", "model_returned",
            "cli_version", "timestamp_start_utc", "timestamp_end_utc", "latency_ms", "finish_reason",
            "output_tokens", "parse_status", "raw_stdout_sha256", "attempts", "transport_failure")}
        _append_jsonl(log_path, log_row)
        completed += 1
        print(json.dumps({"system": provider, "schedule_index": row["schedule_index"], "case_id": case_id,
                          "run": run, "output_tokens": output_tokens, "parse_status": metadata["parse_status"],
                          "transport_failure": metadata["transport_failure"]}, ensure_ascii=False))
        if result["fatal_auth_error"]:
            raise RuntimeError(f"{provider} returned 401; stopping collection without login or retry")
    return {"new_calls": completed, "planned_cli_calls": 60}


def run_builder() -> dict[str, Any]:
    manifest, _ = verify_freeze()
    root = Path(manifest["builder"]["source_root"])
    source_runner = _load_source_runner(root)
    expected = [V3_ROOT / "builder_runs" / case_id / f"run_{run}.json"
                for case_id in manifest["cases"] for run in (1, 2, 3)]
    if any(path.exists() for path in expected):
        raise RuntimeError("Builder output already exists; refusing to overwrite or repeat runs")
    case_files = {case_id: (V3_ROOT / "frozen" / "cases" / f"{case_id}.json").resolve() for case_id in manifest["cases"]}
    records = source_runner.run_builder_pilot(root=V3_ROOT, case_files=case_files)
    return {"builder_runs": len(records), "planned": len(expected), "records_with_trace": sum(bool(row.get("full_trace")) for row in records)}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _evaluation_sources() -> dict[str, Path]:
    return {
        "ChatGPT-web-0916": V2_ROOT / "llm_runs" / "chatgpt",
        "GPT-CLI": V3_ROOT / "raw" / "gpt",
        "Claude-CLI": V3_ROOT / "raw" / "claude",
        "Builder": V3_ROOT / "builder_runs",
    }


def _records_by_key(manifest: dict[str, Any]) -> dict[tuple[str, str, int], tuple[dict[str, Any], Path, str]]:
    data = {}
    for system, folder in _evaluation_sources().items():
        if system == "Builder":
            paths = sorted(folder.glob("*/*.json"))
        elif system == "ChatGPT-web-0916":
            paths = sorted(folder.glob("*.json"))
        else:
            paths = sorted(folder.glob("*.json"))
        for path in paths:
            record = _load_json(path)
            case_id = str(record.get("case_id", ""))
            run = int(record.get("run", record.get("run_id", 0)) or 0)
            if not run and isinstance(record.get("run_id"), str):
                match = re.search(r"run[_-]?(\d+)$", record["run_id"])
                run = int(match.group(1)) if match else 0
            if system == "Builder":
                text = str(record.get("final_result", {}).get("answer", ""))
            elif system == "ChatGPT-web-0916":
                text = str(record.get("response", ""))
            else:
                text = str(record.get("raw_text", ""))
            key = (system, case_id, run)
            if key in data:
                raise ValueError(f"duplicate run record: {system}/{case_id}/{run}")
            data[key] = (record, path, text)
    return data


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def analyze() -> dict[str, Any]:
    manifest, _ = verify_freeze()
    from experiments.baseline_comparison.evaluation.scoring import score_response, structured_agreement

    source = Path(manifest["builder"]["source_root"])
    baseline = _load_source_runner(source)
    cases = manifest["cases"]
    fixture_paths = {case_id: (V3_ROOT / "frozen" / "cases" / f"{case_id}.json").resolve() for case_id in cases}
    fixtures = {case_id: baseline.load_fixture(case_id, root=V3_ROOT, case_files=fixture_paths) for case_id in cases}
    records = _records_by_key(manifest)
    quality_rows = []
    structured: dict[tuple[str, str, int], dict[str, Any]] = {}
    failures = []
    for system in REPORT_SYSTEMS:
        for case_id in cases:
            fixture = fixtures[case_id]
            for run in (1, 2, 3):
                key = (system, case_id, run)
                entry = records.get(key)
                if entry is None:
                    failures.append({"system": system, "case_id": case_id, "run": run, "reason": "missing_record"})
                    continue
                record, path, text = entry
                raw_hash = record.get("raw_text_sha256") or record.get("response_sha256") or sha256_bytes(text.encode("utf-8"))
                parse_status = "EMPTY_OUTPUT" if not text else "OK"
                try:
                    evaluation = score_response(fixture, text)
                    parsed = evaluation.get("parsed", {})
                    if parsed.get("parse_status") == "ambiguous":
                        parse_status = "AMBIGUOUS"
                except Exception as exc:
                    evaluation = {"required_fields_present": False, "required_fields_missing": [],
                                  "context_usage": False, "constraint_satisfaction": False,
                                  "completeness": False, "ground_truth_correctness": "not_applicable",
                                  "unsupported_fact_flags": [], "parsed": {}}
                    parsed = {}
                    parse_status = f"PARSER_ERROR:{type(exc).__name__}"
                    failures.append({"system": system, "case_id": case_id, "run": run,
                                     "reason": f"{type(exc).__name__}: {str(exc)[:240]}"})
                structured[key] = parsed
                result = {
                    "system": system, "domain": CASE_DOMAINS[fixture.payload["domain"]], "case_id": case_id,
                    "run": run, "source_file": path.relative_to(V3_ROOT).as_posix() if path.is_relative_to(V3_ROOT) else str(path),
                    "raw_text_sha256": raw_hash, "parse_status": parse_status,
                    "required_fields_present": evaluation.get("required_fields_present"),
                    "required_fields_missing": evaluation.get("required_fields_missing", []),
                    "context_usage": evaluation.get("context_usage"),
                    "constraint_satisfaction": evaluation.get("constraint_satisfaction"),
                    "completeness": evaluation.get("completeness"),
                    "ground_truth_correctness": evaluation.get("ground_truth_correctness", "not_applicable"),
                    "unsupported_fact_flags": evaluation.get("unsupported_fact_flags", []),
                    "parsed": parsed,
                }
                quality_rows.append(result)

    repeatability_rows = []
    for system in REPORT_SYSTEMS:
        for case_id in cases:
            values = [structured[(system, case_id, run)] for run in (1, 2, 3) if (system, case_id, run) in structured]
            agreement = structured_agreement(values)
            repeatability_rows.append({"system": system, "domain": CASE_DOMAINS[fixtures[case_id].payload["domain"]],
                                       "case_id": case_id, "run_count": agreement["run_count"],
                                       "structured_fields_match": agreement["all_match"],
                                       "compared_fields": ";".join(agreement["compared_fields"])})

    aggregate_rows = []
    process_rows = []
    domain_cases = {domain: [case for case in cases if CASE_DOMAINS[fixtures[case].payload["domain"]] == domain]
                    for domain in ("Customer Support", "Outfit", "Presentation")}
    for system in REPORT_SYSTEMS:
        for domain, case_ids in domain_cases.items():
            subset = [row for row in quality_rows if row["system"] == system and row["domain"] == domain]
            n = len(subset)
            def count(field: str) -> int:
                return sum(row.get(field) is True for row in subset)
            aggregate_rows.append({
                "system": system, "domain": domain, "runs": n,
                "parse_ok": sum(row["parse_status"] in {"OK", "AMBIGUOUS"} for row in subset),
                "parse_empty_or_error": sum(row["parse_status"] == "EMPTY_OUTPUT" or row["parse_status"].startswith("PARSER_ERROR") for row in subset),
                "required_fields_present": count("required_fields_present"),
                "context_usage": count("context_usage"),
                "constraint_satisfaction": count("constraint_satisfaction"),
                "completeness": count("completeness"),
                "ground_truth_correctness": count("ground_truth_correctness") if domain == "Customer Support" else "not_applicable",
                "runs_with_unsupported_facts": sum(bool(row.get("unsupported_fact_flags")) for row in subset),
                "unsupported_fact_flag_count": sum(len(row.get("unsupported_fact_flags") or []) for row in subset),
            })
            case_repeat = [row for row in repeatability_rows if row["system"] == system and row["domain"] == domain]
            repeat_count = sum(row["structured_fields_match"] is True for row in case_repeat)
            if system == "Builder":
                b_records = [records[(system, case, run)][0] for case in case_ids for run in (1, 2, 3) if (system, case, run) in records]
                execution_count = sum(bool(row.get("full_trace")) for row in b_records)
                validation_count = sum(not row.get("errors") for row in b_records)
                process_rows.append({"system": system, "domain": domain, "cases": len(case_ids),
                                     "repeatable_cases": repeat_count, "repeatability_denominator": len(case_ids),
                                     "execution_record": "有", "execution_trace_records": f"{execution_count}/{len(b_records)}",
                                     "pre_execution_validation": "有", "validation_pass_records": f"{validation_count}/{len(b_records)}",
                                     "failure_localization": "有", "failure_localization_evidence": "node-level trace/error fields; no forced failure in the 30 answer-quality runs"})
            else:
                process_rows.append({"system": system, "domain": domain, "cases": len(case_ids),
                                     "repeatable_cases": repeat_count, "repeatability_denominator": len(case_ids),
                                     "execution_record": "不提供", "execution_trace_records": "不提供",
                                     "pre_execution_validation": "不提供", "validation_pass_records": "不提供",
                                     "failure_localization": "不提供", "failure_localization_evidence": "no comparable workflow-runtime artifacts"})

    builder_comparison = []
    for case_id in cases:
        for run in (1, 2, 3):
            old_path = V2_ROOT / "builder_runs" / case_id / f"run_{run}.json"
            new_path = V3_ROOT / "builder_runs" / case_id / f"run_{run}.json"
            if not old_path.is_file() or not new_path.is_file():
                builder_comparison.append({"case_id": case_id, "run": run, "answer_exact_match": "missing",
                                           "evaluation_v2_match": "missing", "old_answer_sha256": "", "new_answer_sha256": ""})
                continue
            old_record, new_record = _load_json(old_path), _load_json(new_path)
            old_answer = str(old_record.get("final_result", {}).get("answer", ""))
            new_answer = str(new_record.get("final_result", {}).get("answer", ""))
            old_score = score_response(fixtures[case_id], old_answer)
            new_score = score_response(fixtures[case_id], new_answer)
            builder_comparison.append({"case_id": case_id, "run": run, "answer_exact_match": old_answer == new_answer,
                                      "evaluation_v2_match": canonical_hash(old_score) == canonical_hash(new_score),
                                      "old_answer_sha256": sha256_bytes(old_answer.encode("utf-8")),
                                      "new_answer_sha256": sha256_bytes(new_answer.encode("utf-8"))})

    results = V3_ROOT / "results"
    _write_csv(results / "answer_quality_by_system_domain.csv",
               ["system", "domain", "runs", "parse_ok", "parse_empty_or_error", "required_fields_present", "context_usage",
                "constraint_satisfaction", "completeness", "ground_truth_correctness", "runs_with_unsupported_facts", "unsupported_fact_flag_count"], aggregate_rows)
    _write_csv(results / "repeatability.csv", ["system", "domain", "case_id", "run_count", "structured_fields_match", "compared_fields"], repeatability_rows)
    _write_csv(results / "process_quality_by_system_domain.csv",
               ["system", "domain", "cases", "repeatable_cases", "repeatability_denominator", "execution_record", "execution_trace_records",
                "pre_execution_validation", "validation_pass_records", "failure_localization", "failure_localization_evidence"], process_rows)
    _write_csv(results / "builder_v2_comparison.csv",
               ["case_id", "run", "answer_exact_match", "evaluation_v2_match", "old_answer_sha256", "new_answer_sha256"], builder_comparison)
    with (results / "case_quality.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in quality_rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    with (results / "parse_failures.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(failures, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    _write_summary(results / "summary.md", manifest, aggregate_rows, process_rows, builder_comparison, failures)
    return {"evaluation_version": "evaluation-v2", "evaluated_runs": len(quality_rows),
            "parse_failures": len(failures), "builder_exact_matches": sum(row.get("answer_exact_match") is True for row in builder_comparison),
            "builder_evaluation_matches": sum(row.get("evaluation_v2_match") is True for row in builder_comparison),
            "summary": str(results / "summary.md")}


def _write_summary(path: Path, manifest: dict[str, Any], quality: list[dict[str, Any]], process: list[dict[str, Any]],
                   builder_comparison: list[dict[str, Any]], failures: list[dict[str, Any]]) -> None:
    lines = [
        "# 三方比较实验 v3（Pilot）结果摘要", "",
        f"Experiment ID: `{manifest['experiment_id']}`。10 个冻结 case，每个系统每个 case 3 次。",
        "Builder 由本地规则程序执行，本轮 Builder 没有调用模型。历史 ChatGPT 数据单独标记为 ChatGPT-web-0916。", "",
        "## A. 答案质量（原始计数）", "",
        "字段为 `通过数/运行数`；支持域的 Ground Truth 指标只适用于 Customer Support。未做综合评分。", "",
        "| 系统 | 领域 | 运行数 | 解析可用 | 必需字段齐全 | 使用上下文 | 满足约束 | 完整 | Ground Truth 正确 | 含 unsupported flag 的运行 | flag 总数 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in quality:
        n = row["runs"]
        def fraction(field: str) -> str:
            value = row[field]
            return "不适用" if value == "not_applicable" else f"{value}/{n}"
        lines.append(f"| {row['system']} | {row['domain']} | {n} | {row['parse_ok']}/{n} | {fraction('required_fields_present')} | {fraction('context_usage')} | {fraction('constraint_satisfaction')} | {fraction('completeness')} | {fraction('ground_truth_correctness')} | {row['runs_with_unsupported_facts']}/{n} | {row['unsupported_fact_flag_count']} |")
    lines += ["", "## B. 流程质量", "", "重复性比较同一 case 三次运行的 evaluation-v2 结构化字段；不是逐字文本相同。能力项是是否提供对应流程工件，不把不提供记为 0。", "",
              "| 系统 | 领域 | 结构化结果一致的 case | 执行记录 | 执行前校验 | 失败定位 |", "|---|---|---:|---|---|---|"]
    for row in process:
        lines.append(f"| {row['system']} | {row['domain']} | {row['repeatable_cases']}/{row['repeatability_denominator']} | {row['execution_record']} | {row['pre_execution_validation']} | {row['failure_localization']} |")
    exact = sum(row.get("answer_exact_match") is True for row in builder_comparison)
    eval_match = sum(row.get("evaluation_v2_match") is True for row in builder_comparison)
    lines += ["", "## Builder 重跑与 9/16 结果", "",
              f"逐条比较 30 个 run：最终答案逐字一致 `{exact}/30`；evaluation-v2 结构化评价一致 `{eval_match}/30`。详细记录见 `builder_v2_comparison.csv`。", "",
              "## 解析失败", "", f"空输出或评价器异常记录 `{len(failures)}` 条，详情见 `parse_failures.json`。字段缺失计入答案质量，不等同于解析器崩溃。", "",
              "## C. 配置成本", "", "本次不测，由后续的复用测试补充。", "",
              "## 调用方式与限制", "",
              "GPT 使用 Codex CLI 的 gpt-6-astra，采用 CLI 默认推理设置；Codex 默认系统指令仍生效，因此与 ChatGPT 网页版不完全相同。",
              "Claude 使用 claude-opus-5-5 的 Claude Code CLI，空 system prompt、无工具、无设置源、无会话持久化；与 Claude 网页版不完全相同。",
              "ChatGPT-web-0916 来自 9 月 16 日网页记录，模型显示为 GPT-5.6 Sol，调用参数和精确后端版本无法获知。",
              "未进行 Human Evaluation，因此不评价自然度、实用性或用户偏好。结论限于这 10 个冻结 case 和本次调用方式。", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Frozen three-way baseline comparison v3")
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--source-root", required=True)
    sub.add_parser("verify")
    sub.add_parser("run-builder")
    sub.add_parser("collect-cli")
    sub.add_parser("analyze")
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            result = freeze_experiment(args.source_root)
        elif args.command == "verify":
            manifest, schedule = verify_freeze()
            result = {"freeze": "PASS", "cases": len(manifest["cases"]), "schedule_rows": len(schedule)}
        elif args.command == "run-builder":
            result = run_builder()
        elif args.command == "collect-cli":
            result = collect_cli()
        else:
            result = analyze()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {str(exc)}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

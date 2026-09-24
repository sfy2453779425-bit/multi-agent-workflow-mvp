"""Claude arm of ac_formal_v2: one fresh, isolated `claude -p` session per call.

Isolation per call:
  - new process, new empty temp working directory (outside the repo)
  - empty system prompt, no tools, no setting sources, no MCP, no session persistence
  - minimal environment (host-session variables such as CLAUDECODE / ANTHROPIC_* are dropped)
  - prompt = frozen canonical user message, passed verbatim on stdin

Outputs are written verbatim and never printed, so the operator does not see model text.

Limits and retries:
  - no output-token cap: the CLI has no flag for it, and CLAUDE_CODE_MAX_OUTPUT_TOKENS=1024 was
    tested and not enforced (1670 output tokens, end_turn). Each call logs output_tokens and
    flags calls above the 1024 reference used for the other models.
  - only timeouts and HTTP 429 / 5xx / 529 are retried (max 3 attempts); anything else,
    including CLI output that is not JSON, is recorded once and not retried

Modes:
  --check-only  verify frozen prompts/hashes and print the call plan (no model calls)
  --probe       one call with a neutral sentence unrelated to any case
  --formal      the 18 scheduled calls; requires tag ac-formal-v2-collect-freeze-r2
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

SCRIPT_VERSION = "claude-cli-runner-v1.2"
OUTPUT_TOKEN_REFERENCE = 1024
EXP_DIR = pathlib.Path(__file__).resolve().parents[1]  # experiments/ac_formal_v2
REPO = EXP_DIR.parents[1]
FREEZE_TAG = "ac-formal-v2-collect-freeze-r2"
PROVIDER_KEY = "claude"

ENV_KEEP = [
    "PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "OS",
    "USERPROFILE", "HOME", "HOMEDRIVE", "HOMEPATH", "USERNAME", "APPDATA", "LOCALAPPDATA",
    "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "TEMP", "TMP",
    "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY", "NODE_EXTRA_CA_CERTS",
]
RETRYABLE_STATUS = {429, 500, 502, 503, 504, 529}
FATAL_STATUS = {400, 401, 403, 404}
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = [15, 45]
CALL_TIMEOUT_SECONDS = 300
PROBE_PROMPT = "Reply with the single word OK."


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def claude_exe():
    found = shutil.which("claude")
    if found:
        return found
    fallback = pathlib.Path.home() / ".local" / "bin" / "claude.exe"
    if fallback.exists():
        return str(fallback)
    sys.exit("claude CLI not found")


def clean_env():
    return {k: os.environ[k] for k in ENV_KEEP if k in os.environ}


def cli_flags(model):
    return [
        "-p",
        "--model", model,
        "--output-format", "json",
        "--system-prompt", "",
        "--tools", "",
        "--setting-sources", "",
        "--strict-mcp-config",
        "--no-session-persistence",
    ]


def cli_version(exe):
    proc = subprocess.run([exe, "--version"], capture_output=True, env=clean_env(), timeout=60)
    return proc.stdout.decode("utf-8", "replace").strip()


def load_plan():
    config = load_json(EXP_DIR / "config" / "freeze_config.json")
    schedule = load_json(EXP_DIR / "config" / "schedule.json")
    calls = sorted(
        (c for c in schedule["calls"] if c["provider"] == PROVIDER_KEY),
        key=lambda c: c["schedule_index"],
    )
    expected = len(config["case_ids"]) * config["runs_per_case_model"]
    if len(calls) != expected:
        sys.exit(f"schedule has {len(calls)} {PROVIDER_KEY} calls, expected {expected}")
    return config, calls


def load_prompt(case_id):
    frozen = load_json(EXP_DIR / "frozen" / "prompts" / f"{case_id}.json")
    messages = frozen["messages"]
    if len(messages) != 1 or messages[0]["role"] != "user":
        sys.exit(f"{case_id}: expected exactly one user message")
    text = messages[0]["content"]
    digest = sha256_bytes(text.encode("utf-8"))
    if digest != frozen["prompt_text_hash"]:
        sys.exit(f"{case_id}: prompt hash mismatch ({digest} != {frozen['prompt_text_hash']})")
    return text, digest


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def check_freeze():
    if git("rev-parse", "-q", "--verify", f"refs/tags/{FREEZE_TAG}").returncode != 0:
        sys.exit(f"tag {FREEZE_TAG} not found; formal run refused")
    for rel in ("experiments/ac_formal_v2/cli_claude/", "experiments/ac_formal_v2/frozen/prompts/",
                "experiments/ac_formal_v2/config/"):
        if git("diff", "--quiet", FREEZE_TAG, "--", rel).returncode != 0:
            sys.exit(f"{rel} differs from {FREEZE_TAG}; formal run refused")


def call_once(exe, model, prompt):
    """One isolated CLI call. Returns (stdout_bytes, stderr_text, exit_code, parsed_or_None, timed_out)."""
    workdir = tempfile.mkdtemp(prefix="acv2_claude_")
    try:
        proc = subprocess.run(
            [exe, *cli_flags(model)],
            input=prompt.encode("utf-8"),
            capture_output=True,
            cwd=workdir,
            env=clean_env(),
            timeout=CALL_TIMEOUT_SECONDS,
        )
        stdout, stderr, code = proc.stdout, proc.stderr.decode("utf-8", "replace"), proc.returncode
    except subprocess.TimeoutExpired:
        return b"", "timeout", None, None, True
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    try:
        parsed = json.loads(stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        parsed = None
    return stdout, stderr, code, parsed, False


def failure_kind(parsed, timed_out):
    if timed_out:
        return "timeout"
    if parsed is None:
        return "cli_output_not_json"
    if parsed.get("is_error"):
        status = parsed.get("api_error_status")
        return f"api_error_{status}" if status else "cli_error"
    return None


def run_call(exe, model, prompt):
    """Retries only timeouts and HTTP 429 / 5xx / 529. Returns (stdout, parsed, attempts, fatal)."""
    attempts = []
    for attempt_no in range(1, MAX_ATTEMPTS + 1):
        stdout, stderr, code, parsed, timed_out = call_once(exe, model, prompt)
        status = parsed.get("api_error_status") if parsed else None
        kind = failure_kind(parsed, timed_out)
        attempts.append({
            "attempt_no": attempt_no,
            "exit_code": code,
            "failure_kind": kind,
            "api_error_status": status,
            "stderr_excerpt": stderr[:500],
        })
        if kind is None:
            return stdout, parsed, attempts, False
        if status in FATAL_STATUS:
            return stdout, parsed, attempts, True
        retryable = timed_out or status in RETRYABLE_STATUS
        if not retryable or attempt_no == MAX_ATTEMPTS:
            return stdout, parsed, attempts, False
        time.sleep(BACKOFF_SECONDS[attempt_no - 1])


def status_line(label, attempts, seconds):
    kind = attempts[-1]["failure_kind"]
    state = "ok" if kind is None else f"FAILED ({kind})"
    return f"{label}: {state}, attempts {len(attempts)}, {seconds:.1f}s"


def model_returned(parsed):
    return sorted((parsed or {}).get("modelUsage", {}).keys())


def do_probe(exe, model):
    out_dir = EXP_DIR / "cli_raw" / "_probe"
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    stdout, parsed, attempts, _ = run_call(exe, model, PROBE_PROMPT)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (out_dir / f"claude_probe_{stamp}.json").write_bytes(stdout)
    print(status_line("probe", attempts, time.monotonic() - started))
    print("model_returned:", model_returned(parsed))
    if parsed:
        usage = parsed.get("usage") or {}
        print("input_tokens:", usage.get("input_tokens"), "output_tokens:", usage.get("output_tokens"))


def do_formal(exe, config, calls):
    check_freeze()
    exp_id = config["experiment_id"]
    model = config["models"][PROVIDER_KEY]
    out_dir = EXP_DIR / "cli_raw" / exp_id / PROVIDER_KEY
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = [c for c in calls if (out_dir / f"{c['case_id']}_run{c['run_id']}.json").exists()]
    if existing:
        sys.exit(f"{len(existing)} output files already exist; refusing to overwrite")
    version = cli_version(exe)
    log_path = out_dir / "run_log.jsonl"
    for call in calls:
        case_id, run_id = call["case_id"], call["run_id"]
        prompt, prompt_hash = load_prompt(case_id)
        started_utc, started = utc_now(), time.monotonic()
        stdout, parsed, attempts, fatal = run_call(exe, model, prompt)
        elapsed = time.monotonic() - started
        out_file = out_dir / f"{case_id}_run{run_id}.json"
        out_file.write_bytes(stdout)
        entry = {
            "experiment_id": exp_id,
            "case_id": case_id,
            "run_id": run_id,
            "schedule_index": call["schedule_index"],
            "schedule_seed": call["schedule_seed"],
            "provider": "anthropic",
            "call_path": "claude_code_cli_print",
            "runner_version": SCRIPT_VERSION,
            "cli_version": version,
            "cli_flags": cli_flags(model),
            "isolation": "fresh process, empty temp cwd, clean env, empty system prompt, no tools",
            "model_requested": model,
            "model_returned": model_returned(parsed),
            "prompt_text_hash": prompt_hash,
            "timestamp_start_utc": started_utc,
            "timestamp_end_utc": utc_now(),
            "latency_ms": round(elapsed * 1000),
            "attempts": attempts,
            "failure_kind": attempts[-1]["failure_kind"],
            "transport_failure": attempts[-1]["failure_kind"] is not None,
            "max_output_tokens": "not_enforceable_cli",
            "output_tokens_over_reference": (
                ((parsed or {}).get("usage") or {}).get("output_tokens", 0) > OUTPUT_TOKEN_REFERENCE
            ),
            "stdout_file": out_file.name,
            "stdout_sha256": sha256_bytes(stdout),
            "usage": (parsed or {}).get("usage"),
            "stop_reason": (parsed or {}).get("stop_reason"),
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(status_line(f"#{call['schedule_index']:02d} {case_id} run{run_id}", attempts, elapsed))
        if fatal:
            sys.exit("non-retryable API error; stopping (no further calls)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--probe", action="store_true")
    mode.add_argument("--formal", action="store_true")
    args = parser.parse_args()

    config, calls = load_plan()
    exe = claude_exe()
    model = config["models"][PROVIDER_KEY]

    if args.check_only:
        for case_id in config["case_ids"]:
            _, digest = load_prompt(case_id)
            print(f"{case_id}: prompt hash OK {digest[:12]}")
        print("cli:", exe, "|", cli_version(exe))
        print("plan:", " ".join(f"#{c['schedule_index']}:{c['case_id']}/r{c['run_id']}" for c in calls))
    elif args.probe:
        do_probe(exe, model)
    else:
        do_formal(exe, config, calls)


if __name__ == "__main__":
    main()

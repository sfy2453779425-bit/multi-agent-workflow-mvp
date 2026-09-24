from __future__ import annotations

from copy import deepcopy
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
V4 = ROOT / "experiments" / "authoritative_contract" / "pilot_v4"
EQ_DIR = ROOT / "experiments" / "authoritative_contract" / "prompt_equality_pilot_v1"
CASES_PATH = V4 / "cases_v1.json"
POLICY_PATH = ROOT / "data" / "support_policy.json"
WORKFLOW_PATH = V4 / "workflow_v1.json"
FIXTURE_HASHES_PATH = V4 / "fixture_hashes_v1.json"
V4_PROMPT_HASHES_PATH = V4 / "prompt_hashes_v1.json"
EQUALITY_RESULTS_PATH = EQ_DIR / "equality_results.csv"

EXPERIMENT_ID = "ac_formal_3model_6case_20260924_v2"
COLLECTION_FREEZE_TAG = "ac-formal-v2-collect-freeze-r2"
SEED = 20260924
CASE_IDS = ("CS01", "CS04", "CS06", "CS08", "CS10", "CS12")
PROVIDERS = (
    ("deepseek", "deepseek-v4-pro"),
    ("gpt", "gpt-6-astra"),
    ("claude", "claude-opus-5-5"),
)

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from experiments.authoritative_contract.pilot import pilot as core  # noqa: E402
from agent_builder.generative_provider import (  # noqa: E402
    PARSE_FAILED,
    PARSE_OK,
    RawGenerationResult,
    customer_message_prompt_evidence,
    parse_candidate,
)
from agent_builder.responses_provider import (  # noqa: E402
    DeepSeekResponsesProvider,
    RESPONSES_DEFAULT_MAX_OUTPUT_TOKENS,
    RESPONSES_PROVIDER_ADAPTER_VERSION,
    RESPONSES_PROVIDER_CONFIG_VERSION,
)
from agent_builder.workflow_runtime import WORKFLOW_RUNTIME_VERSION  # noqa: E402


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_text(canonical_json(value))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_immutable(path: Path, value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"immutable artifact differs: {path.relative_to(ROOT)}")
        return
    path.write_text(text, encoding="utf-8", newline="\n")


def copy_immutable(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    if target.exists():
        if target.read_bytes() != data:
            raise RuntimeError(f"immutable artifact differs: {target.relative_to(ROOT)}")
        return
    target.write_bytes(data)


def build_schedule(seed: int = SEED) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    for run_id in (1, 2, 3):
        round_rows = [
            {"case_id": case_id, "provider": provider, "model_requested": model, "run_id": run_id}
            for case_id in CASE_IDS
            for provider, model in PROVIDERS
        ]
        rng.shuffle(round_rows)
        for row in round_rows:
            rows.append({**row, "schedule_index": len(rows) + 1, "schedule_seed": seed})
    return rows


def _read_equality_prompt_hashes() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    frozen = BASE / "frozen" / "equality_pilot_prompt_hashes.json"
    if frozen.is_file():
        rows = load_json(frozen).get("items", [])
        for row in rows:
            case_id = row.get("case_id")
            if case_id in {"CS01", "CS10", "CS12"}:
                result[case_id] = {
                    key: row.get(key)
                    for key in (
                        "generation_input_hash_equal",
                        "prompt_text_hash_equal",
                        "c_prompt_text_hash",
                        "d_prompt_text_hash",
                    )
                }
        return result
    with EQUALITY_RESULTS_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            case_id = row.get("case_id")
            if case_id not in {"CS01", "CS10", "CS12"}:
                continue
            result[case_id] = {
                "generation_input_hash_equal": row.get("generation_input_hash_equal"),
                "prompt_text_hash_equal": row.get("prompt_text_hash_equal"),
                "c_prompt_text_hash": row.get("c_prompt_text_hash"),
                "d_prompt_text_hash": row.get("d_prompt_text_hash"),
            }
    return result


def _prompt_hash_map(path: Path) -> dict[str, str]:
    payload = load_json(path)
    return {
        item["case_id"]: item["prompt_hash"]
        for item in payload["items"]
        if item.get("condition") == "D_proposed_runtime" and int(item.get("run_id", 1)) == 1
    }


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _source_hashes() -> dict[str, str]:
    paths = {
        "workflow_runtime": ROOT / "src" / "agent_builder" / "workflow_runtime.py",
        "validator_parser": ROOT / "src" / "agent_builder" / "generative_provider.py",
        "provider_adapter": ROOT / "src" / "agent_builder" / "responses_provider.py",
        "node_registry": ROOT / "src" / "agent_builder" / "node_registry.py",
        "workflow_schema": ROOT / "src" / "agent_builder" / "workflow_schema.py",
        "workflow_engine": ROOT / "src" / "agent_builder" / "workflow.py",
        "prompt_and_runtime_helper": ROOT / "experiments" / "authoritative_contract" / "pilot" / "pilot.py",
    }
    return {name: sha256_file(path) for name, path in paths.items()}


def _tool_hashes() -> dict[str, str]:
    paths = (
        BASE / "common.py",
        BASE / "collect.py",
        BASE / "replay.py",
        BASE / "tests" / "test_tools.py",
        BASE / "tests" / "test_cli_tools.py",
        BASE / "cli_gpt" / "run_gpt_cli.py",
        BASE / "import_cli.py",
        BASE / "cli_claude" / "run_claude_cli.py",
        BASE / "README.md",
        BASE / "DEVIATIONS.md",
    )
    return {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths}


def prepare() -> dict[str, Any]:
    """Export frozen prompts and schedule without invoking any provider."""
    raw_payload = load_json(CASES_PATH)
    raw_cases = {item["case_id"]: item for item in raw_payload["cases"]}
    core.CASES_PATH = CASES_PATH
    core.WORKFLOW_PATH = WORKFLOW_PATH
    cases, payload = core.load_cases()
    policy = load_json(POLICY_PATH)
    fixture_hashes = load_json(FIXTURE_HASHES_PATH)["items"]
    prior_prompt_hashes = _prompt_hash_map(V4_PROMPT_HASHES_PATH)
    equality_hashes = _read_equality_prompt_hashes()
    policy_hash = sha256_json(policy)
    workflow_hash = sha256_file(WORKFLOW_PATH)
    prompt_records: list[dict[str, Any]] = []
    failures: list[str] = []

    for case in cases:
        case_id = case["case_id"]
        fixture_hash = core._fixture_hash(case)
        if fixture_hashes.get(case_id) != fixture_hash:
            failures.append(f"{case_id}: fixture hash mismatch")
        info = core.build_condition_prompt(case, policy, "C_prompt_only_hybrid")
        d_info = core.build_condition_prompt(case, policy, "D_proposed_runtime")
        generation_evidence = customer_message_prompt_evidence(
            info["grounding_projection"], info["generation_contract"], info["request_context"]
        )
        prompt_hash = generation_evidence["prompt_text_hash"]
        generation_hash = generation_evidence["generation_input_hash"]
        if info["prompt"] != d_info["prompt"]:
            failures.append(f"{case_id}: C/D canonical prompt mismatch")
        if prior_prompt_hashes.get(case_id) != prompt_hash:
            failures.append(f"{case_id}: frozen pilot prompt hash mismatch")
        equality_ref = equality_hashes.get(case_id)
        equality_status = "NOT_RECORDED"
        if equality_ref:
            if equality_ref.get("prompt_text_hash_equal") != "True":
                failures.append(f"{case_id}: Equality Pilot did not record prompt equality")
            if equality_ref.get("c_prompt_text_hash") != prompt_hash or equality_ref.get("d_prompt_text_hash") != prompt_hash:
                failures.append(f"{case_id}: Equality Pilot prompt hash mismatch")
            equality_status = "PASS"
        raw_case = raw_cases[case_id]
        case_hash = sha256_json(raw_case)
        record = {
            "case_id": case_id,
            "case_type": case["label"],
            "case": deepcopy(case),
            "case_hash": case_hash,
            "fixture_hash": fixture_hash,
            "policy_hash": policy_hash,
            "workflow_hash": workflow_hash,
            "prompt_builder_version": generation_evidence["prompt_builder_version"],
            "prompt_builder_hash": generation_evidence["prompt_builder_hash"],
            "generation_input": generation_evidence["generation_input"],
            "generation_input_hash": generation_hash,
            "prompt_text": info["prompt"],
            "messages": [{"role": "user", "content": info["prompt"]}],
            "prompt_text_hash": prompt_hash,
            "provider_request_prompt_hash": sha256_text(info["prompt"]),
            "pilot_v4_prompt_hash_match": prior_prompt_hashes.get(case_id) == prompt_hash,
            "equality_pilot_hash_status": equality_status,
            "equality_pilot_prompt_hashes": equality_ref,
        }
        prompt_records.append(record)

    prompt_hash_payload = {
        "experiment_id": EXPERIMENT_ID,
        "prompt_version": prompt_records[0]["prompt_builder_version"],
        "items": [
            {
                "case_id": item["case_id"],
                "case_hash": item["case_hash"],
                "fixture_hash": item["fixture_hash"],
                "prompt_text_hash": item["prompt_text_hash"],
                "provider_request_prompt_hash": item["provider_request_prompt_hash"],
                "pilot_v4_prompt_hash_match": item["pilot_v4_prompt_hash_match"],
                "equality_pilot_hash_status": item["equality_pilot_hash_status"],
                "equality_pilot_prompt_hashes": item["equality_pilot_prompt_hashes"],
            }
            for item in prompt_records
        ],
    }
    equality_payload = {
        "items": [
            {"case_id": case_id, **equality_hashes[case_id]}
            for case_id in sorted(equality_hashes)
        ]
    }
    write_json_immutable(BASE / "frozen" / "equality_pilot_prompt_hashes.json", equality_payload)
    write_json_immutable(BASE / "frozen" / "prompt_hashes.json", prompt_hash_payload)
    if failures:
        raise RuntimeError("FREEZE_VIOLATION: " + "; ".join(failures))

    for item in prompt_records:
        write_json_immutable(BASE / "frozen" / "prompts" / f"{item['case_id']}.json", item)
    copy_immutable(POLICY_PATH, BASE / "frozen" / "support_policy.json")
    copy_immutable(WORKFLOW_PATH, BASE / "frozen" / "workflow_v1.json")

    config = {
        "experiment_id": EXPERIMENT_ID,
        "phase": "formal_collection_preparation",
        "case_ids": list(CASE_IDS),
        "runs_per_case_model": 3,
        "planned_calls": 54,
        "schedule_seed": SEED,
        "models": {provider: model for provider, model in PROVIDERS},
        "provider": {
            "deepseek": {
                "api_format": "responses",
                "adapter_version": RESPONSES_PROVIDER_ADAPTER_VERSION,
                "config_version": RESPONSES_PROVIDER_CONFIG_VERSION,
                "model": "deepseek-v4-pro",
                "reasoning_effort": "none",
                "max_output_tokens": RESPONSES_DEFAULT_MAX_OUTPUT_TOKENS,
                "sampling_parameters": "not_set_provider_default",
            },
            "gpt": {
                "api_format": "codex_cli_exec",
                "call_path": "codex_cli_exec",
                "provider_config_version": "codex-cli-gpt6-isolated-v1",
                "model": "gpt-6-astra",
                "reasoning_effort": "low",
                "max_output_tokens": 1024,
                "sampling_parameters": "not_set_provider_default",
                "fresh_session_per_call": True,
                "sandbox": "read-only",
                "model_instructions": "codex_cli_default_unmodified",
                "tools": "disabled",
            },
            "claude": {
                "api_format": "claude_code_cli",
                "call_path": "claude_code_cli_print",
                "provider_config_version": "claude-code-cli-v1",
                "model": "claude-opus-5-5",
                "max_tokens": 1024,
                "max_tokens_enforced_by_current_runner": False,
                "max_tokens_note": "cli_claude runner does not pass a token limit",
                "extended_thinking": "not_enabled",
                "sampling_parameters": "not_set_provider_default",
                "fresh_session_per_call": True,
            },
        },
        "runtime_version": WORKFLOW_RUNTIME_VERSION,
        "validator_version": "consistency-validator-v1.1",
        "sampling_parameters": "not_set_provider_default",
        "temperature": None,
        "top_p": None,
        "seed": None,
        "exact_backend_revision": None,
        "raw_artifacts_immutable": True,
    }
    write_json_immutable(BASE / "config" / "freeze_config.json", config)
    schedule = build_schedule()
    schedule_hash = sha256_json(schedule)
    write_json_immutable(BASE / "config" / "schedule.json", {
        "seed": SEED,
        "schedule_hash": schedule_hash,
        "calls": schedule,
    })
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "status": "PREPARED_SMOKE_PENDING",
        "created_from_commit": _git_commit(),
        "worktree_dirty": True,
        "case_count": len(CASE_IDS),
        "model_count": len(PROVIDERS),
        "runs_per_case_model": 3,
        "planned_calls": len(schedule),
        "schedule_hash": schedule_hash,
        "policy_hash": policy_hash,
        "workflow_hash": workflow_hash,
        "source_hashes": _source_hashes(),
        "tool_hashes": _tool_hashes(),
        "input_hashes": {
            "cases": sha256_file(CASES_PATH),
            "fixture_hashes": sha256_file(FIXTURE_HASHES_PATH),
            "pilot_prompt_hashes": sha256_file(V4_PROMPT_HASHES_PATH),
            "equality_prompt_hashes": sha256_json(equality_payload),
            "policy": sha256_file(POLICY_PATH),
            "workflow": workflow_hash,
        },
        "frozen_artifact_hashes": {
            path.relative_to(ROOT).as_posix(): sha256_file(path)
            for path in sorted((BASE / "frozen").rglob("*"))
            if path.is_file()
        } | {
            path.relative_to(ROOT).as_posix(): sha256_file(path)
            for path in (BASE / "config" / "freeze_config.json", BASE / "config" / "schedule.json")
        },
        "prompt_builder_version": prompt_records[0]["prompt_builder_version"],
        "prompt_builder_hash": prompt_records[0]["prompt_builder_hash"],
        "prompt_hashes_verified": True,
        "equality_pilot_case_hashes_verified": sorted(equality_hashes),
        "fixture_hashes_verified": True,
    }
    write_json_immutable(BASE / "manifest.json", manifest)
    return {"manifest": manifest, "config": config, "schedule": schedule, "prompt_hashes": prompt_hash_payload}


def prompt_for(case_id: str) -> dict[str, Any]:
    if case_id == "SMOKE01":
        policy = load_json(BASE / "frozen" / "support_policy.json")
        delivery = next(item for item in policy["categories"] if item["id"] == "delivery")
        case = {
            "case_id": "SMOKE01",
            "label": "Synthetic ordinary inquiry",
            "request": "Could you tell me how to check the latest status of my package?",
            "authoritative": {
                "ticket_category": "delivery",
                "priority": delivery["priority"],
                "sla": delivery["sla"],
                "owner_team": delivery["owner_team"],
            },
            "pilot_version": "ac-formal-smoke-v1",
            "fixture_version": "ac-formal-smoke-fixture-v1",
            "support_policy_path": "data/support_policy.json",
        }
        info = core.build_condition_prompt(case, policy, "C_prompt_only_hybrid")
        evidence = customer_message_prompt_evidence(
            info["grounding_projection"], info["generation_contract"], info["request_context"]
        )
        return {
            "case_id": "SMOKE01",
            "case_type": "Synthetic ordinary inquiry",
            "case": case,
            "case_hash": sha256_json(case),
            "fixture_hash": sha256_json(case),
            "policy_hash": sha256_json(policy),
            "generation_input": evidence["generation_input"],
            "generation_input_hash": evidence["generation_input_hash"],
            "prompt_text": info["prompt"],
            "messages": [{"role": "user", "content": info["prompt"]}],
            "prompt_text_hash": info["prompt_hash"],
            "provider_request_prompt_hash": sha256_text(info["prompt"]),
        }
    if case_id not in CASE_IDS:
        raise ValueError(f"case not in frozen set: {case_id}")
    return load_json(BASE / "frozen" / "prompts" / f"{case_id}.json")


def frozen_policy() -> dict[str, Any]:
    return load_json(BASE / "frozen" / "support_policy.json")


def frozen_workflow_path() -> Path:
    return BASE / "frozen" / "workflow_v1.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def json_safe(value: Any) -> Any:
    if isinstance(value, dict) or hasattr(value, "items"):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [json_safe(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return json_safe(value.__dict__)
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def runtime_result_fields(context: dict[str, Any]) -> dict[str, Any]:
    evidence = context.get("field_evidence", [])
    rejected_reasons = [
        str(item.get("reason"))
        for item in evidence
        if isinstance(item, dict) and item.get("accepted") is False and item.get("reason")
    ]
    fallback = bool(context.get("fallback_used"))
    return {
        "decision": "REJECT" if fallback else "ACCEPT",
        "reject_reason_codes": list(dict.fromkeys(rejected_reasons)),
        "fallback_used": fallback,
        "fallback_reason": context.get("fallback_reason"),
        "final_output": context.get("customer_message"),
        "candidate": json_safe(context.get("raw_candidates", {}).get("response_generation")),
        "parse_status": context.get("raw_responses", {}).get("response_generation", {}).get("parse_status"),
        "consistency_results": json_safe(context.get("consistency_results", {}).get("response_generation")),
        "field_evidence": json_safe(evidence),
    }


def assert_frozen_source_hashes(manifest: dict[str, Any]) -> None:
    current = _source_hashes()
    if current != manifest.get("source_hashes"):
        raise RuntimeError("FREEZE_VIOLATION: frozen source hash changed")
    if _tool_hashes() != manifest.get("tool_hashes"):
        raise RuntimeError("FREEZE_VIOLATION: collection tooling hash changed")
    for relative, expected in manifest.get("frozen_artifact_hashes", {}).items():
        path = ROOT / Path(relative)
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"FREEZE_VIOLATION: frozen artifact changed: {relative}")


def assert_collection_freeze_tag() -> None:
    tag = f"refs/tags/{COLLECTION_FREEZE_TAG}"
    exists = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "-q", "--verify", tag],
        capture_output=True, text=True, check=False,
    )
    if exists.returncode != 0:
        raise RuntimeError(f"formal collection requires tag {COLLECTION_FREEZE_TAG}")
    path = "experiments/ac_formal_v2/"
    for diff_args in (("diff", "--quiet", tag, "--", path), ("diff", "--cached", "--quiet", tag, "--", path)):
        result = subprocess.run(["git", "-C", str(ROOT), *diff_args], capture_output=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"FREEZE_VIOLATION: {path} differs from {COLLECTION_FREEZE_TAG}")


def redact_secret_text(text: str) -> str:
    result = text
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
        secret = os.environ.get(name)
        if secret:
            result = result.replace(secret, "[REDACTED]")
    return result

"""Prepare, execute, and analyze the six-case E1 pilot.

The runner keeps C as a prompt-only condition: parsed extra fields are retained
and flow into the final artifact. Only D uses the frozen Runtime gate/fallback.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from agent_builder import (  # noqa: E402
    DeepSeekCandidateProvider,
    NodeRegistry,
    ProviderGenerativeNode,
    RawGenerationResult,
    WorkflowRuntime,
    WORKFLOW_RUNTIME_VERSION,
    build_customer_support_prompt,
    create_authoritative_snapshot,
)
from agent_builder.generative_provider import (  # noqa: E402
    PARSE_FAILED,
    PARSE_OK,
    ProviderResponseError,
)
import agent_builder.workflow_runtime as runtime_module  # noqa: E402


PILOT_ROOT = Path(__file__).resolve().parent
CASES_PATH = PILOT_ROOT / "cases_v1.json"
WORKFLOW_PATH = PILOT_ROOT / "workflow_v1.json"
MANIFEST_PATH = PILOT_ROOT.parent / "manifest.json"
RAW_ROOT = PILOT_ROOT / "raw"
PARSED_ROOT = PILOT_ROOT / "parsed"
EVIDENCE_ROOT = PILOT_ROOT / "runtime_evidence"
EVALUATION_ROOT = PILOT_ROOT / "evaluation"
PROMPTS_ROOT = PILOT_ROOT / "prompts"
PROMPT_HASHES_PATH = PILOT_ROOT / "prompt_hashes_v1.json"
FIXTURE_HASHES_PATH = PILOT_ROOT / "fixture_hashes_v1.json"

EXPERIMENT_ID = "authoritative_contract_pilot_20260918_v2"
PILOT_VERSION = "pilot-v2"
PROMPT_VERSION = "authoritative-contract-pilot-prompt-v2"
PROVIDER_ADAPTER_VERSION = "deepseek-anthropic-adapter-v1"
CONDITIONS = ("A_direct_llm", "C_prompt_only_hybrid", "D_proposed_runtime")
PILOT_CASE_IDS = ("CS01", "CS04", "CS06", "CS08", "CS10", "CS12")
AUTHORITATIVE_FIELDS = ("priority", "sla", "owner_team")
ALL_DIRECT_FIELDS = ("priority", "sla", "owner_team", "customer_message")
NOT_APPLICABLE = "NOT_APPLICABLE"


def _json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if hasattr(value, "items"):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _canonical(value: Any) -> str:
    return json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_text(_canonical(value))


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_cases() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = _load(CASES_PATH)
    cases = []
    for raw in payload["cases"]:
        case = deepcopy(raw)
        case["pilot_version"] = payload["pilot_version"]
        case["fixture_version"] = payload["fixture_version"]
        case["support_policy_path"] = payload["support_policy_path"]
        cases.append(case)
    if tuple(case["case_id"] for case in cases) != PILOT_CASE_IDS:
        raise ValueError("pilot cases must remain CS01, CS04, CS06, CS08, CS10, CS12")
    truths = {tuple(sorted(_json_safe(case["authoritative"].items()))) for case in cases}
    if len(truths) != 1:
        raise ValueError("all E1 pilot cases must share the frozen authoritative facts")
    return cases, payload


def _policy_path(payload: dict[str, Any]) -> Path:
    return ROOT / payload["support_policy_path"]


def _category(policy: dict[str, Any], ticket_category: str) -> dict[str, Any]:
    return next(item for item in policy["categories"] if item["id"] == ticket_category)


def _policy_context(policy: dict[str, Any], ticket_category: str) -> dict[str, Any]:
    """Expose process policy without leaking the case's expected field values."""

    category = _category(policy, ticket_category)
    known_teams = runtime_module._policy_owner_teams(policy)
    return {
        "category": category["id"],
        "label": category.get("label", ""),
        "policy": category.get("policy", ""),
        "next_actions": list(category.get("next_actions") or []),
        "known_owner_teams": known_teams,
    }


def _generation_contract(case: dict[str, Any], condition: str) -> dict[str, Any]:
    if condition == "A_direct_llm":
        fields = list(ALL_DIRECT_FIELDS)
    else:
        fields = ["customer_message"]
    return {
        "allowed_output_fields": fields,
        "fixture_version": case.get("fixture_version", "authoritative-contract-pilot-fixture-v1"),
        "runtime_version": WORKFLOW_RUNTIME_VERSION,
        "schema_version": 2,
        "prompt_version": PROMPT_VERSION,
        "provider_adapter_version": PROVIDER_ADAPTER_VERSION,
        "max_tokens": 256,
    }


def build_condition_prompt(
    case: dict[str, Any],
    policy: dict[str, Any],
    condition: str,
) -> dict[str, Any]:
    """Build the exact frozen prompt inputs for one case and condition."""

    if condition not in CONDITIONS:
        raise ValueError(f"unknown pilot condition: {condition}")
    authoritative = case["authoritative"]
    request_context = {
        "user_input": case["request"],
        "ticket_category": authoritative["ticket_category"],
        "support_policy": _policy_context(policy, authoritative["ticket_category"]),
    }
    if condition == "A_direct_llm":
        projection = {
            "request_context": deepcopy(request_context),
            "authoritative_facts": {},
            "fields": {},
            "canonical_json": "{}",
            "sha256": NOT_APPLICABLE,
        }
    else:
        snapshot = create_authoritative_snapshot(authoritative)
        projection = runtime_module._create_grounding_projection(
            snapshot,
            list(AUTHORITATIVE_FIELDS),
            request_context,
        )
    contract = _generation_contract(case, condition)
    prompt = build_customer_support_prompt(projection, contract, request_context)
    return {
        "prompt": prompt,
        "prompt_hash": _sha256_text(prompt),
        "prompt_version": PROMPT_VERSION,
        "generation_contract": contract,
        "request_context": request_context,
        "grounding_projection": projection,
        "grounding_hash": projection["sha256"],
    }


class _RecordingProvider:
    """Expose a provider exception to the experiment logger without changing Runtime."""

    provider = "deepseek"

    def __init__(self, provider: Any):
        self.inner = provider
        self.model = getattr(provider, "model", "unavailable")
        self.last_error: Exception | None = None

    def generate(self, grounding_projection, generation_contract, request_context):
        self.last_error = None
        try:
            return self.inner.generate(
                grounding_projection,
                generation_contract,
                request_context,
            )
        except Exception as exc:
            self.last_error = exc
            raise


def _build_runtime(
    case: dict[str, Any],
    policy: dict[str, Any],
    provider: Any,
) -> WorkflowRuntime:
    config = _load(WORKFLOW_PATH)
    authoritative = case["authoritative"]
    category = _category(policy, authoritative["ticket_category"])
    generation_contract = _generation_contract(case, "D_proposed_runtime")
    registry = NodeRegistry()
    registry.register(
        "classification",
        lambda context, node_config: {
            "ticket_category": authoritative["ticket_category"],
            "policy": category["policy"],
        },
    )
    registry.register(
        "routing_decision",
        lambda context, node_config: {
            "owner_team": authoritative["owner_team"],
            "priority": authoritative["priority"],
            "sla": authoritative["sla"],
        },
    )
    registry.register(
        "response_generation",
        ProviderGenerativeNode(provider, generation_contract),
    )
    return WorkflowRuntime(config, registry)


def _failure_kind(error: Exception) -> str:
    if isinstance(error, ProviderResponseError):
        return error.provider_status
    if isinstance(error, HTTPError):
        return "PROVIDER_FAILED"
    if isinstance(error, (URLError, TimeoutError, ConnectionError, socket.timeout, OSError)):
        return "NETWORK_FAILED"
    lowered = str(error).casefold()
    if any(term in lowered for term in ("timed out", "timeout", "connection", "network")):
        return "NETWORK_FAILED"
    return "PROVIDER_FAILED"


def _error_text(error: Exception) -> str:
    text = str(error)
    for name in ("DEEPSEEK_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        secret = __import__("os").environ.get(name)
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text


def _semantic_result(
    message: Any,
    authoritative: dict[str, Any],
    known_teams: list[str],
) -> tuple[Any, Any]:
    if not isinstance(message, str) or not message.strip():
        return NOT_APPLICABLE, NOT_APPLICABLE
    checks = runtime_module._aggregate_consistency(
        {
            "priority": runtime_module._priority_consistency(
                message, authoritative["priority"]
            ),
            "sla": runtime_module._sla_consistency(message, authoritative["sla"]),
            "owner_team": runtime_module._owner_team_consistency(
                message,
                authoritative["owner_team"],
                known_teams,
            ),
        }
    )
    return checks.get("overall"), checks


def _field_correctness(candidate: dict[str, Any], authoritative: dict[str, Any]) -> dict[str, str]:
    return {
        field: (
            "UNRESOLVED"
            if field not in candidate
            else "PASS"
            if candidate[field] == authoritative[field]
            else "FAIL"
        )
        for field in AUTHORITATIVE_FIELDS
    }


def _required_complete(candidate: dict[str, Any]) -> bool:
    return all(field in candidate for field in ALL_DIRECT_FIELDS) and isinstance(
        candidate.get("customer_message"), str
    )


def _record_from_outcome(
    *,
    case: dict[str, Any],
    policy_hash: str,
    fixture_hash: str,
    condition: str,
    run_id: int,
    attempt_id: str,
    prompt_info: dict[str, Any],
    provider: str,
    model: str,
    timestamp: str,
    status: str,
    error: str,
    raw_response: str | None,
    raw_metadata: dict[str, Any],
    parsed_candidate: dict[str, Any],
    parse_status: str,
    runtime_decision: str,
    candidate_checks: Any,
    final_checks: Any,
    final_candidate: dict[str, Any],
    final_output: str,
    fallback_used: Any,
    unauthorized_attempt: Any,
    accepted_unauthorized_write: Any,
    runtime_evidence: Any,
    trace: Any,
) -> dict[str, Any]:
    candidate_status = (
        candidate_checks.get("overall")
        if isinstance(candidate_checks, dict)
        else NOT_APPLICABLE
    )
    final_status = (
        final_checks.get("overall") if isinstance(final_checks, dict) else NOT_APPLICABLE
    )
    raw_hash = _sha256_text(raw_response) if isinstance(raw_response, str) else NOT_APPLICABLE
    provider_status = raw_metadata.get("provider_status", status)
    candidate_available = bool(raw_response and raw_response.strip())
    return {
        "experiment_id": EXPERIMENT_ID,
        "pilot_version": PILOT_VERSION,
        "case_id": case["case_id"],
        "condition": condition,
        "run_id": run_id,
        "attempt_id": attempt_id,
        "replacement_for": NOT_APPLICABLE,
        "provider": provider,
        "model": model,
        "timestamp": timestamp,
        "prompt_version": prompt_info["prompt_version"],
        "prompt_hash": prompt_info["prompt_hash"],
        "fixture_version": case.get("fixture_version", "authoritative-contract-pilot-fixture-v1"),
        "fixture_hash": fixture_hash,
        "policy_hash": policy_hash,
        "grounding_hash": prompt_info["grounding_hash"],
        "raw_response": raw_response,
        "raw_response_hash": raw_hash,
        "raw_model_text": raw_response if candidate_available else None,
        "candidate_available": candidate_available,
        "provider_status": provider_status,
        "provider_payload": deepcopy(raw_metadata.get("provider_payload", NOT_APPLICABLE)),
        "raw_response_body": raw_metadata.get("raw_response_body", NOT_APPLICABLE),
        "raw_response_body_hash": raw_metadata.get("raw_response_body_hash", NOT_APPLICABLE),
        "extraction_status": raw_metadata.get("extraction_status", NOT_APPLICABLE),
        "extraction_path": raw_metadata.get("extraction_path", NOT_APPLICABLE),
        "thinking_mode": raw_metadata.get("thinking_mode", NOT_APPLICABLE),
        "reasoning_effort": raw_metadata.get("reasoning_effort", NOT_APPLICABLE),
        "max_tokens": raw_metadata.get("max_tokens", NOT_APPLICABLE),
        "temperature": raw_metadata.get("temperature", NOT_APPLICABLE),
        "top_p": raw_metadata.get("top_p", NOT_APPLICABLE),
        "provider_config_version": raw_metadata.get("provider_config_version", NOT_APPLICABLE),
        "raw_provider_metadata": raw_metadata,
        "parsed_candidate": parsed_candidate,
        "parse_status": parse_status,
        "runtime_decision": runtime_decision,
        "candidate_consistency_results": candidate_checks,
        "final_consistency_results": final_checks,
        "candidate_semantic_conflict": (
            candidate_status == "CONFLICT" if candidate_status != NOT_APPLICABLE else NOT_APPLICABLE
        ),
        "final_semantic_conflict": (
            final_status == "CONFLICT" if final_status != NOT_APPLICABLE else NOT_APPLICABLE
        ),
        "fallback_used": fallback_used,
        "unauthorized_attempt": unauthorized_attempt,
        "accepted_unauthorized_write": accepted_unauthorized_write,
        "final_candidate": final_candidate,
        "final_output": final_output,
        "authoritative_field_correctness": _field_correctness(final_candidate, case["authoritative"]),
        "required_output_complete": _required_complete(final_candidate),
        "parse_success": parse_status == PARSE_OK,
        "final_unresolved": (
            final_status == "UNRESOLVED" if final_status != NOT_APPLICABLE else NOT_APPLICABLE
        ),
        "status": status,
        "error": error or NOT_APPLICABLE,
        "runtime_evidence": runtime_evidence,
        "trace": trace,
    }


def _base_error_result(
    case: dict[str, Any],
    policy_hash: str,
    fixture_hash: str,
    condition: str,
    run_id: int,
    attempt_id: str,
    prompt_info: dict[str, Any],
    provider: Any,
    error: Exception,
) -> dict[str, Any]:
    status = _failure_kind(error)
    raw_metadata = (
        error.to_metadata()
        if isinstance(error, ProviderResponseError)
        else {
            "error": _error_text(error),
            "sampling_parameters": "unavailable",
            "exact_backend_revision": "unavailable",
        }
    )
    return _record_from_outcome(
        case=case,
        policy_hash=policy_hash,
        fixture_hash=fixture_hash,
        condition=condition,
        run_id=run_id,
        attempt_id=attempt_id,
        prompt_info=prompt_info,
        provider="deepseek",
        model=str(getattr(provider, "model", "unavailable")),
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=status,
        error=_error_text(error),
        raw_response=None,
        raw_metadata=raw_metadata,
        parsed_candidate={},
        parse_status=NOT_APPLICABLE,
        runtime_decision=(
            NOT_APPLICABLE
            if condition == "A_direct_llm"
            else f"{status}_NO_GATE"
        ),
        candidate_checks=NOT_APPLICABLE,
        final_checks=NOT_APPLICABLE,
        final_candidate={},
        final_output="",
        fallback_used=NOT_APPLICABLE,
        unauthorized_attempt=NOT_APPLICABLE if condition == "A_direct_llm" else False,
        accepted_unauthorized_write=NOT_APPLICABLE if condition == "A_direct_llm" else False,
        runtime_evidence=NOT_APPLICABLE,
        trace=NOT_APPLICABLE,
    )


def run_condition(
    case: dict[str, Any],
    policy: dict[str, Any],
    condition: str,
    provider: Any,
    *,
    experiment_id: str = EXPERIMENT_ID,
    prompt_info: dict[str, Any] | None = None,
    run_id: int = 1,
    attempt_id: str | None = None,
    policy_hash: str = NOT_APPLICABLE,
    fixture_hash: str = NOT_APPLICABLE,
) -> dict[str, Any]:
    """Run one cell exactly once; callers decide whether a transport replacement is allowed."""

    if condition not in CONDITIONS:
        raise ValueError(f"unknown pilot condition: {condition}")
    prompt_info = prompt_info or build_condition_prompt(case, policy, condition)
    attempt_id = attempt_id or f"{case['case_id']}-{condition}-run-{run_id}-attempt-1"
    authoritative = case["authoritative"]
    known_teams = runtime_module._policy_owner_teams(policy)

    if condition in ("A_direct_llm", "C_prompt_only_hybrid"):
        try:
            generation: RawGenerationResult = provider.generate(
                prompt_info["grounding_projection"],
                prompt_info["generation_contract"],
                prompt_info["request_context"],
            )
        except Exception as exc:
            result = _base_error_result(
                case, policy_hash, fixture_hash, condition, run_id, attempt_id, prompt_info, provider, exc
            )
            result["experiment_id"] = experiment_id
            return result
        parsed = _json_safe(deepcopy(generation.parsed_candidate))
        if not isinstance(parsed, dict):
            parsed = {}
        metadata = _json_safe(deepcopy(generation.metadata))
        if not isinstance(metadata, dict):
            metadata = {}
        actual_prompt_hash = metadata.get("prompt_hash", prompt_info["prompt_hash"])
        integrity_error = "" if actual_prompt_hash == prompt_info["prompt_hash"] else "prompt hash mismatch"
        candidate_status, candidate_checks = _semantic_result(
            parsed.get("customer_message"), authoritative, known_teams
        )
        final_candidate = (
            dict(parsed)
            if condition == "A_direct_llm"
            else {**deepcopy(authoritative), **dict(parsed)}
        )
        final_status, final_checks = _semantic_result(
            final_candidate.get("customer_message"), authoritative, known_teams
        )
        del candidate_status, final_status
        record = _record_from_outcome(
            case=case,
            policy_hash=policy_hash,
            fixture_hash=fixture_hash,
            condition=condition,
            run_id=run_id,
            attempt_id=attempt_id,
            prompt_info=prompt_info,
            provider=generation.provider,
            model=generation.model,
            timestamp=str(metadata.get("timestamp") or datetime.now(timezone.utc).isoformat()),
            status="PIPELINE_ERROR" if integrity_error else "COMPLETED",
            error=integrity_error,
            raw_response=generation.raw_response,
            raw_metadata=metadata,
            parsed_candidate=parsed,
            parse_status=generation.parse_status,
            runtime_decision=(
                NOT_APPLICABLE
                if condition == "A_direct_llm"
                else "ACCEPTED_NO_GATE"
                if generation.parse_status == PARSE_OK
                else "NO_GATE_PARSE_FAILED"
            ),
            candidate_checks=candidate_checks,
            final_checks=final_checks,
            final_candidate=final_candidate,
            final_output=str(final_candidate.get("customer_message") or ""),
            fallback_used=NOT_APPLICABLE,
            unauthorized_attempt=(
                NOT_APPLICABLE
                if condition == "A_direct_llm"
                else any(field in parsed for field in AUTHORITATIVE_FIELDS)
            ),
            accepted_unauthorized_write=(
                NOT_APPLICABLE
                if condition == "A_direct_llm"
                else any(field in parsed for field in AUTHORITATIVE_FIELDS)
            ),
            runtime_evidence=NOT_APPLICABLE,
            trace=NOT_APPLICABLE,
        )
        record["candidate_status"] = candidate_checks.get("overall", NOT_APPLICABLE) if isinstance(candidate_checks, dict) else NOT_APPLICABLE
        record["final_status"] = final_checks.get("overall", NOT_APPLICABLE) if isinstance(final_checks, dict) else NOT_APPLICABLE
        record["candidate_semantic_conflict"] = record["candidate_status"] == "CONFLICT" if record["candidate_status"] != NOT_APPLICABLE else NOT_APPLICABLE
        record["final_semantic_conflict"] = record["final_status"] == "CONFLICT" if record["final_status"] != NOT_APPLICABLE else NOT_APPLICABLE
        record["experiment_id"] = experiment_id
        return record

    recording_provider = _RecordingProvider(provider)
    runtime = _build_runtime(case, policy, recording_provider)
    result = runtime.run(
        {
            "user_input": case["request"],
            "support_policy": policy,
            "prompt_policy_context": prompt_info["request_context"]["support_policy"],
        }
    )
    context = result.context
    raw_record = _json_safe(context.get("raw_responses", {}).get("response_generation", {}))
    if not isinstance(raw_record, dict):
        raw_record = {}
    network_error = recording_provider.last_error
    if network_error is not None:
        error_status = _failure_kind(network_error)
        record = _base_error_result(
            case, policy_hash, fixture_hash, condition, run_id, attempt_id, prompt_info, provider, network_error
        ) | {
            "runtime_decision": f"{error_status}_FALLBACK" if context.get("fallback_used") else error_status,
            "fallback_used": bool(context.get("fallback_used")),
            "fallback_reason": error_status,
            "final_candidate": {
                field: context.get(field, authoritative.get(field))
                for field in ("ticket_category", *AUTHORITATIVE_FIELDS)
            },
            "final_output": str(context.get("customer_message") or ""),
            "runtime_evidence": _json_safe(context.get("field_evidence", [])),
            "trace": _json_safe([step.__dict__ for step in result.trace]),
        }
        final_candidate = record["final_candidate"]
        final_output = record["final_output"]
        if final_output:
            final_candidate["customer_message"] = final_output
        final_status, final_checks = _semantic_result(
            final_output,
            authoritative,
            known_teams,
        )
        record.update(
            {
                "final_consistency_results": final_checks,
                "final_semantic_conflict": (
                    final_status == "CONFLICT"
                    if final_status != NOT_APPLICABLE
                    else NOT_APPLICABLE
                ),
                "final_unresolved": (
                    final_status == "UNRESOLVED"
                    if final_status != NOT_APPLICABLE
                    else NOT_APPLICABLE
                ),
                "authoritative_field_correctness": _field_correctness(
                    final_candidate,
                    authoritative,
                ),
                "required_output_complete": _required_complete(final_candidate),
            }
        )
        return record
    parsed = _json_safe(context.get("raw_candidates", {}).get("response_generation", {}))
    if not isinstance(parsed, dict):
        parsed = {}
    raw_response = raw_record.get("raw_response")
    parse_status = str(raw_record.get("parse_status") or PARSE_FAILED)
    candidate_checks = _json_safe(
        context.get("consistency_results", {}).get("response_generation", NOT_APPLICABLE)
    )
    final_candidate = {
        "ticket_category": context.get("ticket_category", authoritative["ticket_category"]),
        **{
            field: context.get(field, authoritative[field])
            for field in AUTHORITATIVE_FIELDS
        },
    }
    if isinstance(context.get("customer_message"), str):
        final_candidate["customer_message"] = context["customer_message"]
    final_status, final_checks = _semantic_result(
        final_candidate.get("customer_message"), authoritative, known_teams
    )
    del final_status
    accepted = context.get("write_sets", {}).get("response_generation", {}).get("allowed", [])
    unauthorized = any(field in parsed for field in AUTHORITATIVE_FIELDS)
    record = _record_from_outcome(
        case=case,
        policy_hash=policy_hash,
        fixture_hash=fixture_hash,
        condition=condition,
        run_id=run_id,
        attempt_id=attempt_id,
        prompt_info=prompt_info,
        provider=raw_record.get("provider", "deepseek"),
        model=raw_record.get("model", getattr(provider, "model", "unavailable")),
        timestamp=str(raw_record.get("timestamp") or datetime.now(timezone.utc).isoformat()),
        status="COMPLETED",
        error="",
        raw_response=raw_response if isinstance(raw_response, str) else None,
        raw_metadata=raw_record,
        parsed_candidate=parsed,
        parse_status=parse_status,
        runtime_decision="REJECTED_FALLBACK" if context.get("fallback_used") else "ACCEPTED",
        candidate_checks=candidate_checks,
        final_checks=final_checks,
        final_candidate=final_candidate,
        final_output=str(context.get("customer_message") or ""),
        fallback_used=bool(context.get("fallback_used")),
        unauthorized_attempt=unauthorized,
        accepted_unauthorized_write=any(field in accepted for field in AUTHORITATIVE_FIELDS),
        runtime_evidence=_json_safe(
            [
                item
                for item in context.get("field_evidence", [])
                if item.get("attempted_writer") == "response_generation"
            ]
        ),
        trace=_json_safe([step.__dict__ for step in result.trace]),
    )
    record["candidate_status"] = candidate_checks.get("overall", NOT_APPLICABLE) if isinstance(candidate_checks, dict) else NOT_APPLICABLE
    record["final_status"] = final_checks.get("overall", NOT_APPLICABLE) if isinstance(final_checks, dict) else NOT_APPLICABLE
    record["candidate_semantic_conflict"] = record["candidate_status"] == "CONFLICT" if record["candidate_status"] != NOT_APPLICABLE else NOT_APPLICABLE
    record["final_semantic_conflict"] = record["final_status"] == "CONFLICT" if record["final_status"] != NOT_APPLICABLE else NOT_APPLICABLE
    return record


def _fixture_hash(case: dict[str, Any]) -> str:
    return _sha256_json(case)


def _source_hashes() -> dict[str, str]:
    return {
        "runtime_source": _sha256_bytes(ROOT / "src" / "agent_builder" / "workflow_runtime.py"),
        "validator_source": _sha256_bytes(ROOT / "src" / "agent_builder" / "workflow_runtime.py"),
        "validator_benchmark_source": _sha256_bytes(
            ROOT / "experiments" / "authoritative_contract" / "validator_benchmark" / "__init__.py"
        ),
        "provider_adapter_source": _sha256_bytes(ROOT / "src" / "agent_builder" / "generative_provider.py"),
        "pilot_runner_source": _sha256_bytes(Path(__file__)),
        "workflow_source": _sha256_bytes(WORKFLOW_PATH),
        "cases_source": _sha256_bytes(CASES_PATH),
        "policy_source": _sha256_bytes(ROOT / "data" / "support_policy.json"),
    }


def _git_state() -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True)
    return {
        "head": head,
        "dirty": bool(status.strip()),
        "status_lines": status.splitlines(),
    }


def _tree_fingerprint(path: Path) -> dict[str, Any]:
    files = sorted(item for item in path.rglob("*") if item.is_file())
    lines = [f"{item.relative_to(path).as_posix()}:{_sha256_bytes(item)}" for item in files]
    return {
        "file_count": len(files),
        "fingerprint": _sha256_text("\n".join(lines)),
    }


def _load_e0() -> dict[str, Any]:
    return _load(PILOT_ROOT.parent / "validator_benchmark" / "results_v1.json")


def prepare() -> dict[str, Any]:
    cases, payload = load_cases()
    policy_path = _policy_path(payload)
    policy = _load(policy_path)
    prompt_items = []
    prompt_map = {}
    fixture_map = {}
    for case in cases:
        fixture_hash = _fixture_hash(case)
        fixture_map[case["case_id"]] = fixture_hash
        for condition in CONDITIONS:
            info = build_condition_prompt(case, policy, condition)
            target = PROMPTS_ROOT / condition / f"{case['case_id']}_run_1.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            # Keep the frozen prompt bytes identical to the string sent by the adapter.
            target.write_bytes(info["prompt"].encode("utf-8"))
            key = f"{case['case_id']}::{condition}::run_1"
            prompt_map[key] = info["prompt_hash"]
            prompt_items.append(
                {
                    "case_id": case["case_id"],
                    "condition": condition,
                    "run_id": 1,
                    "path": str(target.relative_to(PILOT_ROOT)),
                    "prompt_version": info["prompt_version"],
                    "prompt_hash": info["prompt_hash"],
                    "grounding_hash": info["grounding_hash"],
                    "allowed_output_fields": info["generation_contract"]["allowed_output_fields"],
                }
            )
    _write_json(PROMPT_HASHES_PATH, {"prompt_version": PROMPT_VERSION, "items": prompt_items})
    _write_json(FIXTURE_HASHES_PATH, {"fixture_version": payload["fixture_version"], "items": fixture_map})
    e0 = _load_e0()
    old_baseline = _tree_fingerprint(ROOT / "experiments" / "baseline_comparison" / "v2")
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "pilot_version": PILOT_VERSION,
        "formal_main_experiment": False,
        "status": "E1_PROMPTS_FROZEN",
        "schema_version": 2,
        "runtime_version": WORKFLOW_RUNTIME_VERSION,
        "validator_version": "consistency-validator-v1.1",
        "provider_adapter_version": PROVIDER_ADAPTER_VERSION,
        "provider": "deepseek",
        "model": "configured-at-run-time",
        "condition_B": "UNAVAILABLE",
        "conditions": list(CONDITIONS),
        "cases": [case["case_id"] for case in cases],
        "runs_per_cell": 1,
        "pre_run_freeze": {
            "tests_baseline": "160 tests, 0 failures, 0 errors, 0 skipped",
            "git": _git_state(),
            "source_hashes": _source_hashes(),
            "old_baseline_experiment": {
                "path": "experiments/baseline_comparison/v2",
                **old_baseline,
            },
        },
        "e0": {
            "status": "E0_COMPLETE",
            "benchmark_version": e0["benchmark_version"],
            "ground_truth_version": e0["ground_truth_version"],
            "results_path": "experiments/authoritative_contract/validator_benchmark/results_v1.json",
            "results_hash": _sha256_bytes(PILOT_ROOT.parent / "validator_benchmark" / "results_v1.json"),
            "metrics": e0["metrics"],
            "validator_source_hash": e0["validator_source_hash"],
            "benchmark_hash": e0["benchmark_hash"],
            "ground_truth_hash": e0["ground_truth_hash"],
        },
        "fixture": {
            "path": str(CASES_PATH.relative_to(ROOT)),
            "source_hash": _sha256_bytes(CASES_PATH),
            "fixture_hashes_path": str(FIXTURE_HASHES_PATH.relative_to(ROOT)),
            "fixture_hashes": fixture_map,
            "policy_path": str(policy_path.relative_to(ROOT)),
            "policy_hash": _sha256_bytes(policy_path),
        },
        "workflow": {
            "path": str(WORKFLOW_PATH.relative_to(ROOT)),
            "hash": _sha256_bytes(WORKFLOW_PATH),
        },
        "prompts": {
            "path": str(PROMPTS_ROOT.relative_to(ROOT)),
            "hashes_path": str(PROMPT_HASHES_PATH.relative_to(ROOT)),
            "hashes": prompt_map,
            "prompt_version": PROMPT_VERSION,
        },
        "network_policy": {
            "no_content_retry": True,
            "replacement_allowed_for": "NETWORK_FAILED",
            "replacement_count": 1,
            "attempt_id_required": True,
            "replacement_for_required": True,
        },
    }
    _write_json(MANIFEST_PATH, manifest)
    return manifest


def _load_prompt_infos(cases: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    saved = _load(PROMPT_HASHES_PATH)
    infos = {}
    for case in cases:
        for condition in CONDITIONS:
            info = build_condition_prompt(case, policy, condition)
            key = f"{case['case_id']}::{condition}::run_1"
            expected = next(
                item for item in saved["items"]
                if f"{item['case_id']}::{item['condition']}::run_{item['run_id']}" == key
            )
            prompt_path = PILOT_ROOT / expected["path"]
            if _sha256_bytes(prompt_path) != expected["prompt_hash"] or info["prompt_hash"] != expected["prompt_hash"]:
                raise RuntimeError(f"frozen prompt mismatch: {key}")
            infos[key] = info
    return infos


def _verify_freeze(manifest: dict[str, Any], cases: list[dict[str, Any]], policy: dict[str, Any]) -> None:
    if manifest.get("status") != "E1_PROMPTS_FROZEN":
        raise RuntimeError(f"pilot manifest is not frozen for execution: {manifest.get('status')}")
    recorded = manifest["pre_run_freeze"]["source_hashes"]
    current = _source_hashes()
    for key, value in recorded.items():
        if current.get(key) != value:
            raise RuntimeError(f"frozen source hash changed: {key}")
    expected_fixtures = manifest["fixture"]["fixture_hashes"]
    for case in cases:
        if _fixture_hash(case) != expected_fixtures[case["case_id"]]:
            raise RuntimeError(f"frozen fixture hash changed: {case['case_id']}")
    if _sha256_bytes(_policy_path({"support_policy_path": cases[0]["support_policy_path"]})) != manifest["fixture"]["policy_hash"]:
        raise RuntimeError("frozen policy hash changed")


def _write_cell_artifacts(record: dict[str, Any]) -> None:
    identity = f"{record['case_id']}_{record['condition']}_run_{record['run_id']}"
    raw_path = RAW_ROOT / record["condition"] / f"{identity}.json"
    parsed_path = PARSED_ROOT / record["condition"] / f"{identity}.json"
    evidence_path = EVIDENCE_ROOT / record["condition"] / f"{identity}.json"
    _write_json(raw_path, record)
    _write_json(
        parsed_path,
        {
            "experiment_id": record["experiment_id"],
            "pilot_version": record["pilot_version"],
            "case_id": record["case_id"],
            "condition": record["condition"],
            "run_id": record["run_id"],
            "raw_response_hash": record["raw_response_hash"],
            "parsed_candidate": record["parsed_candidate"],
            "parse_status": record["parse_status"],
            "candidate_semantic_conflict": record["candidate_semantic_conflict"],
            "final_semantic_conflict": record["final_semantic_conflict"],
            "final_candidate": record["final_candidate"],
        },
    )
    _write_json(
        evidence_path,
        {
            "experiment_id": record["experiment_id"],
            "pilot_version": record["pilot_version"],
            "case_id": record["case_id"],
            "condition": record["condition"],
            "run_id": record["run_id"],
            "runtime_decision": record["runtime_decision"],
            "fallback_used": record["fallback_used"],
            "runtime_evidence": record["runtime_evidence"],
            "trace": record["trace"],
        },
    )


def run_pilot() -> dict[str, Any]:
    manifest = _load(MANIFEST_PATH)
    cases, payload = load_cases()
    policy = _load(_policy_path(payload))
    _verify_freeze(manifest, cases, policy)
    prompt_infos = _load_prompt_infos(cases, policy)
    if any(RAW_ROOT.rglob("*.json")):
        raise RuntimeError("pilot raw directory is non-empty; refusing accidental rerun")
    for root in (RAW_ROOT, PARSED_ROOT, EVIDENCE_ROOT, EVALUATION_ROOT):
        root.mkdir(parents=True, exist_ok=True)
    provider = DeepSeekCandidateProvider.from_environment()
    provider.prompt_version = PROMPT_VERSION
    records = []
    for case in cases:
        for condition in CONDITIONS:
            key = f"{case['case_id']}::{condition}::run_1"
            record = run_condition(
                case,
                policy,
                condition,
                provider,
                prompt_info=prompt_infos[key],
                run_id=1,
                attempt_id=f"{case['case_id']}-{condition}-run-1-attempt-1",
                policy_hash=manifest["fixture"]["policy_hash"],
                fixture_hash=manifest["fixture"]["fixture_hashes"][case["case_id"]],
            )
            _write_cell_artifacts(record)
            records.append(record)
            print(json.dumps({
                "case_id": record["case_id"],
                "condition": record["condition"],
                "status": record["status"],
                "parse_status": record["parse_status"],
                "fallback_used": record["fallback_used"],
            }, ensure_ascii=False))
    manifest["status"] = "E1_CALLS_COMPLETE" if len(records) == 18 else "E1_PARTIAL"
    manifest["e1"] = {
        "planned_calls": 18,
        "recorded_calls": len(records),
        "completed": sum(record["status"] == "COMPLETED" for record in records),
        "network_failed": sum(record["status"] == "NETWORK_FAILED" for record in records),
        "provider_failed": sum(record["status"] == "PROVIDER_FAILED" for record in records),
        "pipeline_error": sum(record["status"] == "PIPELINE_ERROR" for record in records),
    }
    _write_json(MANIFEST_PATH, manifest)
    return {"status": manifest["status"], **manifest["e1"]}


def _raw_records() -> list[dict[str, Any]]:
    records = [_load(path) for path in sorted(RAW_ROOT.rglob("*.json"))]
    identity = [(item["case_id"], item["condition"], item["run_id"]) for item in records]
    if len(identity) != len(set(identity)):
        raise RuntimeError("duplicate pilot cell identity")
    return records


def _metric_rate(numerator: int, denominator: int) -> float | str:
    return NOT_APPLICABLE if denominator == 0 else numerator / denominator


def analyze_pilot() -> dict[str, Any]:
    records = _raw_records()
    by_condition = {}
    for condition in CONDITIONS:
        cells = [item for item in records if item["condition"] == condition]
        applicable = [item for item in cells if item["status"] == "COMPLETED"]
        by_condition[condition] = {
            "planned": 6,
            "records": len(cells),
            "completed": len(applicable),
            "network_failed": sum(item["status"] == "NETWORK_FAILED" for item in cells),
            "provider_failed": sum(item["status"] == "PROVIDER_FAILED" for item in cells),
            "parse_success": sum(item["parse_success"] for item in applicable),
            "parse_success_rate": _metric_rate(sum(item["parse_success"] for item in applicable), len(applicable)),
            "required_output_complete": sum(item["required_output_complete"] for item in applicable),
            "required_output_completeness_rate": _metric_rate(sum(item["required_output_complete"] for item in applicable), len(applicable)),
            "candidate_semantic_conflicts": sum(item["candidate_semantic_conflict"] is True for item in applicable),
            "final_semantic_conflicts": sum(item["final_semantic_conflict"] is True for item in applicable),
            "fallback_count": sum(item["fallback_used"] is True for item in applicable),
            "fallback_rate": _metric_rate(sum(item["fallback_used"] is True for item in applicable), len(applicable)),
            "unresolved_count": sum(item["final_unresolved"] is True for item in applicable),
            "unresolved_rate": _metric_rate(sum(item["final_unresolved"] is True for item in applicable), len(applicable)),
            "unauthorized_attempt_count": sum(item["unauthorized_attempt"] is True for item in applicable),
            "accepted_unauthorized_write_count": sum(item["accepted_unauthorized_write"] is True for item in applicable),
            "authoritative_field_correctness": {
                field: {
                    "pass": sum(item["authoritative_field_correctness"].get(field) == "PASS" for item in applicable),
                    "fail": sum(item["authoritative_field_correctness"].get(field) == "FAIL" for item in applicable),
                    "unresolved": sum(item["authoritative_field_correctness"].get(field) == "UNRESOLVED" for item in applicable),
                }
                for field in AUTHORITATIVE_FIELDS
            },
        }
    case_rows = []
    for item in records:
        case_rows.append({
            "case_id": item["case_id"],
            "condition": item["condition"],
            "run_id": item["run_id"],
            "status": item["status"],
            "parse_status": item["parse_status"],
            "m1_priority": item["authoritative_field_correctness"].get("priority", NOT_APPLICABLE),
            "m1_sla": item["authoritative_field_correctness"].get("sla", NOT_APPLICABLE),
            "m1_owner_team": item["authoritative_field_correctness"].get("owner_team", NOT_APPLICABLE),
            "candidate_semantic_conflict": item["candidate_semantic_conflict"],
            "final_semantic_conflict": item["final_semantic_conflict"],
            "required_output_complete": item["required_output_complete"],
            "fallback_used": item["fallback_used"],
            "final_unresolved": item["final_unresolved"],
            "raw_response_hash": item["raw_response_hash"],
        })
    EVALUATION_ROOT.mkdir(parents=True, exist_ok=True)
    rows_path = EVALUATION_ROOT / "case_condition_results_v1.csv"
    with rows_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(case_rows[0]) if case_rows else ["case_id"])
        writer.writeheader()
        writer.writerows(case_rows)
    artifact_counts = {
        "raw_files": len(list(RAW_ROOT.rglob("*.json"))),
        "parsed_files": len(list(PARSED_ROOT.rglob("*.json"))),
        "runtime_evidence_files": len(list(EVIDENCE_ROOT.rglob("*.json"))),
        "evaluation_rows": len(case_rows),
    }
    metrics = {
        "experiment_id": EXPERIMENT_ID,
        "pilot_version": PILOT_VERSION,
        "analysis_version": "pilot-analysis-v1",
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "planned_calls": 18,
        "recorded_calls": len(records),
        "artifact_counts": artifact_counts,
        "pipeline_errors": [
            {"case_id": item["case_id"], "condition": item["condition"], "error": item["error"]}
            for item in records if item["status"] == "PIPELINE_ERROR"
        ],
        "network_failures": [
            {"case_id": item["case_id"], "condition": item["condition"], "error": item["error"]}
            for item in records if item["status"] == "NETWORK_FAILED"
        ],
        "condition_metrics": by_condition,
        "source_hashes": _source_hashes(),
        "prompt_hashes_path": str(PROMPT_HASHES_PATH.relative_to(ROOT)),
        "fixture_hashes_path": str(FIXTURE_HASHES_PATH.relative_to(ROOT)),
    }
    _write_json(EVALUATION_ROOT / "metrics_v1.json", metrics)
    _write_json(EVALUATION_ROOT / "results_v1.json", {"metrics": metrics, "rows": case_rows})
    summary_lines = [
        "# E1 Small Pilot Analysis",
        "",
        "This is a pipeline check. It is not a formal winner or generalization result.",
        "",
        f"- Planned calls: {metrics['planned_calls']}",
        f"- Recorded calls: {metrics['recorded_calls']}",
        f"- Raw / parsed / evidence / evaluation rows: {artifact_counts['raw_files']} / {artifact_counts['parsed_files']} / {artifact_counts['runtime_evidence_files']} / {artifact_counts['evaluation_rows']}",
        "",
        "| Condition | Completed | Parse success | Candidate conflicts | Final conflicts | Fallback | UNRESOLVED |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        item = by_condition[condition]
        summary_lines.append(
            f"| {condition} | {item['completed']} | {item['parse_success']} | {item['candidate_semantic_conflicts']} | {item['final_semantic_conflicts']} | {item['fallback_count']} | {item['unresolved_count']} |"
        )
    (EVALUATION_ROOT / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "run", "analyze"))
    args = parser.parse_args()
    if args.command == "prepare":
        manifest = prepare()
        print(json.dumps({"status": manifest["status"], "experiment_id": manifest["experiment_id"], "prompt_count": len(manifest["prompts"]["hashes"])}, ensure_ascii=False))
    elif args.command == "run":
        print(json.dumps(run_pilot(), ensure_ascii=False))
    else:
        print(json.dumps(analyze_pilot(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

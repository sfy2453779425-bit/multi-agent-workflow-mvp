from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from experiments.ac_formal_v2.common import (
    BASE,
    CASE_IDS,
    EXPERIMENT_ID,
    PROVIDERS,
    ROOT,
    SEED,
    append_jsonl,
    assert_frozen_source_hashes,
    build_schedule,
    canonical_json,
    core,
    frozen_policy,
    frozen_workflow_path,
    json_safe,
    load_json,
    prompt_for,
    prepare as prepare_frozen,
    read_jsonl,
    redact_secret_text,
    runtime_result_fields,
    sha256_json,
    sha256_text,
)
from agent_builder.generative_provider import PARSE_OK, RawGenerationResult, customer_message_prompt_evidence, parse_candidate
from agent_builder.responses_provider import (
    DeepSeekResponsesProvider,
    NETWORK_FAILED,
    RESPONSES_DEFAULT_MAX_OUTPUT_TOKENS,
    RESPONSES_PROVIDER_ADAPTER_VERSION,
    RESPONSES_PROVIDER_CONFIG_VERSION,
    ResponsesProviderError,
)


GPT_MODEL = "gpt-5.6"
CLAUDE_MODEL = "claude-opus-5-5"
GPT_REASONING = "none"
GPT_MAX_OUTPUT = 1024
CLAUDE_MAX_OUTPUT = 1024
HTTP_TIMEOUT = 120
MAX_ATTEMPTS = 3


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def is_retryable_status(status: int | None) -> bool:
    return status == 429 or (status is not None and 500 <= status <= 599)


def is_transport_failure(provider_status: str | None, http_status: int | None) -> bool:
    return provider_status == NETWORK_FAILED or is_retryable_status(http_status)


def build_openai_payload(
    model: str,
    messages: list[dict[str, str]],
    max_output_tokens: int,
    reasoning_effort: str,
) -> dict[str, Any]:
    return {
        "model": model,
        "input": [{"role": item["role"], "content": item["content"]} for item in messages],
        "max_output_tokens": max_output_tokens,
        "reasoning": {"effort": reasoning_effort},
    }


def build_anthropic_payload(
    model: str, messages: list[dict[str, str]], max_tokens: int
) -> dict[str, Any]:
    body: dict[str, Any] = {"model": model, "max_tokens": max_tokens, "messages": []}
    user_messages = []
    system_parts = []
    for item in messages:
        if item["role"] == "system":
            system_parts.append(item["content"])
        else:
            user_messages.append({"role": item["role"], "content": item["content"]})
    if system_parts:
        body["system"] = "\n\n".join(system_parts)
    body["messages"] = user_messages
    return body


def extract_openai_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    parts: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "".join(parts)


def extract_anthropic_text(payload: dict[str, Any]) -> str:
    return "".join(
        item.get("text", "")
        for item in payload.get("content") or []
        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str)
    )


def _parse_body(raw_body: str) -> Any:
    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        return {"_raw_body": raw_body}


def _redact_tree(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secret_text(value)
    if isinstance(value, dict):
        return {str(key): _redact_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_tree(item) for item in value]
    return value


def _post_json(
    url: str, body: dict[str, Any], headers: dict[str, str]
) -> dict[str, Any]:
    request_bytes = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    attempts: list[dict[str, Any]] = []
    start = time.perf_counter()
    for attempt_no in range(1, MAX_ATTEMPTS + 1):
        request = Request(url, data=request_bytes, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=HTTP_TIMEOUT) as response:
                status = int(getattr(response, "status", 200))
                raw_body = response.read().decode("utf-8", errors="replace")
                attempts.append({"attempt": attempt_no, "http_status": status, "error_type": None, "error_message": None})
                return {
                    "http_status": status,
                    "raw_body": raw_body,
                    "payload": _parse_body(raw_body),
                    "attempts": attempts,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 3),
                    "transport_failure": False,
                    "api_request_hash": hashlib.sha256(request_bytes).hexdigest(),
                }
        except HTTPError as exc:
            raw_body = exc.read().decode("utf-8", errors="replace")
            retryable = is_retryable_status(int(exc.code))
            attempts.append({
                "attempt": attempt_no,
                "http_status": int(exc.code),
                "error_type": "HTTPError",
                "error_message": redact_secret_text(f"HTTP {exc.code}"),
            })
            if retryable and attempt_no < MAX_ATTEMPTS:
                time.sleep(2 ** (attempt_no - 1))
                continue
            return {
                "http_status": int(exc.code),
                "raw_body": raw_body,
                "payload": _parse_body(raw_body),
                "attempts": attempts,
                "latency_ms": round((time.perf_counter() - start) * 1000, 3),
                "transport_failure": retryable or int(exc.code) >= 500,
                "api_request_hash": hashlib.sha256(request_bytes).hexdigest(),
            }
        except (URLError, TimeoutError, ConnectionError, socket.timeout, OSError) as exc:
            attempts.append({
                "attempt": attempt_no,
                "http_status": None,
                "error_type": type(exc).__name__,
                "error_message": redact_secret_text(str(getattr(exc, "reason", exc))),
            })
            if attempt_no < MAX_ATTEMPTS:
                time.sleep(2 ** (attempt_no - 1))
                continue
            return {
                "http_status": None,
                "raw_body": "",
                "payload": None,
                "attempts": attempts,
                "latency_ms": round((time.perf_counter() - start) * 1000, 3),
                "transport_failure": True,
                "api_request_hash": hashlib.sha256(request_bytes).hexdigest(),
            }
    raise AssertionError("unreachable retry loop")


class _CheckedRetryProvider:
    """Keep DeepSeek's frozen adapter request path; only wrap transport retries."""

    provider = "deepseek"

    def __init__(self, inner: DeepSeekResponsesProvider, expected_prompt_hash: str):
        self.inner = inner
        self.model = inner.model
        self.expected_prompt_hash = expected_prompt_hash
        self.attempts: list[dict[str, Any]] = []
        self.freeze_violation: str | None = None

    def generate(self, grounding_projection, generation_contract, request_context):
        evidence = customer_message_prompt_evidence(
            grounding_projection, generation_contract, request_context
        )
        if evidence["prompt_text_hash"] != self.expected_prompt_hash:
            self.freeze_violation = "runtime prompt differs from frozen prompt"
            raise RuntimeError("FREEZE_VIOLATION: runtime prompt hash differs")
        for attempt_no in range(1, MAX_ATTEMPTS + 1):
            try:
                generation = self.inner.generate(
                    grounding_projection, generation_contract, request_context
                )
                metadata = deepcopy(generation.metadata)
                metadata["attempts"] = [
                    *self.attempts,
                    {
                        "attempt": attempt_no,
                        "http_status": metadata.get("http_status"),
                        "error_type": None,
                        "error_message": None,
                    },
                ]
                return RawGenerationResult(
                    provider=generation.provider,
                    model=generation.model,
                    raw_response=generation.raw_response,
                    parsed_candidate=generation.parsed_candidate,
                    parse_status=generation.parse_status,
                    metadata=metadata,
                )
            except ResponsesProviderError as exc:
                meta = exc.to_metadata()
                status = getattr(exc, "http_status", None)
                retryable = status is None and meta.get("provider_status") == NETWORK_FAILED
                retryable = retryable or is_retryable_status(status)
                self.attempts.append({
                    "attempt": attempt_no,
                    "http_status": status,
                    "error_type": type(exc).__name__,
                    "error_message": redact_secret_text(str(exc)),
                })
                if retryable and attempt_no < MAX_ATTEMPTS:
                    time.sleep(2 ** (attempt_no - 1))
                    continue
                raise
        raise AssertionError("unreachable retry loop")


def _make_prompt_case(case_id: str, smoke: bool) -> dict[str, Any]:
    return prompt_for("SMOKE01" if smoke else case_id)


def _base_artifact(
    *,
    row: dict[str, Any],
    prompt: dict[str, Any],
    provider: str,
    smoke: bool,
) -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "experiment_status": "SMOKE" if smoke else "FORMAL",
        "case_id": prompt["case_id"],
        "case_type": prompt["case_type"],
        "condition": "deepseek_live_runtime" if provider == "deepseek" else "direct_model",
        "run_id": 1 if smoke else row["run_id"],
        "schedule_index": None if smoke else row["schedule_index"],
        "schedule_seed": SEED,
        "provider": provider,
        "api_format": {"deepseek": "responses", "gpt": "responses", "claude": "messages"}[provider],
        "model_requested": {name: model for name, model in PROVIDERS}[provider],
        "model_returned": None,
        "response_id": None,
        "call_path": None,
        "timestamp_start_utc": None,
        "timestamp_end_utc": None,
        "latency_ms": None,
        "case_hash": prompt["case_hash"],
        "prompt_text_hash": prompt["prompt_text_hash"],
        "api_request_hash": None,
        "http_status": None,
        "provider_status": None,
        "response_status": None,
        "incomplete_details": None,
        "output_item_types": None,
        "reasoning_tokens": None,
        "output_tokens": None,
        "extraction_status": None,
        "extraction_path": None,
        "raw_response_hash": None,
        "provider_payload_hash": None,
        "sanitized_request": None,
        "params_sent": None,
        "params_unsupported": [],
        "sampling_parameters": "not_set_provider_default",
        "finish_reason": None,
        "usage": None,
        "raw_response": None,
        "raw_response_body": None,
        "provider_payload": None,
        "raw_text": None,
        "raw_model_text": None,
        "raw_model_text_hash": None,
        "parse_status": None,
        "parsed_candidate": None,
        "attempts": [],
        "transport_failure": False,
        "live_runtime": None,
        "git_commit": None,
        "runtime_version": "authoritative-contract-v1.1",
        "validator_version": "consistency-validator-v1.1",
        "provider_adapter": RESPONSES_PROVIDER_ADAPTER_VERSION if provider == "deepseek" else None,
        "provider_config": RESPONSES_PROVIDER_CONFIG_VERSION if provider == "deepseek" else None,
        "fixture_hash": prompt.get("fixture_hash"),
        "policy_hash": prompt.get("policy_hash"),
        "grounding_hash": None,
        "experiment_notes": None,
    }


def _finish_artifact(artifact: dict[str, Any], *, start: str, start_clock: float) -> dict[str, Any]:
    artifact["timestamp_start_utc"] = start
    artifact["timestamp_end_utc"] = utc_now()
    artifact["latency_ms"] = round((time.perf_counter() - start_clock) * 1000, 3)
    artifact["git_commit"] = _git_commit()
    return _redact_tree(artifact)


def _git_commit() -> str | None:
    try:
        import subprocess
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return None


def _run_deepseek(
    row: dict[str, Any], prompt_record: dict[str, Any], *, smoke: bool
) -> dict[str, Any]:
    secret = os.environ.get("DEEPSEEK_API_KEY")
    if not secret:
        artifact = _base_artifact(row=row, prompt=prompt_record, provider="deepseek", smoke=smoke)
        artifact["experiment_notes"] = "SKIPPED: DEEPSEEK_API_KEY not present"
        return artifact
    start = utc_now()
    start_clock = time.perf_counter()
    case = deepcopy(prompt_record["case"])
    policy = frozen_policy()
    core.WORKFLOW_PATH = frozen_workflow_path()
    provider = DeepSeekResponsesProvider.from_environment(
        model="deepseek-v4-pro",
        max_output_tokens=RESPONSES_DEFAULT_MAX_OUTPUT_TOKENS,
        reasoning_effort="none",
        provider_config_version=RESPONSES_PROVIDER_CONFIG_VERSION,
    )
    checked = _CheckedRetryProvider(provider, prompt_record["prompt_text_hash"])
    runtime = core._build_runtime(case, policy, checked)
    result = runtime.run({
        "user_input": case["request"],
        "support_policy": policy,
        "prompt_policy_context": core._policy_context(policy, case["authoritative"]["ticket_category"]),
    })
    if checked.freeze_violation:
        raise RuntimeError("FREEZE_VIOLATION: runtime generation prompt mismatch")
    runtime_fields = runtime_result_fields(result.context)
    metadata = json_safe(result.context.get("raw_responses", {}).get("response_generation", {}))
    raw_text = metadata.get("raw_response") or metadata.get("raw_model_text") or ""
    raw_payload = metadata.get("provider_payload")
    raw_body = metadata.get("raw_response_body")
    artifact = _base_artifact(row=row, prompt=prompt_record, provider="deepseek", smoke=smoke)
    artifact.update({
        "call_path": "frozen_responses_adapter_via_runtime",
        "model_returned": metadata.get("model", provider.model),
        "http_status": metadata.get("http_status"),
        "provider_status": metadata.get("provider_status"),
        "response_status": metadata.get("response_status"),
        "incomplete_details": metadata.get("incomplete_details"),
        "output_item_types": metadata.get("response_output_item_types"),
        "reasoning_tokens": metadata.get("reasoning_tokens"),
        "output_tokens": metadata.get("output_tokens"),
        "extraction_status": metadata.get("extraction_status"),
        "extraction_path": metadata.get("extraction_path"),
        "response_id": (raw_payload or {}).get("id") if isinstance(raw_payload, dict) else None,
        "api_request_hash": metadata.get("request_hash"),
        "raw_response_hash": metadata.get("raw_response_body_hash") or (sha256_text(raw_body) if isinstance(raw_body, str) else None),
        "provider_payload_hash": metadata.get("raw_response_body_hash"),
        "sanitized_request": metadata.get("request_payload"),
        "params_sent": {"reasoning": {"effort": "none"}, "max_output_tokens": 1024},
        "finish_reason": (
            (metadata.get("incomplete_details") or {}).get("reason")
            if isinstance(metadata.get("incomplete_details"), dict)
            else None
        ) or metadata.get("response_status") or metadata.get("provider_status"),
        "usage": {
            "reasoning_tokens": metadata.get("reasoning_tokens"),
            "output_tokens": metadata.get("output_tokens"),
        },
        "raw_response": raw_payload,
        "raw_response_body": raw_body,
        "raw_text": raw_text,
        "parse_status": metadata.get("parse_status"),
        "parsed_candidate": runtime_fields["candidate"],
        "attempts": metadata.get("attempts") or checked.attempts,
        "provider_payload": raw_payload,
        "raw_model_text": raw_text,
        "raw_model_text_hash": sha256_text(raw_text),
        "transport_failure": is_transport_failure(
            metadata.get("provider_status"),
            metadata.get("http_status") if isinstance(metadata.get("http_status"), int) else None,
        ),
        "live_runtime": {
            "decision": runtime_fields["decision"],
            "reject_reason_codes": runtime_fields["reject_reason_codes"],
            "final_output": runtime_fields["final_output"],
        },
        "grounding_hash": metadata.get("grounding_hash"),
        "experiment_notes": (
            "runtime_error=" + str(result.error) if result.error
            else (f"provider_status={metadata.get('provider_status')}" if metadata.get("provider_status") not in (None, "COMPLETED") else None)
        ),
    })
    return _finish_artifact(artifact, start=start, start_clock=start_clock)


def _run_direct(
    row: dict[str, Any], prompt_record: dict[str, Any], *, smoke: bool
) -> dict[str, Any]:
    provider = row["provider"]
    model = row["model_requested"]
    messages = prompt_record["messages"]
    if provider == "gpt":
        secret = os.environ.get("OPENAI_API_KEY")
        if not secret:
            artifact = _base_artifact(row=row, prompt=prompt_record, provider=provider, smoke=smoke)
            artifact["experiment_notes"] = "SKIPPED: OPENAI_API_KEY not present"
            return artifact
        body = build_openai_payload(model, messages, GPT_MAX_OUTPUT, GPT_REASONING)
        headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}
        url = "https://api.openai.com/v1/responses"
        params_sent = {"max_output_tokens": GPT_MAX_OUTPUT, "reasoning": {"effort": GPT_REASONING}}
        call_path = "openai_responses_http"
    else:
        secret = os.environ.get("ANTHROPIC_API_KEY")
        if not secret:
            artifact = _base_artifact(row=row, prompt=prompt_record, provider=provider, smoke=smoke)
            artifact["experiment_notes"] = "SKIPPED: ANTHROPIC_API_KEY not present"
            return artifact
        body = build_anthropic_payload(model, messages, CLAUDE_MAX_OUTPUT)
        headers = {
            "x-api-key": secret,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        url = "https://api.anthropic.com/v1/messages"
        params_sent = {"max_tokens": CLAUDE_MAX_OUTPUT}
        call_path = "anthropic_messages_http"

    start = utc_now()
    start_clock = time.perf_counter()
    observation = _post_json(url, body, headers)
    payload = observation["payload"] if isinstance(observation["payload"], dict) else {}
    raw_text = extract_openai_text(payload) if provider == "gpt" else extract_anthropic_text(payload)
    parsed, parse_status = parse_candidate(raw_text)
    raw_body = observation["raw_body"]
    artifact = _base_artifact(row=row, prompt=prompt_record, provider=provider, smoke=smoke)
    artifact.update({
        "call_path": call_path,
        "model_returned": payload.get("model"),
        "response_id": payload.get("id"),
        "http_status": observation["http_status"],
        "provider_status": payload.get("status") or payload.get("type"),
        "response_status": payload.get("status"),
        "incomplete_details": payload.get("incomplete_details"),
        "output_item_types": (
            [item.get("type") for item in payload.get("output", []) if isinstance(item, dict)]
            if provider == "gpt"
            else [item.get("type") for item in payload.get("content", []) if isinstance(item, dict)]
        ),
        "extraction_status": "SUCCESS" if raw_text else "FAILED",
        "extraction_path": "output.message.content.output_text" if provider == "gpt" else "content.text",
        "api_request_hash": observation["api_request_hash"],
        "raw_response_hash": hashlib.sha256(raw_body.encode("utf-8")).hexdigest() if raw_body else None,
        "provider_payload_hash": hashlib.sha256(raw_body.encode("utf-8")).hexdigest() if raw_body else None,
        "sanitized_request": body,
        "params_sent": params_sent,
        "finish_reason": payload.get("stop_reason") or (payload.get("incomplete_details") or {}).get("reason") or payload.get("status"),
        "usage": payload.get("usage"),
        "raw_response": observation["payload"],
        "raw_response_body": raw_body,
        "provider_payload": observation["payload"],
        "raw_text": raw_text,
        "raw_model_text": raw_text,
        "raw_model_text_hash": sha256_text(raw_text),
        "parse_status": parse_status,
        "parsed_candidate": parsed if parse_status == PARSE_OK else None,
        "attempts": observation["attempts"],
        "transport_failure": observation["transport_failure"],
        "experiment_notes": None if 200 <= (observation["http_status"] or 0) < 300 else f"HTTP {observation['http_status']}",
    })
    artifact = _finish_artifact(artifact, start=start, start_clock=start_clock)
    artifact["latency_ms"] = observation["latency_ms"]
    return artifact


def _append_call(root: Path, row: dict[str, Any]) -> None:
    append_jsonl(root / f"calls_{row['provider']}.jsonl", row)
    append_jsonl(root / f"parsed_{row['provider']}.jsonl", {
        "experiment_id": row["experiment_id"],
        "case_id": row["case_id"],
        "run_id": row["run_id"],
        "provider": row["provider"],
        "raw_response_hash": row["raw_response_hash"],
        "parse_status": row["parse_status"],
        "parsed_candidate": row["parsed_candidate"],
    })
    if row["provider"] == "deepseek":
        append_jsonl(root / "runtime_evidence_deepseek.jsonl", {
            "experiment_id": row["experiment_id"],
            "case_id": row["case_id"],
            "run_id": row["run_id"],
            "decision": (row["live_runtime"] or {}).get("decision"),
            "reject_reason_codes": (row["live_runtime"] or {}).get("reject_reason_codes"),
            "fallback_used": (row["live_runtime"] or {}).get("decision") == "REJECT",
            "final_output": (row["live_runtime"] or {}).get("final_output"),
        })


def _merge_provider_logs(root: Path, *, smoke: bool) -> list[dict[str, Any]]:
    rows = []
    for provider, _model in PROVIDERS:
        rows.extend(read_jsonl(root / f"calls_{provider}.jsonl"))
    rows.sort(key=lambda item: (item.get("schedule_index") is None, item.get("schedule_index") or PROVIDERS.index((item["provider"], item["model_requested"]))))
    merged_path = root / "calls.jsonl"
    serialized = "".join(json.dumps(_redact_tree(item), ensure_ascii=False, separators=(",", ":")) + "\n" for item in rows)
    if merged_path.exists():
        if merged_path.read_text(encoding="utf-8") != serialized:
            raise RuntimeError("immutable merged calls.jsonl differs from provider append logs")
    else:
        merged_path.parent.mkdir(parents=True, exist_ok=True)
        merged_path.write_text(serialized, encoding="utf-8", newline="\n")
    return rows


def _run_worker(provider: str, rows: list[dict[str, Any]], smoke: bool, stop_event: Event) -> list[dict[str, Any]]:
    prompt_record = prompt_for("SMOKE01") if smoke else None
    root = BASE / "smoke" if smoke else BASE / "raw" / EXPERIMENT_ID
    existing = read_jsonl(root / f"calls_{provider}.jsonl")
    if smoke and any(item.get("case_id") == "SMOKE01" for item in existing):
        return [item for item in existing if item.get("case_id") == "SMOKE01"]
    completed_keys = {(item.get("case_id"), item.get("run_id")) for item in existing}
    results = []
    for row in rows:
        if stop_event.is_set():
            break
        if not smoke and (row["case_id"], row["run_id"]) in completed_keys:
            continue
        prompt = prompt_record if smoke else prompt_for(row["case_id"])
        artifact = _run_deepseek(row, prompt, smoke=smoke) if provider == "deepseek" else _run_direct(row, prompt, smoke=smoke)
        _append_call(root, artifact)
        results.append(artifact)
        status = artifact.get("http_status")
        if artifact.get("transport_failure") or (status is not None and 400 <= status < 500):
            stop_event.set()
            break
    return results


def _collect_smoke() -> list[dict[str, Any]]:
    prompt = prompt_for("SMOKE01")
    rows = [
        {"provider": provider, "model_requested": model, "run_id": 1, "schedule_index": None}
        for provider, model in PROVIDERS
    ]
    output_root = BASE / "smoke"
    stop_event = Event()
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="ac-smoke") as pool:
        futures = [pool.submit(_run_worker, provider, [row], True, stop_event) for provider, _ in PROVIDERS for row in rows if row["provider"] == provider]
        for future in as_completed(futures):
            future.result()
    results = _merge_provider_logs(output_root, smoke=True)
    write_json = {
        "experiment_id": EXPERIMENT_ID,
        "experiment_status": "SMOKE",
        "case_id": "SMOKE01",
        "calls": sum(1 for item in results if item.get("case_id") == "SMOKE01" and item.get("http_status") is not None),
        "providers_skipped": [item["provider"] for item in results if str(item.get("experiment_notes") or "").startswith("SKIPPED:")],
        "results": [
            {key: item.get(key) for key in (
                "provider", "model_returned", "finish_reason", "parse_status", "transport_failure", "experiment_notes"
            )}
            for item in results
        ],
    }
    from experiments.ac_formal_v2.common import write_json_immutable
    # Smoke output is append-only by call ID; the summary is immutable per first run.
    write_json_immutable(output_root / "smoke_summary.json", write_json)
    return results


def _collect_formal() -> list[dict[str, Any]]:
    manifest = load_json(BASE / "manifest.json")
    assert_frozen_source_hashes(manifest)
    schedule = load_json(BASE / "config" / "schedule.json")["calls"]
    if len(schedule) != 54:
        raise RuntimeError("FREEZE_VIOLATION: expected 54 frozen schedule rows")
    if len(CASE_IDS) != 6:
        raise RuntimeError("FREEZE_VIOLATION: frozen case count changed")
    smoke_rows = read_jsonl(BASE / "smoke" / "calls_deepseek.jsonl")
    smoke_rows += read_jsonl(BASE / "smoke" / "calls_gpt.jsonl")
    smoke_rows += read_jsonl(BASE / "smoke" / "calls_claude.jsonl")
    smoke_by_provider = {row["provider"]: row for row in smoke_rows if row.get("case_id") == "SMOKE01"}
    if set(smoke_by_provider) != {"deepseek", "gpt", "claude"}:
        raise RuntimeError("SMOKE_INCOMPLETE: all three provider smoke calls are required")
    for item in smoke_by_provider.values():
        if item.get("parse_status") != PARSE_OK or not item.get("raw_text"):
            raise RuntimeError(f"SMOKE_FAILED: {item['provider']} did not produce parseable output")

    raw_dir = BASE / "raw" / EXPERIMENT_ID
    api_env = {"deepseek": "DEEPSEEK_API_KEY", "gpt": "OPENAI_API_KEY", "claude": "ANTHROPIC_API_KEY"}
    missing = [name for name in api_env.values() if not os.environ.get(name)]
    if missing:
        raise RuntimeError("FORMAL_COLLECTION_BLOCKED: required provider credential environment variable missing")
    existing = []
    for provider, _model in PROVIDERS:
        existing.extend(read_jsonl(raw_dir / f"calls_{provider}.jsonl"))
    existing_keys = {(item.get("case_id"), item.get("provider"), item.get("run_id")) for item in existing}
    failures = [item for item in existing if item.get("transport_failure") or str(item.get("http_status") or "").startswith("4")]
    if failures:
        raise RuntimeError("FORMAL_COLLECTION_STOPPED: prior frozen schedule contains failed calls")
    remaining_by_provider = {
        provider: [
            row for row in schedule
            if row["provider"] == provider
            and (row["case_id"], provider, row["run_id"]) not in existing_keys
        ]
        for provider, _model in PROVIDERS
    }
    stop_event = Event()
    results = []
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="ac-formal") as pool:
        futures = [
            pool.submit(_run_worker, provider, rows, False, stop_event)
            for provider, rows in remaining_by_provider.items()
        ]
        for future in as_completed(futures):
            results.extend(future.result())
    _merge_provider_logs(raw_dir, smoke=False)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--smoke", action="store_true")
    group.add_argument("--formal", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        try:
            result = prepare_frozen()
        except Exception as exc:
            print(str(exc))
            return 2
        print(json.dumps({"prepared": True, "planned_calls": len(result["schedule"]), "schedule_hash": result["manifest"]["schedule_hash"]}))
        return 0
    if args.smoke:
        if not (BASE / "manifest.json").exists():
            print("NOT_PREPARED")
            return 2
        try:
            from experiments.ac_formal_v2.common import assert_frozen_source_hashes
            assert_frozen_source_hashes(load_json(BASE / "manifest.json"))
            results = _collect_smoke()
            print(json.dumps([
                {"provider": item["provider"], "model_returned": item.get("model_returned"), "finish_reason": item.get("finish_reason"), "parse_status": item.get("parse_status"), "nonempty": bool(item.get("raw_text")), "transport_failure": item.get("transport_failure"), "experiment_notes": item.get("experiment_notes")}
                for item in results
            ], ensure_ascii=False))
            return 0
        except Exception as exc:
            print(redact_secret_text(str(exc)))
            return 2
    try:
        results = _collect_formal()
    except Exception as exc:
        print(redact_secret_text(str(exc)))
        return 2
    print(json.dumps({"new_calls": len(results), "experiment_id": EXPERIMENT_ID}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

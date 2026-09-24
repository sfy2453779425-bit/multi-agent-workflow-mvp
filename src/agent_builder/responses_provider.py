"""DeepSeek Responses API adapter with immutable response evidence."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from collections.abc import Mapping
from typing import Any
import urllib.error
import urllib.request

from .generative_provider import (
    COMPLETED,
    CONTENT_EXTRACTION_FAILED,
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_MAX_TOKENS,
    HTTP_FAILED,
    NETWORK_FAILED,
    PARSE_FAILED,
    ProviderResponseError,
    RawGenerationResult,
    customer_message_prompt_evidence,
    parse_candidate,
    _safe_response_headers,
    _http_status,
)


RESPONSES_PROVIDER_ADAPTER_VERSION = "deepseek-responses-adapter-v1"
RESPONSES_PROVIDER_CONFIG_VERSION = "deepseek-v4-pro-responses-nonthinking-v1"
RESPONSES_DEFAULT_MAX_OUTPUT_TOKENS = DEFAULT_MAX_TOKENS
PROVIDER_INCOMPLETE = "PROVIDER_INCOMPLETE"
PROVIDER_FAILED = "PROVIDER_FAILED"
PROVIDER_MODE_CONTROL_FAILED = "PROVIDER_MODE_CONTROL_FAILED"


class ResponsesProviderError(ProviderResponseError):
    """ProviderResponseError carrying Responses-specific observations."""

    def to_metadata(self) -> dict[str, Any]:
        metadata = super().to_metadata()
        metadata.update(
            {
                "api_format": "responses",
                "provider_adapter_version": RESPONSES_PROVIDER_ADAPTER_VERSION,
                "raw_model_text": self.context_metadata.get("raw_model_text"),
                "raw_response_hash": self.context_metadata.get(
                    "raw_response_hash", "NOT_APPLICABLE"
                ),
                "response_status": self.context_metadata.get(
                    "response_status", "unavailable"
                ),
                "incomplete_details": deepcopy(
                    self.context_metadata.get("incomplete_details")
                ),
                "response_output_item_types": deepcopy(
                    self.context_metadata.get("response_output_item_types", [])
                ),
                "reasoning_tokens": self.context_metadata.get(
                    "reasoning_tokens", "unavailable"
                ),
                "output_tokens": self.context_metadata.get(
                    "output_tokens", "unavailable"
                ),
                "request_payload": deepcopy(
                    self.context_metadata.get("request_payload", {})
                ),
                "request_hash": self.context_metadata.get(
                    "request_hash", "NOT_APPLICABLE"
                ),
            }
        )
        return metadata


def _response_output_item_types(payload: Mapping[str, Any]) -> list[str]:
    output = payload.get("output")
    if not isinstance(output, list):
        return []
    return [
        str(item.get("type"))
        for item in output
        if isinstance(item, dict) and item.get("type") is not None
    ]


def _usage_value(payload: Mapping[str, Any], key: str) -> int | str:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return "unavailable"
    value = usage.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else "unavailable"


def _reasoning_tokens(payload: Mapping[str, Any]) -> int | str:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return "unavailable"
    details = usage.get("output_tokens_details")
    if not isinstance(details, dict):
        return "unavailable"
    value = details.get("reasoning_tokens")
    return value if isinstance(value, int) and not isinstance(value, bool) else "unavailable"


def _incomplete_details(payload: Mapping[str, Any]) -> dict[str, Any] | str:
    value = payload.get("incomplete_details")
    return deepcopy(value) if isinstance(value, dict) else "unavailable"


def _response_observation(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "response_status": payload.get("status", "unavailable"),
        "incomplete_details": _incomplete_details(payload),
        "response_output_item_types": _response_output_item_types(payload),
        "reasoning_tokens": _reasoning_tokens(payload),
        "output_tokens": _usage_value(payload, "output_tokens"),
    }


def _extract_message_output_text(payload: Mapping[str, Any]) -> tuple[str, str]:
    output = payload.get("output")
    if not isinstance(output, list):
        raise ValueError("Responses payload contains no output list")
    parts: list[str] = []
    first_path = ""
    for output_index, item in enumerate(output):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content)
            first_path = first_path or f"output[{output_index}].content"
            continue
        if not isinstance(content, list):
            continue
        for content_index, part in enumerate(content):
            if (
                isinstance(part, dict)
                and part.get("type") == "output_text"
                and isinstance(part.get("text"), str)
                and part["text"].strip()
            ):
                parts.append(part["text"])
                first_path = first_path or (
                    f"output[{output_index}].content[{content_index}].text"
                )
    if parts:
        return "".join(parts), first_path
    raise ValueError("Responses payload contains no message output_text")


def parse_responses_provider_body(
    raw_body: str,
    *,
    http_status: int | str = "unavailable",
    response_headers: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify one Responses response without passing reasoning to the parser."""

    headers = _safe_response_headers(response_headers or {})
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ResponsesProviderError(
            "PROVIDER_RESPONSE_INVALID",
            f"provider response is not valid JSON: {exc.msg}",
            raw_response_body=raw_body,
            http_status=http_status,
            response_headers=headers,
        ) from exc
    if not isinstance(payload, dict):
        raise ResponsesProviderError(
            "PROVIDER_RESPONSE_INVALID",
            "Responses provider response JSON is not an object",
            raw_response_body=raw_body,
            provider_payload=payload,
            http_status=http_status,
            response_headers=headers,
        )

    observation = _response_observation(payload)
    observed_keys = sorted(str(key) for key in payload)
    base_error = {
        "raw_response_body": raw_body,
        "provider_payload": payload,
        "http_status": http_status,
        "response_headers": headers,
        "observed_keys": observed_keys,
        "context_metadata": observation,
    }
    if isinstance(http_status, int) and http_status >= 400:
        raise ResponsesProviderError(
            HTTP_FAILED,
            f"provider returned HTTP {http_status}",
            **base_error,
        )

    response_status = payload.get("status")
    if response_status == "failed":
        raise ResponsesProviderError(
            PROVIDER_FAILED,
            "Responses provider returned status=failed",
            **base_error,
        )
    if response_status == "incomplete":
        reason = (payload.get("incomplete_details") or {}).get("reason")
        raise ResponsesProviderError(
            PROVIDER_INCOMPLETE,
            f"Responses provider returned incomplete status: {reason or 'unknown'}",
            **base_error,
        )
    if response_status != "completed":
        raise ResponsesProviderError(
            "PROVIDER_RESPONSE_INVALID",
            f"unexpected Responses status: {response_status!r}",
            **base_error,
        )

    try:
        raw_model_text, extraction_path = _extract_message_output_text(payload)
    except ValueError as exc:
        has_reasoning = "reasoning" in observation["response_output_item_types"]
        status = (
            PROVIDER_MODE_CONTROL_FAILED
            if has_reasoning
            else CONTENT_EXTRACTION_FAILED
        )
        raise ResponsesProviderError(
            status,
            str(exc),
            extraction_status="FAILED",
            **base_error,
        ) from exc

    reasoning_tokens = observation["reasoning_tokens"]
    if isinstance(reasoning_tokens, int) and reasoning_tokens > 0:
        raise ResponsesProviderError(
            PROVIDER_MODE_CONTROL_FAILED,
            "reasoning tokens were returned although effort=none was requested",
            extraction_status="SUCCESS",
            extraction_path=extraction_path,
            context_metadata={
                **observation,
                "raw_model_text": raw_model_text,
                "raw_response_hash": hashlib.sha256(
                    raw_model_text.encode("utf-8")
                ).hexdigest(),
            },
            **{
                key: value
                for key, value in base_error.items()
                if key != "context_metadata"
            },
        )

    return {
        "provider_status": COMPLETED,
        "http_status": http_status,
        "response_status": response_status,
        "incomplete_details": observation["incomplete_details"],
        "response_output_item_types": observation["response_output_item_types"],
        "reasoning_tokens": reasoning_tokens,
        "output_tokens": observation["output_tokens"],
        "provider_payload": deepcopy(payload),
        "raw_response_body": raw_body,
        "raw_response_body_hash": hashlib.sha256(raw_body.encode("utf-8")).hexdigest(),
        "observed_keys": observed_keys,
        "raw_model_text": raw_model_text,
        "extraction_status": "SUCCESS",
        "extraction_path": extraction_path,
    }


def _responses_base_url() -> str:
    configured = os.getenv("DEEPSEEK_RESPONSES_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL")
    if not configured:
        return "https://api.deepseek.com"
    value = configured.rstrip("/")
    for suffix in ("/anthropic", "/v1"):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
            break
    return value.rstrip("/")


class DeepSeekResponsesProvider:
    """DeepSeek official Responses API provider, fixed to non-thinking mode."""

    provider = "deepseek"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = 60.0,
        prompt_version: str = "stage3-customer-support-v1",
        max_output_tokens: int = RESPONSES_DEFAULT_MAX_OUTPUT_TOKENS,
        reasoning_effort: str = DEFAULT_REASONING_EFFORT,
        provider_config_version: str = RESPONSES_PROVIDER_CONFIG_VERSION,
    ):
        if not api_key:
            raise ValueError("DeepSeek Responses provider requires an API key")
        if max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        if reasoning_effort != "none":
            raise ValueError("Responses provider is frozen to reasoning.effort=none")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.prompt_version = prompt_version
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = reasoning_effort
        self.provider_config_version = provider_config_version

    @classmethod
    def from_environment(
        cls,
        *,
        model: str | None = None,
        max_output_tokens: int = RESPONSES_DEFAULT_MAX_OUTPUT_TOKENS,
        reasoning_effort: str = DEFAULT_REASONING_EFFORT,
        provider_config_version: str = RESPONSES_PROVIDER_CONFIG_VERSION,
    ) -> "DeepSeekResponsesProvider":
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY or ANTHROPIC_AUTH_TOKEN is required")
        return cls(
            api_key=api_key,
            base_url=_responses_base_url(),
            model=model or os.getenv("DEEPSEEK_MODEL") or DEFAULT_MODEL,
            max_output_tokens=max_output_tokens,
            reasoning_effort=reasoning_effort,
            provider_config_version=provider_config_version,
        )

    def _context_metadata(
        self,
        prompt: str,
        prompt_evidence: dict[str, Any],
        payload: dict[str, Any],
        grounding_projection: dict[str, Any],
        generation_contract: dict[str, Any],
    ) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return {
            "provider": self.provider,
            "api_format": "responses",
            "provider_adapter_version": RESPONSES_PROVIDER_ADAPTER_VERSION,
            "provider_config_version": self.provider_config_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_payload": deepcopy(payload),
            "request_hash": hashlib.sha256(body).hexdigest(),
            "prompt": prompt,
            **prompt_evidence,
            "prompt_hash": prompt_evidence["prompt_text_hash"],
            "prompt_version": self.prompt_version,
            "grounding_hash": str(grounding_projection.get("sha256", "")),
            "fixture_version": generation_contract.get("fixture_version", "unavailable"),
            "runtime_version": generation_contract.get("runtime_version", "unavailable"),
            "schema_version": generation_contract.get("schema_version", "unavailable"),
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "thinking_mode": "disabled",
            "max_output_tokens": self.max_output_tokens,
            "max_tokens": "unavailable",
            "temperature": "unavailable",
            "top_p": "unavailable",
            "sampling_parameters": "unavailable",
            "exact_backend_revision": "unavailable",
        }

    def generate(
        self,
        grounding_projection: dict[str, Any],
        generation_contract: dict[str, Any],
        request_context: dict[str, Any],
    ) -> RawGenerationResult:
        prompt_evidence = customer_message_prompt_evidence(
            grounding_projection,
            generation_contract,
            request_context,
        )
        prompt = prompt_evidence["prompt"]
        payload = {
            "model": self.model,
            "input": prompt,
            "reasoning": {"effort": self.reasoning_effort},
            "max_output_tokens": self.max_output_tokens,
        }
        context_metadata = self._context_metadata(
            prompt, prompt_evidence, payload, grounding_projection, generation_contract
        )
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/responses",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                http_status = _http_status(getattr(response, "status", "unavailable"))
                response_headers = _safe_response_headers(getattr(response, "headers", {}))
                raw_body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            response_headers = _safe_response_headers(exc.headers)
            raw_body = exc.read().decode("utf-8", errors="replace")
            try:
                parse_responses_provider_body(
                    raw_body,
                    http_status=int(exc.code),
                    response_headers=response_headers,
                )
            except ResponsesProviderError as error:
                error.context_metadata.update(context_metadata)
                raise
            raise ResponsesProviderError(
                HTTP_FAILED,
                f"provider returned HTTP {exc.code}",
                raw_response_body=raw_body,
                http_status=int(exc.code),
                response_headers=response_headers,
                context_metadata=context_metadata,
            )
        except urllib.error.URLError as exc:
            raise ResponsesProviderError(
                NETWORK_FAILED,
                f"provider network request failed: {exc.reason}",
                context_metadata=context_metadata,
            ) from exc
        except (TimeoutError, OSError) as exc:
            raise ResponsesProviderError(
                NETWORK_FAILED,
                f"provider network request failed: {exc}",
                context_metadata=context_metadata,
            ) from exc

        try:
            response_info = parse_responses_provider_body(
                raw_body,
                http_status=http_status,
                response_headers=response_headers,
            )
        except ResponsesProviderError as error:
            error.context_metadata.update(context_metadata)
            raise

        raw_model_text = response_info["raw_model_text"]
        parsed_candidate, parse_status = parse_candidate(raw_model_text)
        response_payload = response_info["provider_payload"]
        metadata = {
            **context_metadata,
            "provider_status": COMPLETED,
            "http_status": http_status,
            "response_status": response_info["response_status"],
            "incomplete_details": response_info["incomplete_details"],
            "response_output_item_types": response_info["response_output_item_types"],
            "reasoning_tokens": response_info["reasoning_tokens"],
            "output_tokens": response_info["output_tokens"],
            "content_type": response_headers.get("content-type", "unavailable"),
            "response_headers": response_headers,
            "provider_payload": deepcopy(response_payload),
            "raw_response_body": raw_body,
            "raw_response_body_hash": response_info["raw_response_body_hash"],
            "observed_keys": response_info["observed_keys"],
            "extraction_status": response_info["extraction_status"],
            "extraction_path": response_info["extraction_path"],
            "raw_model_text": raw_model_text,
            "raw_response_hash": hashlib.sha256(raw_model_text.encode("utf-8")).hexdigest(),
            "parse_status": parse_status,
        }
        return RawGenerationResult(
            provider=self.provider,
            model=str(response_payload.get("model") or self.model),
            raw_response=raw_model_text,
            parsed_candidate=parsed_candidate,
            parse_status=parse_status,
            metadata=metadata,
        )

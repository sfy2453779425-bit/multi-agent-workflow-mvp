"""Provider-neutral candidate parsing primitives."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import inspect
import os
from collections.abc import Mapping
from typing import Any, Protocol
import urllib.error
import urllib.request


PARSE_OK = "PARSE_OK"
PARSE_FAILED = "PARSE_FAILED"
PARTIAL = "PARTIAL"

NETWORK_FAILED = "NETWORK_FAILED"
HTTP_FAILED = "HTTP_FAILED"
PROVIDER_REJECTED = "PROVIDER_REJECTED"
PROVIDER_RESPONSE_INVALID = "PROVIDER_RESPONSE_INVALID"
CONTENT_EXTRACTION_FAILED = "CONTENT_EXTRACTION_FAILED"
COMPLETED = "COMPLETED"
PROVIDER_ADAPTER_VERSION = "deepseek-anthropic-adapter-v1.2"
PROVIDER_CONFIG_VERSION = "deepseek-v4-pro-nonthinking-v1"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_THINKING_MODE = "disabled"
DEFAULT_REASONING_EFFORT = "none"
PROMPT_BUILDER_VERSION = "customer-message-prompt-v2"


def _safe_response_headers(headers: object) -> dict[str, str]:
    if not hasattr(headers, "items"):
        return {}
    blocked = {
        "authorization",
        "x-api-key",
        "api-key",
        "cookie",
        "set-cookie",
        "proxy-authorization",
    }
    try:
        items = headers.items()  # type: ignore[union-attr]
        return {
            str(key).lower(): str(value)
            for key, value in items
            if str(key).lower() not in blocked
        }
    except (TypeError, AttributeError):
        return {}


@dataclass(frozen=True)
class RawGenerationResult:
    provider: str
    model: str
    raw_response: str
    parsed_candidate: dict[str, Any]
    parse_status: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ProviderResponseError(RuntimeError):
    """A provider response was received or attempted but could not yield model text."""

    def __init__(
        self,
        provider_status: str,
        message: str,
        *,
        raw_response_body: str = "",
        provider_payload: Any = "NOT_APPLICABLE",
        http_status: int | str = "NOT_APPLICABLE",
        response_headers: Mapping[str, Any] | None = None,
        observed_keys: list[str] | None = None,
        extraction_status: str = "NOT_APPLICABLE",
        extraction_path: str = "NOT_APPLICABLE",
        context_metadata: Mapping[str, Any] | None = None,
    ):
        self.provider_status = provider_status
        self.raw_response_body = raw_response_body
        self.provider_payload = provider_payload
        self.http_status = http_status
        self.response_headers = _safe_response_headers(response_headers or {})
        self.observed_keys = list(observed_keys or [])
        self.extraction_status = extraction_status
        self.extraction_path = extraction_path
        self.context_metadata = dict(context_metadata or {})
        self.raw_response_body_hash = hashlib.sha256(
            raw_response_body.encode("utf-8")
        ).hexdigest() if raw_response_body else "NOT_APPLICABLE"
        super().__init__(message)

    def to_metadata(self) -> dict[str, Any]:
        return {
            **self.context_metadata,
            "provider_status": self.provider_status,
            "http_status": self.http_status,
            "content_type": self.response_headers.get("content-type", "unavailable"),
            "response_headers": dict(self.response_headers),
            "provider_payload": deepcopy(self.provider_payload),
            "raw_response_body": self.raw_response_body or "NOT_APPLICABLE",
            "raw_response_body_hash": self.raw_response_body_hash,
            "observed_keys": list(self.observed_keys),
            "extraction_status": self.extraction_status,
            "extraction_path": self.extraction_path,
            "error": str(self),
            "sampling_parameters": self.context_metadata.get(
                "sampling_parameters", "unavailable"
            ),
            "exact_backend_revision": self.context_metadata.get(
                "exact_backend_revision", "unavailable"
            ),
        }


class GenerativeCandidateProvider(Protocol):
    def generate(
        self,
        grounding_projection: dict[str, Any],
        generation_contract: dict[str, Any],
        request_context: dict[str, Any],
    ) -> RawGenerationResult:
        ...


def _canonical_generation_json(value: dict[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def build_customer_message_generation_input(
    grounding_projection: dict[str, Any],
    generation_contract: dict[str, Any],
    request_context: dict[str, Any],
) -> dict[str, Any]:
    allowed = list(generation_contract.get("allowed_output_fields") or ["customer_message"])
    return {
        "request_context": deepcopy(request_context),
        "authoritative_facts": deepcopy(grounding_projection.get("authoritative_facts") or {}),
        "allowed_output_fields": allowed,
    }


def _render_customer_message_prompt(generation_input: dict[str, Any]) -> str:
    allowed = generation_input["allowed_output_fields"]
    return (
        "Generate one JSON object for the customer support response.\n"
        "Use the authoritative facts as supplied. Do not decide or rewrite them.\n"
        f"Generate only these fields: {', '.join(allowed)}.\n"
        "Return JSON only.\n\n"
        + json.dumps(generation_input, ensure_ascii=False, sort_keys=True, indent=2)
    )


def prompt_builder_hash() -> str:
    source = inspect.getsource(build_customer_message_generation_input) + inspect.getsource(
        _render_customer_message_prompt
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def customer_message_prompt_evidence(
    grounding_projection: dict[str, Any],
    generation_contract: dict[str, Any],
    request_context: dict[str, Any],
) -> dict[str, Any]:
    generation_input = build_customer_message_generation_input(
        grounding_projection, generation_contract, request_context
    )
    prompt = _render_customer_message_prompt(generation_input)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return {
        "generation_input": generation_input,
        "generation_input_hash": hashlib.sha256(
            _canonical_generation_json(generation_input).encode("utf-8")
        ).hexdigest(),
        "prompt": prompt,
        "prompt_text_hash": prompt_hash,
        "provider_request_prompt_hash": prompt_hash,
        "prompt_builder_version": PROMPT_BUILDER_VERSION,
        "prompt_builder_hash": prompt_builder_hash(),
    }


def build_customer_message_prompt(
    grounding_projection: dict[str, Any],
    generation_contract: dict[str, Any],
    request_context: dict[str, Any],
) -> str:
    return customer_message_prompt_evidence(
        grounding_projection, generation_contract, request_context
    )["prompt"]


def build_customer_support_prompt(
    grounding_projection: dict[str, Any],
    generation_contract: dict[str, Any],
    request_context: dict[str, Any],
) -> str:
    """Backward-compatible alias for the canonical customer-message builder."""

    return build_customer_message_prompt(
        grounding_projection, generation_contract, request_context
    )


class MockCandidateProvider:
    """Deterministic provider for offline adapter and Runtime tests."""

    def __init__(self, candidate: dict[str, Any], model: str = "mock-model"):
        if not isinstance(candidate, dict):
            raise TypeError("mock candidate must be an object")
        self._candidate = deepcopy(candidate)
        self.model = model

    def generate(
        self,
        grounding_projection: dict[str, Any],
        generation_contract: dict[str, Any],
        request_context: dict[str, Any],
    ) -> RawGenerationResult:
        raw_response = json.dumps(self._candidate, ensure_ascii=False, separators=(",", ":"))
        parsed_candidate, parse_status = parse_candidate(raw_response)
        return RawGenerationResult(
            provider="mock",
            model=self.model,
            raw_response=raw_response,
            parsed_candidate=parsed_candidate,
            parse_status=parse_status,
            metadata={
                "sampling_parameters": "unavailable",
                "exact_backend_revision": "unavailable",
            },
        )


class DeepSeekCandidateProvider:
    """DeepSeek provider through the configured Anthropic-compatible endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 60.0,
        prompt_version: str = "stage3-customer-support-v1",
        max_tokens: int = DEFAULT_MAX_TOKENS,
        thinking_mode: str = DEFAULT_THINKING_MODE,
        reasoning_effort: str = DEFAULT_REASONING_EFFORT,
        provider_config_version: str = PROVIDER_CONFIG_VERSION,
    ):
        if not api_key:
            raise ValueError("DeepSeek provider requires an API key")
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.prompt_version = prompt_version
        self.max_tokens = max_tokens
        self.thinking_mode = thinking_mode
        self.reasoning_effort = reasoning_effort
        self.provider_config_version = provider_config_version

    @classmethod
    def from_environment(
        cls,
        *,
        model: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        thinking_mode: str = DEFAULT_THINKING_MODE,
        reasoning_effort: str = DEFAULT_REASONING_EFFORT,
        provider_config_version: str = PROVIDER_CONFIG_VERSION,
    ) -> "DeepSeekCandidateProvider":
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY or ANTHROPIC_AUTH_TOKEN is required")
        return cls(
            api_key=api_key,
            base_url=(
                os.getenv("DEEPSEEK_BASE_URL")
                or os.getenv("ANTHROPIC_BASE_URL")
                or "https://api.deepseek.com/anthropic"
            ),
            model=model or os.getenv("DEEPSEEK_MODEL") or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL,
            max_tokens=max_tokens,
            thinking_mode=thinking_mode,
            reasoning_effort=reasoning_effort,
            provider_config_version=provider_config_version,
        )

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
            "max_tokens": self.max_tokens,
            "reasoning": {"effort": self.reasoning_effort},
            "messages": [{"role": "user", "content": prompt}],
        }
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request_hash = hashlib.sha256(body).hexdigest()
        endpoint = self.base_url + ("/messages" if self.base_url.endswith("/v1") else "/v1/messages")
        timestamp = datetime.now(timezone.utc).isoformat()
        context_metadata = {
            "timestamp": timestamp,
            "request_hash": request_hash,
            **prompt_evidence,
            "prompt_hash": prompt_evidence["prompt_text_hash"],
            "prompt": prompt,
            "prompt_version": self.prompt_version,
            "grounding_hash": str(grounding_projection.get("sha256", "")),
            "fixture_version": generation_contract.get("fixture_version", "unavailable"),
            "runtime_version": generation_contract.get("runtime_version", "unavailable"),
            "schema_version": generation_contract.get("schema_version", "unavailable"),
            "model": self.model,
            "thinking_mode": self.thinking_mode,
            "reasoning_effort": self.reasoning_effort,
            "max_tokens": self.max_tokens,
            "temperature": "unavailable",
            "top_p": "unavailable",
            "provider_config_version": self.provider_config_version,
            "sampling_parameters": "unavailable",
            "exact_backend_revision": "unavailable",
        }
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "anthropic-version": "2023-06-01",
                "x-api-key": self.api_key,
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
                parse_provider_response_body(
                    raw_body,
                    http_status=int(exc.code),
                    response_headers=response_headers,
                )
            except ProviderResponseError as error:
                error.context_metadata.update(context_metadata)
                raise
            raise ProviderResponseError(
                HTTP_FAILED,
                f"provider returned HTTP {exc.code}",
                raw_response_body=raw_body,
                http_status=int(exc.code),
                response_headers=response_headers,
                context_metadata=context_metadata,
            )
        except urllib.error.URLError as exc:
            raise ProviderResponseError(
                NETWORK_FAILED,
                f"provider network request failed: {exc.reason}",
                context_metadata=context_metadata,
            ) from exc
        except (TimeoutError, OSError) as exc:
            raise ProviderResponseError(
                NETWORK_FAILED,
                f"provider network request failed: {exc}",
                context_metadata=context_metadata,
            ) from exc

        try:
            response_info = parse_provider_response_body(
                raw_body,
                http_status=http_status,
                response_headers=response_headers,
            )
        except ProviderResponseError as error:
            error.context_metadata.update(context_metadata)
            raise

        raw_response = response_info["raw_model_text"]
        parsed_candidate, parse_status = parse_candidate(raw_response)
        response_payload = response_info["provider_payload"]
        metadata = {
            **context_metadata,
            "provider_status": COMPLETED,
            "http_status": http_status,
            "content_type": response_headers.get("content-type", "unavailable"),
            "response_headers": response_headers,
            "provider_payload": deepcopy(response_payload),
            "raw_response_body": raw_body,
            "raw_response_body_hash": response_info["raw_response_body_hash"],
            "observed_keys": response_info["observed_keys"],
            "extraction_status": response_info["extraction_status"],
            "extraction_path": response_info["extraction_path"],
            "raw_model_text": raw_response,
            "raw_response_hash": hashlib.sha256(raw_response.encode("utf-8")).hexdigest(),
        }
        return RawGenerationResult(
            provider="deepseek",
            model=str(response_payload.get("model") or self.model),
            raw_response=raw_response,
            parsed_candidate=parsed_candidate,
            parse_status=parse_status,
            metadata=metadata,
        )


def _http_status(value: object) -> int | str:
    return value if isinstance(value, int) and not isinstance(value, bool) else "unavailable"


def _extract_provider_text_with_path(payload: Mapping[str, Any]) -> tuple[str, str]:
    content = payload.get("content")
    if isinstance(content, list):
        text_parts = [
            item["text"]
            for item in content
            if isinstance(item, dict)
            and item.get("type") == "text"
            and isinstance(item.get("text"), str)
            and item["text"].strip()
        ]
        if text_parts:
            first_index = next(
                index
                for index, item in enumerate(content)
                if isinstance(item, dict)
                and item.get("type") == "text"
                and isinstance(item.get("text"), str)
                and item["text"].strip()
            )
            return "".join(text_parts), f"content[{first_index}].text"
    if isinstance(content, str) and content.strip():
        return content, "content"
    for key in ("answer", "text", "output"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value, key
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            if message["content"].strip():
                return message["content"], "choices[0].message.content"
    raise ValueError("provider response contains no text content")


def _extract_provider_text(payload: dict[str, Any]) -> str:
    """Extract model text while retaining the legacy helper's return type."""

    return _extract_provider_text_with_path(payload)[0]


def parse_provider_response_body(
    raw_body: str,
    *,
    http_status: int | str = "unavailable",
    response_headers: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify and extract one provider response without discarding its payload."""

    headers = _safe_response_headers(response_headers or {})
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ProviderResponseError(
            PROVIDER_RESPONSE_INVALID,
            f"provider response is not valid JSON: {exc.msg}",
            raw_response_body=raw_body,
            http_status=http_status,
            response_headers=headers,
        ) from exc

    if not isinstance(payload, dict):
        raise ProviderResponseError(
            PROVIDER_RESPONSE_INVALID,
            "provider response JSON is not an object",
            raw_response_body=raw_body,
            provider_payload=payload,
            http_status=http_status,
            response_headers=headers,
        )

    observed_keys = sorted(str(key) for key in payload)
    if payload.get("type") == "error" or "error" in payload:
        raise ProviderResponseError(
            PROVIDER_REJECTED,
            "provider returned a structured error response",
            raw_response_body=raw_body,
            provider_payload=payload,
            http_status=http_status,
            response_headers=headers,
            observed_keys=observed_keys,
        )
    if isinstance(http_status, int) and http_status >= 400:
        raise ProviderResponseError(
            HTTP_FAILED,
            f"provider returned HTTP {http_status}",
            raw_response_body=raw_body,
            provider_payload=payload,
            http_status=http_status,
            response_headers=headers,
            observed_keys=observed_keys,
        )

    try:
        raw_model_text, extraction_path = _extract_provider_text_with_path(payload)
    except ValueError as exc:
        raise ProviderResponseError(
            CONTENT_EXTRACTION_FAILED,
            str(exc),
            raw_response_body=raw_body,
            provider_payload=payload,
            http_status=http_status,
            response_headers=headers,
            observed_keys=observed_keys,
            extraction_status="FAILED",
        ) from exc

    return {
        "provider_status": COMPLETED,
        "http_status": http_status,
        "provider_payload": deepcopy(payload),
        "raw_response_body": raw_body,
        "raw_response_body_hash": hashlib.sha256(raw_body.encode("utf-8")).hexdigest(),
        "observed_keys": observed_keys,
        "raw_model_text": raw_model_text,
        "extraction_status": "SUCCESS",
        "extraction_path": extraction_path,
    }


class ProviderGenerativeNode:
    """Turn a provider-neutral generation result into a Runtime node result."""

    def __init__(self, provider: GenerativeCandidateProvider, generation_contract: dict[str, Any]):
        self.provider = provider
        self.generation_contract = dict(generation_contract)

    def execute(self, context: dict[str, Any], node_config: dict[str, Any]) -> Any:
        from .node_registry import NodeExecutionResult

        inputs = node_config.get("inputs") or {}
        projection = inputs.get("grounding") or {}
        request_context = dict(projection.get("request_context") or {})
        request_context.update(
            {
                name: value
                for name, value in inputs.items()
                if name != "grounding" and name not in request_context
            }
        )
        try:
            generation = self.provider.generate(
                projection,
                self.generation_contract,
                request_context,
            )
        except ProviderResponseError as exc:
            return NodeExecutionResult(
                outputs={},
                raw_candidate={},
                raw_response="",
                provider=str(getattr(self.provider, "provider", "deepseek")),
                model=str(getattr(self.provider, "model", "unavailable")),
                parse_status=PARSE_FAILED,
                metadata=exc.to_metadata(),
                detail=(
                    "generative provider response failed; "
                    f"status={exc.provider_status}; candidate gate will use fallback"
                ),
            )
        except Exception as exc:
            return NodeExecutionResult(
                outputs={},
                raw_candidate={},
                raw_response="",
                provider=str(getattr(self.provider, "provider", "real")),
                model=str(getattr(self.provider, "model", "unavailable")),
                parse_status=PARSE_FAILED,
                metadata={
                    "error": str(exc),
                    "provider_status": PROVIDER_RESPONSE_INVALID,
                    "sampling_parameters": "unavailable",
                    "exact_backend_revision": "unavailable",
                },
                detail="generative provider failed; candidate gate will use fallback",
            )
        parsed = deepcopy(generation.parsed_candidate)
        return NodeExecutionResult(
            outputs=deepcopy(parsed),
            raw_candidate=parsed,
            raw_response=generation.raw_response,
            provider=generation.provider,
            model=generation.model,
            parse_status=generation.parse_status,
            metadata=deepcopy(generation.metadata),
            detail="generative provider returned candidate",
            data={"parse_status": generation.parse_status},
        )


def parse_candidate(raw_response: str) -> tuple[dict[str, Any], str]:
    """Parse one JSON object without filtering any candidate fields."""

    if not isinstance(raw_response, str) or not raw_response.strip():
        return {}, PARSE_FAILED
    text = raw_response.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return {}, PARSE_FAILED
        try:
            value = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}, PARSE_FAILED
        return value if isinstance(value, dict) else {}, PARTIAL
    if not isinstance(value, dict):
        return {}, PARSE_FAILED
    return value, PARSE_OK

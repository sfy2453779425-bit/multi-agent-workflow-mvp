import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LocalLLMNodeConfig:
    enabled: bool = False
    provider: str = "mock"
    model: str = "Qwen2.5-1.5B-Instruct"
    role: str = "compose"
    endpoint: str = ""
    replay_path: str = ""
    timeout_seconds: float = 30.0
    max_prompt_chars: int = 4000
    fallback_to_mock: bool = True
    extra_headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "LocalLLMNodeConfig":
        if not value:
            return cls()
        allowed = {
            "enabled",
            "provider",
            "model",
            "role",
            "endpoint",
            "replay_path",
            "timeout_seconds",
            "max_prompt_chars",
            "fallback_to_mock",
            "extra_headers",
        }
        return cls(**{key: value[key] for key in allowed if key in value})


@dataclass(frozen=True)
class LocalLLMResult:
    text: str
    provider: str
    model: str
    prompt: str
    metrics: dict[str, Any]


class LocalLLMNode:
    """Optional local LLM workflow node with mock and remote providers.

    The mock provider makes the project demonstrable without requiring a GPU on
    the user's laptop. The remote provider is a thin HTTP boundary for a future
    GPU-hosted Qwen service.
    """

    def __init__(self, config: LocalLLMNodeConfig | dict[str, Any] | None = None):
        if isinstance(config, LocalLLMNodeConfig):
            self.config = config
        else:
            self.config = LocalLLMNodeConfig.from_dict(config)

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def run(self, context: dict[str, Any]) -> LocalLLMResult:
        prompt = self._build_prompt(context)[: self.config.max_prompt_chars]
        if self.config.provider == "remote":
            try:
                return self._run_remote(prompt, context)
            except Exception as exc:
                if not self.config.fallback_to_mock:
                    raise
                return self._run_mock(prompt, context, error=str(exc))
        if self.config.provider == "replay":
            try:
                return self._run_replay(prompt, context)
            except Exception as exc:
                if not self.config.fallback_to_mock:
                    raise
                return self._run_mock(prompt, context, error=str(exc))
        return self._run_mock(prompt, context)

    def _build_prompt(self, context: dict[str, Any]) -> str:
        payload = {
            "workflow_name": context.get("workflow_name", ""),
            "runtime_type": context.get("runtime_type", ""),
            "user_query": context.get("query", ""),
            "weather_summary": context.get("weather_summary", {}),
            "shopping_analysis_summary": context.get("shopping_analysis_summary", {}),
            "ranked_items": context.get("ranked_items", []),
            "summary_cards": context.get("summary_cards", []),
            "executed_agents": context.get("executed_agents", []),
        }
        return (
            "You are a Local LLM Node for a Template-based Multi-Agent Workflow Builder.\n"
            f"Role: {self.config.role}\n"
            "Use the structured context to produce a concise final enhancement.\n"
            "Do not invent external tool outputs.\n\n"
            + json.dumps(payload, ensure_ascii=False, indent=2)
        )

    def _run_mock(
        self,
        prompt: str,
        context: dict[str, Any],
        *,
        error: str = "",
    ) -> LocalLLMResult:
        start = time.perf_counter()
        workflow_name = context.get("workflow_name", "Workflow")
        ranked_items = context.get("ranked_items", [])
        summary_cards = context.get("summary_cards", [])
        if ranked_items:
            evidence = "; ".join(str(item) for item in ranked_items[:3])
        elif summary_cards:
            evidence = "; ".join(card.get("title", "") for card in summary_cards[:3])
        else:
            evidence = "structured workflow context"

        lines = [
            "[Local LLM Node]",
            f"Model candidate: {self.config.model}",
            f"Workflow: {workflow_name}",
            f"Role: {self.config.role}",
            f"Evidence: {evidence}",
            "This mock output verifies the Local LLM Node interface without requiring GPU inference.",
        ]
        if error:
            lines.append(f"Remote fallback reason: {error}")
        text = "\n".join(lines)
        elapsed = time.perf_counter() - start
        metrics = {
            "latency_seconds": round(elapsed, 4),
            "prompt_chars": len(prompt),
            "generated_chars": len(text),
            "tokens_per_second": 0,
            "fallback": bool(error),
        }
        return LocalLLMResult(
            text=text,
            provider="mock",
            model=self.config.model,
            prompt=prompt,
            metrics=metrics,
        )

    def _run_replay(self, prompt: str, context: dict[str, Any]) -> LocalLLMResult:
        if not self.config.replay_path:
            raise ValueError("replay Local LLM provider requires replay_path")

        result_path = Path(self.config.replay_path)
        if not result_path.is_absolute():
            result_path = Path.cwd() / result_path
        if result_path.is_dir():
            candidates = sorted(result_path.glob("single_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
            if not candidates:
                raise FileNotFoundError(f"no single_*.json replay result in {result_path}")
            result_path = candidates[0]
        if not result_path.exists():
            raise FileNotFoundError(str(result_path))

        record = json.loads(result_path.read_text(encoding="utf-8"))
        answer = str(record.get("answer", "")).strip()
        if not answer:
            rows = record.get("rows", [])
            if rows:
                answer = str(rows[0].get("answer", "")).strip()
        if not answer:
            raise ValueError(f"replay result has no answer: {result_path}")

        model = str(record.get("model") or self.config.model)
        metrics = {
            "source": str(result_path),
            "load_seconds": record.get("load_seconds", 0),
            "infer_seconds": record.get("infer_seconds", 0),
            "generated_tokens": record.get("generated_tokens", 0),
            "tokens_per_second": record.get("token_per_second", record.get("tokens_per_second", 0)),
            "peak_memory_mb": record.get("peak_torch_allocated_mb", record.get("peak_memory_mb", 0)),
            "replay": True,
        }
        text = "\n".join(
            [
                "[Local LLM Node - GPU Replay]",
                f"Model: {model}",
                f"Source: {result_path.name}",
                f"token/s: {metrics['tokens_per_second']}",
                "",
                answer,
            ]
        )
        return LocalLLMResult(
            text=text,
            provider="replay",
            model=model,
            prompt=prompt,
            metrics=metrics,
        )

    def _run_remote(self, prompt: str, context: dict[str, Any]) -> LocalLLMResult:
        if not self.config.endpoint:
            raise ValueError("remote Local LLM provider requires endpoint")

        payload = {
            "model": self.config.model,
            "role": self.config.role,
            "prompt": prompt,
            "context": {
                "workflow_name": context.get("workflow_name", ""),
                "runtime_type": context.get("runtime_type", ""),
                "query": context.get("query", ""),
            },
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            **self.config.extra_headers,
        }
        request = urllib.request.Request(
            self.config.endpoint,
            data=data,
            headers=headers,
            method="POST",
        )

        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Local LLM remote request failed: {exc}") from exc
        elapsed = time.perf_counter() - start

        parsed = json.loads(body)
        text = parsed.get("answer") or parsed.get("text") or parsed.get("output") or ""
        metrics = {
            "latency_seconds": round(elapsed, 4),
            "prompt_chars": len(prompt),
            **parsed.get("metrics", {}),
        }
        return LocalLLMResult(
            text=text,
            provider="remote",
            model=parsed.get("model", self.config.model),
            prompt=prompt,
            metrics=metrics,
        )

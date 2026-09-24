"""Small registry and execution contract for workflow nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
from typing import Any, Callable, Protocol


class NodeHandler(Protocol):
    def execute(self, context: dict[str, Any], config: dict[str, Any]) -> Any:
        """Execute a node using the shared context and resolved node config."""


@dataclass(frozen=True)
class NodeExecutionResult:
    """Normalized result returned by a node handler."""

    outputs: dict[str, Any] = field(default_factory=dict)
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    halt: bool = False
    halt_reason: str = ""
    raw_candidate: dict[str, Any] | None = None
    raw_response: str | None = None
    provider: str = ""
    model: str = ""
    parse_status: str = "PARSE_OK"
    metadata: dict[str, Any] = field(default_factory=dict)


class MockGenerativeNode:
    """Scripted candidate source used by the P0 runtime tests."""

    def __init__(self, candidate: dict[str, Any]):
        if not isinstance(candidate, dict):
            raise TypeError("mock generative candidate must be an object")
        self._candidate = deepcopy(candidate)

    def execute(self, context: dict[str, Any], config: dict[str, Any]) -> NodeExecutionResult:
        raw_candidate = deepcopy(self._candidate)
        return NodeExecutionResult(
            outputs=deepcopy(raw_candidate),
            raw_candidate=raw_candidate,
            detail="mock generative candidate returned",
            data={"candidate_fields": sorted(raw_candidate)},
        )


class FunctionNodeHandler:
    """Adapter that keeps the registry friendly to existing bound methods."""

    def __init__(self, function: Callable[[dict[str, Any], dict[str, Any]], Any]):
        self.function = function

    def execute(self, context: dict[str, Any], config: dict[str, Any]) -> Any:
        return self.function(context, config)


@dataclass(frozen=True)
class WorkflowNode:
    """A configured node resolved from a Workflow JSON definition."""

    node_id: str
    node_type: str
    name: str
    inputs: dict[str, Any]
    outputs: dict[str, str]
    required_inputs: tuple[str, ...]
    config: dict[str, Any]
    handler: NodeHandler
    mode: str = "deterministic"

    def resolve_inputs(self, context: dict[str, Any]) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for name, binding in self.inputs.items():
            resolved[name] = resolve_binding(binding, context)
        return resolved

    def execute(self, context: dict[str, Any], inputs: dict[str, Any]) -> NodeExecutionResult:
        handler_config = {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "inputs": inputs,
            "config": dict(self.config),
        }
        result = self.handler.execute(context, handler_config)
        if isinstance(result, NodeExecutionResult):
            return result
        if isinstance(result, dict):
            return NodeExecutionResult(outputs=result)
        raise TypeError(
            f"node handler {self.node_type!r} must return NodeExecutionResult or dict, "
            f"got {type(result).__name__}"
        )


class UnknownNodeTypeError(ValueError):
    """Raised when a Workflow references a node type without a handler."""


class NodeRegistry:
    """Map declarative node types to small executable handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, NodeHandler] = {}

    def register(
        self,
        node_type: str,
        handler: NodeHandler | Callable[[dict[str, Any], dict[str, Any]], Any],
        *,
        replace: bool = False,
    ) -> None:
        if not node_type or not isinstance(node_type, str):
            raise ValueError("node_type must be a non-empty string")
        if node_type in self._handlers and not replace:
            raise ValueError(f"node type already registered: {node_type}")
        if not hasattr(handler, "execute"):
            handler = FunctionNodeHandler(handler)
        self._handlers[node_type] = handler  # type: ignore[assignment]

    def get(self, node_type: str) -> NodeHandler:
        try:
            return self._handlers[node_type]
        except KeyError as exc:
            raise UnknownNodeTypeError(f"unknown node type: {node_type}") from exc

    def contains(self, node_type: str) -> bool:
        return node_type in self._handlers

    def node_types(self) -> tuple[str, ...]:
        return tuple(self._handlers)


def resolve_binding(binding: Any, context: dict[str, Any]) -> Any:
    """Resolve ``context.foo.bar`` bindings and preserve literal values."""

    if not isinstance(binding, str) or not binding.startswith("context."):
        return binding

    current: Any = context
    path = binding[len("context.") :]
    if not path:
        raise KeyError("context binding cannot be empty")
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"missing context input: {binding}")
        current = current[part]
    return current


def write_binding(binding: str, value: Any, context: dict[str, Any]) -> None:
    """Write a node output to a dotted context path."""

    if not isinstance(binding, str) or not binding.startswith("context."):
        raise ValueError(f"invalid output binding: {binding!r}")
    parts = binding[len("context.") :].split(".")
    if not parts or not parts[0]:
        raise ValueError(f"invalid output binding: {binding!r}")
    target = context
    for part in parts[:-1]:
        child = target.get(part)
        if child is None:
            child = {}
            target[part] = child
        if not isinstance(child, dict):
            raise ValueError(f"output binding crosses non-object context key: {binding}")
        target = child
    target[parts[-1]] = value

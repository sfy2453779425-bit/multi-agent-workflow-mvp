"""Declarative sequential Workflow JSON runtime and validation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from time import perf_counter
from typing import Any
from collections.abc import Mapping
from types import MappingProxyType

from agent_builder.engine import TraceStep
from agent_builder.node_registry import (
    NodeRegistry,
    NodeExecutionResult,
    UnknownNodeTypeError,
    WorkflowNode,
    write_binding,
)
from agent_builder.workflow_schema import (
    output_contract_from_workflow,
    upgrade_workflow_config,
    validate_output_contract,
)


WORKFLOW_RUNTIME_VERSION = "authoritative-contract-v1.1"


class WorkflowValidationError(ValueError):
    """Raised before execution when a Workflow JSON contract is invalid."""

    def __init__(self, message: str, errors: list[str] | None = None):
        self.errors = errors or [message]
        super().__init__(message)


@dataclass(frozen=True)
class WorkflowRun:
    context: dict[str, Any]
    trace: list[TraceStep]
    failed_node: str = ""
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return not self.failed_node


@dataclass(frozen=True)
class AuthoritativeSnapshot:
    fields: Mapping[str, Any]
    canonical_json: str
    sha256: str


def create_authoritative_snapshot(fields: dict[str, Any]) -> AuthoritativeSnapshot:
    copied = deepcopy(fields)
    canonical_json = json.dumps(
        copied,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return AuthoritativeSnapshot(
        fields=_freeze(copied),
        canonical_json=canonical_json,
        sha256=hashlib.sha256(canonical_json.encode("utf-8")).hexdigest(),
    )


def _consistency_result(
    rule_id: str,
    status: str,
    claims_found: list[str],
    conflicts: list[str],
    reason: str,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "status": status,
        "claims_found": claims_found,
        "conflicts": conflicts,
        "reason": reason,
    }


def _priority_consistency(text: str, expected: Any) -> dict[str, Any]:
    claims = []
    for match in re.findall(r"(?<![A-Za-z0-9])P([1-3])(?![A-Za-z0-9])", text, re.IGNORECASE):
        claim = f"P{match.upper()}"
        if claim not in claims:
            claims.append(claim)
    if not claims:
        return _consistency_result(
            "priority", "UNRESOLVED", [], [], "no explicit priority claim found"
        )
    expected_value = str(expected).upper() if isinstance(expected, str) else ""
    conflicts = [claim for claim in claims if claim != expected_value]
    if conflicts or len(claims) > 1:
        return _consistency_result(
            "priority",
            "CONFLICT",
            claims,
            conflicts or claims[1:],
            f"explicit priority claim does not match authoritative value {expected!r}",
        )
    return _consistency_result(
        "priority", "PASS", claims, [], "explicit priority claim matches authoritative value"
    )


def _sla_consistency(text: str, expected: Any) -> dict[str, Any]:
    separator = r"(?:\s+|-)"
    patterns = (
        (rf"\b(?:within{separator})?(?:4|four){separator}hours?\b", "4 hours"),
        (
            rf"\b(?:within{separator})?(?:1|one){separator}business{separator}day\b",
            "1 business day",
        ),
        (rf"\b(?:within{separator})?24{separator}hours?\b", "24 hours"),
    )
    claims = []
    for pattern, normalized in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            claims.append(normalized)
    if not claims:
        return _consistency_result("sla", "UNRESOLVED", [], [], "no supported SLA claim found")
    expected_value = str(expected).strip().lower() if isinstance(expected, str) else ""
    conflicts = [claim for claim in claims if claim.lower() != expected_value]
    if conflicts or len(claims) > 1:
        return _consistency_result(
            "sla",
            "CONFLICT",
            claims,
            conflicts or claims[1:],
            f"explicit SLA claim does not match authoritative value {expected!r}",
        )
    return _consistency_result(
        "sla", "PASS", claims, [], "explicit SLA claim matches authoritative value"
    )


def _policy_owner_teams(policy: Any) -> list[str]:
    teams: list[str] = []
    if isinstance(policy, Mapping):
        for key, value in policy.items():
            if key == "owner_team" and isinstance(value, str) and value not in teams:
                teams.append(value)
            teams.extend(team for team in _policy_owner_teams(value) if team not in teams)
    elif isinstance(policy, (list, tuple)):
        for value in policy:
            teams.extend(team for team in _policy_owner_teams(value) if team not in teams)
    return teams


def _owner_team_consistency(
    text: str,
    expected: Any,
    known_teams: list[str],
) -> dict[str, Any]:
    claims: list[str] = []
    for team in sorted(set(known_teams), key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(team)}(?!\w)", text, re.IGNORECASE):
            claims.append(team)
    if not claims:
        return _consistency_result(
            "owner_team", "UNRESOLVED", [], [], "no known owner team claim found"
        )
    expected_value = str(expected).casefold() if isinstance(expected, str) else ""
    conflicts = [team for team in claims if team.casefold() != expected_value]
    if conflicts or len(claims) > 1:
        return _consistency_result(
            "owner_team",
            "CONFLICT",
            claims,
            conflicts or claims[1:],
            f"explicit owner team claim does not match authoritative value {expected!r}",
        )
    return _consistency_result(
        "owner_team", "PASS", claims, [], "explicit owner team claim matches authoritative value"
    )


def _aggregate_consistency(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    statuses = [result["status"] for result in results.values()]
    if "CONFLICT" in statuses:
        overall = "CONFLICT"
    elif "PASS" in statuses:
        overall = "PASS"
    else:
        overall = "UNRESOLVED"
    return {**results, "overall": overall}


def _matches_contract_type(value: Any, type_name: Any) -> bool:
    normalized = str(type_name or "any").lower()
    if normalized in {"any", "json"}:
        return True
    if normalized in {"string", "str"}:
        return isinstance(value, str)
    if normalized in {"integer", "int"}:
        return isinstance(value, int) and not isinstance(value, bool)
    if normalized in {"number", "float"}:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if normalized in {"boolean", "bool"}:
        return isinstance(value, bool)
    if normalized in {"object", "mapping", "dict"}:
        return isinstance(value, Mapping)
    if normalized in {"array", "list"}:
        return isinstance(value, list)
    return False


def _deterministic_fallback(snapshot: AuthoritativeSnapshot) -> str:
    fields = snapshot.fields
    return (
        f"Your request has been assigned to {fields.get('owner_team')}. "
        f"Priority: {fields.get('priority')}. "
        f"Expected response time: {fields.get('sla')}."
    )


class _UnavailableNodeHandler:
    def __init__(self, node_type: str):
        self.node_type = node_type

    def execute(self, context: dict[str, Any], config: dict[str, Any]) -> Any:
        raise UnknownNodeTypeError(f"unknown node type: {self.node_type}")


class WorkflowRuntime:
    """Execute the nodes and order declared by a Workflow JSON config."""

    def __init__(self, workflow_config: dict[str, Any], registry: NodeRegistry):
        self.workflow_config = upgrade_workflow_config(workflow_config)
        self.registry = registry
        self.nodes = self._build_nodes()
        self._nodes_by_id = {node.node_id: node for node in self.nodes}

    def _build_nodes(self) -> list[WorkflowNode]:
        raw_nodes = self.workflow_config.get("nodes", [])
        if not isinstance(raw_nodes, list):
            raise WorkflowValidationError("nodes must be a list")

        nodes: list[WorkflowNode] = []
        for raw in raw_nodes:
            if not isinstance(raw, dict) or not raw.get("id"):
                raise WorkflowValidationError("each node must have a non-empty id")
            node_type = str(raw.get("type") or raw["id"])
            try:
                handler = self.registry.get(node_type)
            except UnknownNodeTypeError:
                handler = _UnavailableNodeHandler(node_type)
            nodes.append(
                WorkflowNode(
                    node_id=str(raw["id"]),
                    node_type=node_type,
                    name=str(raw.get("name") or raw["id"]),
                    inputs=dict(raw.get("inputs") or {}),
                    outputs=dict(raw.get("outputs") or {}),
                    required_inputs=tuple(raw.get("required_inputs") or (raw.get("inputs") or {}).keys()),
                    config=dict(raw.get("config") or {}),
                    handler=handler,
                    mode=str(raw.get("mode", "deterministic")),
                )
            )
        return nodes

    @property
    def execution_order(self) -> list[str]:
        execution = self.workflow_config.get("execution") or {}
        return list(execution.get("order") or [])

    def ordered_nodes(self) -> list[WorkflowNode]:
        return [self._nodes_by_id[node_id] for node_id in self.execution_order]

    def validate(self, initial_context: dict[str, Any] | None = None) -> None:
        errors: list[str] = validate_output_contract(self.workflow_config)
        node_ids = [node.node_id for node in self.nodes]
        duplicates = sorted({node_id for node_id in node_ids if node_ids.count(node_id) > 1})
        if duplicates:
            errors.append("duplicate node ids: " + ", ".join(duplicates))

        order = self.execution_order
        if not order:
            errors.append("execution.order must contain at least one node")
        order_duplicates = sorted({node_id for node_id in order if order.count(node_id) > 1})
        if order_duplicates:
            errors.append("duplicate execution.order node ids: " + ", ".join(order_duplicates))

        known_ids = set(node_ids)
        for node_id in order:
            if node_id not in known_ids:
                errors.append(f"missing node definition for execution.order entry: {node_id}")
        for node_id in node_ids:
            if node_id not in order:
                errors.append(f"node is missing from execution.order: {node_id}")

        for node in self.nodes:
            if not self.registry.contains(node.node_type):
                errors.append(f"unknown node type: {node.node_type}")
            for input_name in node.required_inputs:
                if input_name not in node.inputs:
                    errors.append(f"missing required input: {node.node_id}.{input_name}")

        initial_paths = {f"context.{key}" for key in (initial_context or {})}
        if int(self.workflow_config.get("schema_version", 1)) == 2:
            initial_paths.add("context.authoritative_snapshot")
        available_paths = set(initial_paths)
        produced_by: dict[str, str] = {}
        for node in self.nodes:
            for target in node.outputs.values():
                if not isinstance(target, str) or not target.startswith("context.") or target == "context.":
                    errors.append(f"invalid output binding in {node.node_id}: {target!r}")
                    continue
                previous = produced_by.get(target)
                if previous and previous != node.node_id:
                    errors.append(
                        f"output binding conflict: {target} is produced by {previous} and {node.node_id}"
                    )
                produced_by[target] = node.node_id

        if not errors:
            for node in self.ordered_nodes():
                for input_name, source in node.inputs.items():
                    if not isinstance(source, str) or not source.startswith("context."):
                        continue
                    if source in available_paths:
                        continue
                    producer = produced_by.get(source)
                    if producer and producer != node.node_id:
                        errors.append(
                            f"dependency violation: {node.node_id}.{input_name} requires {source} "
                            f"from later node {producer}"
                        )
                    else:
                        errors.append(f"missing required input: {node.node_id}.{input_name} -> {source}")
                available_paths.update(node.outputs.values())

        if errors:
            raise WorkflowValidationError("; ".join(errors), errors)

    def run(self, initial_context: dict[str, Any]) -> WorkflowRun:
        context = dict(initial_context)
        context.setdefault("executed_agents", [])
        context.setdefault("executed_tools", [])
        if self._is_v2:
            context.setdefault("field_evidence", [])
            context.setdefault("raw_candidates", {})
            context.setdefault("write_sets", {})
            context.setdefault("grounding_projections", {})
            context.setdefault("consistency_results", {})
            context.setdefault("fallback_used", False)
            context.setdefault("raw_responses", {})
        self.validate(context)

        trace: list[TraceStep] = []
        ordered_nodes = self.ordered_nodes()
        for index, node in enumerate(ordered_nodes):
            started_at = _timestamp()
            started = perf_counter()
            inputs: dict[str, Any] = {}
            try:
                if self._is_v2 and node.mode == "generative":
                    self._ensure_authoritative_snapshot(context)
                inputs = node.resolve_inputs(context)
                execution_context = context
                if self._is_v2 and node.mode == "generative":
                    inputs = self._detach_generative_inputs(node, inputs, context)
                    execution_context = {}
                result = node.execute(execution_context, inputs)
                if self._is_v2:
                    self._commit_node_outputs(node, result, context)
                else:
                    self._write_outputs(node, result.outputs, context)
                context["executed_agents"].append(node.node_id)
                finished_at = _timestamp()
                trace.append(
                    self._trace(
                        node,
                        status="SUCCESS",
                        started_at=started_at,
                        finished_at=finished_at,
                        duration_ms=_duration_ms(started),
                        inputs=_trace_inputs(node, inputs, context),
                        outputs=result.outputs,
                        detail=result.detail or f"{node.node_type} executed",
                        data=result.data or result.outputs,
                    )
                )
                if result.halt:
                    remaining = ordered_nodes[index + 1 :]
                    context["workflow_halted"] = True
                    context["halt_reason"] = result.halt_reason or "node requested halt"
                    context["skipped_agents"] = [item.node_id for item in remaining]
                    break
            except Exception as exc:
                finished_at = _timestamp()
                error = str(exc)
                trace.append(
                    self._trace(
                        node,
                        status="FAILED",
                        started_at=started_at,
                        finished_at=finished_at,
                        duration_ms=_duration_ms(started),
                        inputs=_trace_inputs(node, inputs, context),
                        outputs={},
                        detail=f"{node.node_type} failed",
                        data={},
                        error=error,
                    )
                )
                context["workflow_error"] = error
                context["failed_node"] = node.node_id
                for skipped in ordered_nodes[index + 1 :]:
                    now = _timestamp()
                    trace.append(
                        self._trace(
                            skipped,
                            status="SKIPPED",
                            started_at=now,
                            finished_at=now,
                            duration_ms=0.0,
                            inputs={},
                            outputs={},
                            detail=f"skipped after failure in {node.node_id}",
                            data={},
                        )
                    )
                return WorkflowRun(context=context, trace=trace, failed_node=node.node_id, error=error)

        return WorkflowRun(context=context, trace=trace)

    @property
    def _is_v2(self) -> bool:
        return int(self.workflow_config.get("schema_version", 1)) == 2

    def _ensure_authoritative_snapshot(self, context: dict[str, Any]) -> AuthoritativeSnapshot:
        snapshot = context.get("authoritative_snapshot")
        if isinstance(snapshot, AuthoritativeSnapshot):
            return snapshot
        contract = output_contract_from_workflow(self.workflow_config)
        if contract is None:
            raise WorkflowValidationError("schema v2 requires an output contract")
        fields = {
            field.name: _resolve_context_path(field.binding, context)
            for field in contract.fields.values()
            if field.authority == "authoritative"
        }
        snapshot = create_authoritative_snapshot(fields)
        context["authoritative_snapshot"] = snapshot
        context["authoritative_snapshot_hash"] = snapshot.sha256
        return snapshot

    def _detach_generative_inputs(
        self,
        node: WorkflowNode,
        inputs: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        contract = output_contract_from_workflow(self.workflow_config)
        if contract is None:
            raise WorkflowValidationError("schema v2 requires an output contract")
        snapshot = context.get("authoritative_snapshot")
        grounding_fields: list[str] = []
        for field in contract.fields.values():
            if field.producer != node.node_id or field.authority != "generative":
                continue
            for name in field.grounded_on:
                if name not in grounding_fields:
                    grounding_fields.append(name)

        detached: dict[str, Any] = {}
        request_context: dict[str, Any] = {}
        prompt_policy_context = context.get("prompt_policy_context")
        for name, value in inputs.items():
            if isinstance(value, AuthoritativeSnapshot):
                continue
            detached[name] = _thaw(value)
            if name == "support_policy" and isinstance(prompt_policy_context, Mapping):
                continue
            request_context[name] = _thaw(value)

        if isinstance(prompt_policy_context, Mapping):
            request_context["support_policy"] = _thaw(prompt_policy_context)

        if isinstance(snapshot, AuthoritativeSnapshot):
            projection = _create_grounding_projection(
                snapshot,
                grounding_fields,
                request_context,
            )
            context["grounding_projections"][node.node_id] = _freeze(deepcopy(projection))
            for name, value in inputs.items():
                if isinstance(value, AuthoritativeSnapshot):
                    detached[name] = deepcopy(projection)
        return detached

    def _commit_node_outputs(
        self,
        node: WorkflowNode,
        result: NodeExecutionResult,
        context: dict[str, Any],
    ) -> None:
        contract = output_contract_from_workflow(self.workflow_config)
        if contract is None:
            raise WorkflowValidationError("schema v2 requires an output contract")
        fields_by_binding = {field.binding: field for field in contract.fields.values()}
        declared: list[str] = []
        for target in node.outputs.values():
            field = fields_by_binding.get(target)
            declared.append(field.name if field else target)

        if node.mode == "generative":
            raw_candidate = deepcopy(result.raw_candidate if result.raw_candidate is not None else result.outputs)
            if result.raw_response is not None:
                raw_response = str(result.raw_response)
                raw_record = deepcopy(result.metadata or {})
                raw_record.update(
                    {
                        "provider": result.provider or raw_record.get("provider", "unavailable"),
                        "model": result.model or raw_record.get("model", "unavailable"),
                        "raw_response": raw_response,
                        "parse_status": result.parse_status,
                        "raw_response_hash": hashlib.sha256(raw_response.encode("utf-8")).hexdigest(),
                    }
                )
                raw_record.setdefault("timestamp", _timestamp())
                raw_record.setdefault("request_hash", "unavailable")
                raw_record.setdefault("prompt_version", "unavailable")
                raw_record.setdefault("grounding_hash", "")
                raw_record.setdefault("fixture_version", "unavailable")
                raw_record.setdefault("runtime_version", "unavailable")
                raw_record.setdefault("schema_version", self.workflow_config.get("schema_version", 2))
                raw_record.setdefault("sampling_parameters", "unavailable")
                raw_record.setdefault("exact_backend_revision", "unavailable")
                context["raw_responses"][node.node_id] = _freeze(raw_record)
            context["raw_candidates"][node.node_id] = _freeze(raw_candidate)
            if not isinstance(context.get("authoritative_snapshot"), AuthoritativeSnapshot):
                raise WorkflowValidationError("generative candidate requires an authoritative snapshot")
            requests = [
                (str(name), value, contract.fields.get(str(name)))
                for name, value in raw_candidate.items()
            ] if isinstance(raw_candidate, Mapping) else []
            self._commit_generative_candidate(
                node,
                raw_candidate,
                requests,
                declared,
                contract,
                context,
                result.parse_status,
            )
            return
        else:
            requests = []
            for output_name, target in node.outputs.items():
                if output_name not in result.outputs:
                    raise KeyError(f"node {node.node_id} did not return declared output: {output_name}")
                requests.append(
                    (
                        fields_by_binding.get(target).name if target in fields_by_binding else target,
                        result.outputs[output_name],
                        fields_by_binding.get(target),
                    )
                )

        allowed = []
        reasons: dict[str, str] = {}
        targets: dict[str, str] = {}
        for field_name, _value, field in requests:
            target = field.binding if field else ""
            targets[field_name] = target
            if field is None and node.mode == "deterministic" and target == "":
                target = field_name if field_name.startswith("context.") else ""
                targets[field_name] = target
            if field is None:
                if node.mode == "deterministic" and field_name.startswith("context."):
                    allowed.append(field_name)
                    continue
                reasons[field_name] = "unknown field"
                continue
            if field.producer != node.node_id:
                reasons[field_name] = (
                    f"{field.authority} field cannot be written by {node.node_id!r}; "
                    f"declared producer is {field.producer!r}"
                )
                continue
            expected_authority = "generative" if node.mode == "generative" else "authoritative"
            if field.authority != expected_authority:
                reasons[field_name] = (
                    f"{node.mode} node cannot write {field.authority} field"
                )
                continue
            allowed.append(field_name)

        context["write_sets"][node.node_id] = {
            "declared": sorted(set(declared)),
            "requested": sorted(field_name for field_name, _value, _field in requests),
            "allowed": sorted(set(allowed)),
        }
        unauthorized = [
            field_name
            for field_name, _value, _field in requests
            if field_name not in allowed
        ]
        atomic_reason = "candidate rejected atomically because another field is unauthorized"
        if unauthorized:
            for field_name, value, field in requests:
                reason = reasons.get(field_name, atomic_reason)
                self._record_field_evidence(
                    context,
                    field_name,
                    field,
                    node.node_id,
                    value,
                    accepted=False,
                    target=targets.get(field_name, ""),
                    reason=reason,
                )
            return

        for field_name, value, field in requests:
            target = targets.get(field_name, "")
            if target:
                write_binding(target, value, context)
            if field is not None:
                self._record_field_evidence(
                    context,
                    field_name,
                    field,
                    node.node_id,
                    value,
                    accepted=True,
                    target=target,
                    reason="authorized producer",
                )

    def _commit_generative_candidate(
        self,
        node: WorkflowNode,
        raw_candidate: Any,
        requests: list[tuple[str, Any, Any]],
        declared: list[str],
        contract: Any,
        context: dict[str, Any],
        parse_status: str,
    ) -> None:
        allowed: list[str] = []
        reasons: dict[str, str] = {}
        targets: dict[str, str] = {}
        for field_name, _value, field in requests:
            target = field.binding if field else ""
            targets[field_name] = target
            if field is None:
                reasons[field_name] = "unknown field"
                continue
            if field.producer != node.node_id:
                reasons[field_name] = (
                    f"{field.authority} field cannot be written by {node.node_id!r}; "
                    f"declared producer is {field.producer!r}"
                )
                continue
            if field.authority != "generative":
                reasons[field_name] = f"generative node cannot write {field.authority} field"
                continue
            allowed.append(field_name)

        context["write_sets"][node.node_id] = {
            "declared": sorted(set(declared)),
            "requested": sorted(field_name for field_name, _value, _field in requests),
            "allowed": sorted(set(allowed)),
        }

        missing = [
            field.name
            for field in contract.fields.values()
            if field.producer == node.node_id
            and field.authority == "generative"
            and field.required
            and (not isinstance(raw_candidate, Mapping) or field.name not in raw_candidate)
        ]
        for field_name in missing:
            reasons[field_name] = "missing required field"
            targets[field_name] = contract.fields[field_name].binding

        invalid_types = [
            field_name
            for field_name, value, field in requests
            if field is not None
            and field_name in allowed
            and not _matches_contract_type(value, field.type)
        ]
        for field_name in invalid_types:
            reasons[field_name] = "invalid type"

        parse_rejected = parse_status != "PARSE_OK"
        if parse_rejected and "customer_message" not in reasons:
            reasons["customer_message"] = f"parse status {parse_status}"

        snapshot = context.get("authoritative_snapshot")
        if not isinstance(snapshot, AuthoritativeSnapshot):
            raise WorkflowValidationError("consistency validation requires an authoritative snapshot")
        message = raw_candidate.get("customer_message") if isinstance(raw_candidate, Mapping) else None
        consistency = _aggregate_consistency(
            {
                "priority": _priority_consistency(
                    message if isinstance(message, str) else "",
                    snapshot.fields.get("priority"),
                ),
                "sla": _sla_consistency(
                    message if isinstance(message, str) else "",
                    snapshot.fields.get("sla"),
                ),
                "owner_team": _owner_team_consistency(
                    message if isinstance(message, str) else "",
                    snapshot.fields.get("owner_team"),
                    _policy_owner_teams(context.get("support_policy")),
                ),
            }
        )
        context["consistency_results"][node.node_id] = consistency
        rejected = bool(
            not isinstance(raw_candidate, Mapping)
            or len(allowed) != len(requests)
            or missing
            or invalid_types
            or parse_rejected
            or consistency.get("overall") == "CONFLICT"
        )
        grounding_fields, grounding_hash = self._grounding_metadata(node, contract, context)
        fallback = False
        if rejected and self._fallback_is_available(contract, node.node_id):
            snapshot = context.get("authoritative_snapshot")
            if not isinstance(snapshot, AuthoritativeSnapshot):
                raise WorkflowValidationError("fallback requires an authoritative snapshot")
            write_binding(
                contract.fields["customer_message"].binding,
                _deterministic_fallback(snapshot),
                context,
            )
            context["fallback_used"] = True
            context["fallback_reason"] = self._candidate_rejection_reason(
                reasons, consistency.get("overall") == "CONFLICT"
            )
            fallback = True

        if rejected:
            for field_name, value, field in requests:
                self._record_field_evidence(
                    context,
                    field_name,
                    field,
                    node.node_id,
                    value,
                    accepted=False,
                    target=targets.get(field_name, ""),
                    reason=reasons.get(field_name, "candidate rejected atomically"),
                    grounding_fields=grounding_fields,
                    grounding_hash=grounding_hash,
                    consistency_results=consistency,
                    fallback_used=fallback,
                    parse_status=parse_status,
                )
            for field_name in missing:
                self._record_field_evidence(
                    context,
                    field_name,
                    contract.fields[field_name],
                    node.node_id,
                    None,
                    accepted=False,
                    target=targets[field_name],
                    reason="missing required field",
                    grounding_fields=grounding_fields,
                    grounding_hash=grounding_hash,
                    consistency_results=consistency,
                    fallback_used=fallback,
                    parse_status=parse_status,
                )
            return

        for field_name, value, field in requests:
            write_binding(targets[field_name], value, context)
            self._record_field_evidence(
                context,
                field_name,
                field,
                node.node_id,
                value,
                accepted=True,
                target=targets[field_name],
                reason="authorized producer",
                grounding_fields=grounding_fields,
                grounding_hash=grounding_hash,
                consistency_results=consistency,
                fallback_used=False,
                parse_status=parse_status,
            )

    @staticmethod
    def _fallback_is_available(contract: Any, node_id: str) -> bool:
        message = contract.fields.get("customer_message")
        return bool(
            message
            and message.producer == node_id
            and message.authority == "generative"
            and message.required
        )

    @staticmethod
    def _candidate_rejection_reason(
        reasons: dict[str, str], consistency_conflict: bool
    ) -> str:
        if consistency_conflict:
            return "consistency conflict"
        return next(iter(reasons.values()), "candidate rejected")

    @staticmethod
    def _grounding_metadata(
        node: WorkflowNode,
        contract: Any,
        context: dict[str, Any],
    ) -> tuple[list[str], str]:
        grounding_fields: list[str] = []
        for field in contract.fields.values():
            if field.producer != node.node_id or field.authority != "generative":
                continue
            for name in field.grounded_on:
                if name not in grounding_fields:
                    grounding_fields.append(name)
        projection = context.get("grounding_projections", {}).get(node.node_id, {})
        return grounding_fields, str(projection.get("sha256", ""))

    @staticmethod
    def _record_field_evidence(
        context: dict[str, Any],
        field_name: str,
        field: Any,
        writer: str,
        value: Any,
        *,
        accepted: bool,
        target: str,
        reason: str,
        grounding_fields: list[str] | None = None,
        grounding_hash: str = "",
        consistency_results: dict[str, Any] | None = None,
        fallback_used: bool = False,
        parse_status: str = "PARSE_OK",
    ) -> None:
        final_value = _resolve_context_path(target, context) if accepted and target else None
        context["field_evidence"].append(
            {
                "field": field_name,
                "authority": field.authority if field is not None else "unknown",
                "declared_producer": field.producer if field is not None else "",
                "attempted_writer": writer,
                "attempted_value": _safe_value(deepcopy(value)),
                "accepted": accepted,
                "final_value": _safe_value(final_value),
                "write_status": "accepted" if accepted else "rejected",
                "reason": reason,
                "grounding_fields": list(grounding_fields or []),
                "grounding_hash": grounding_hash,
                "consistency_results": _safe_value(consistency_results or {}),
                "fallback_used": fallback_used,
                "parse_status": parse_status,
            }
        )

    def _write_outputs(
        self,
        node: WorkflowNode,
        outputs: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        for output_name, target in node.outputs.items():
            if output_name not in outputs:
                raise KeyError(f"node {node.node_id} did not return declared output: {output_name}")
            write_binding(target, outputs[output_name], context)

    def _trace(
        self,
        node: WorkflowNode,
        *,
        status: str,
        started_at: str,
        finished_at: str,
        duration_ms: float,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        detail: str,
        data: dict[str, Any],
        error: str | None = None,
    ) -> TraceStep:
        return TraceStep(
            name=node.name,
            detail=detail,
            data=_safe_value(data),
            node_id=node.node_id,
            node_type=node.node_type,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            input=_safe_value(inputs),
            output=_safe_value(outputs),
            error=error,
        )


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _duration_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 3)


def _safe_value(value: Any) -> Any:
    if is_dataclass(value):
        return _safe_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_safe_value(item) for item in value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _trace_inputs(
    node: WorkflowNode,
    inputs: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    if node.mode != "generative":
        return inputs
    projection = context.get("grounding_projections", {}).get(node.node_id)
    if not isinstance(projection, Mapping):
        return inputs
    projection_hash = projection.get("sha256")
    grounding_fields = list((projection.get("authoritative_facts") or {}).keys())
    redacted: dict[str, Any] = {}
    for name, value in inputs.items():
        if isinstance(value, Mapping) and value.get("sha256") == projection_hash:
            redacted[name] = {
                "grounding_fields": grounding_fields,
                "grounding_hash": projection_hash,
            }
        else:
            redacted[name] = value
    return redacted


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return deepcopy(value)


def _create_grounding_projection(
    snapshot: AuthoritativeSnapshot,
    grounding_fields: list[str],
    request_context: dict[str, Any],
) -> dict[str, Any]:
    authoritative_facts = {
        name: _thaw(snapshot.fields[name])
        for name in grounding_fields
        if name in snapshot.fields
    }
    canonical_json = json.dumps(
        authoritative_facts,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return {
        "request_context": deepcopy(request_context),
        "authoritative_facts": authoritative_facts,
        # Keep the Stage 1 shape as a detached compatibility alias.
        "fields": authoritative_facts,
        "canonical_json": canonical_json,
        "sha256": hashlib.sha256(canonical_json.encode("utf-8")).hexdigest(),
    }


def _resolve_context_path(binding: str, context: dict[str, Any]) -> Any:
    if not isinstance(binding, str) or not binding.startswith("context."):
        raise KeyError(f"invalid context binding: {binding!r}")
    current: Any = context
    path = binding[len("context.") :]
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise KeyError(f"missing context value: {binding}")
        current = current[part]
    return current

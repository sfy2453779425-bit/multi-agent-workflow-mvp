"""Compatibility conversion from the original template metadata to executable nodes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


FIELD_AUTHORITIES = {"authoritative", "generative"}
FIELD_CONTRACT_KEYS = {
    "name",
    "binding",
    "type",
    "required",
    "authority",
    "producer",
    "grounded_on",
}


@dataclass(frozen=True)
class FieldContract:
    """The small, explicit ownership contract for one canonical field."""

    name: str
    binding: str
    type: str
    required: bool
    authority: str
    producer: str
    grounded_on: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, name: str, value: Any) -> "FieldContract":
        if not isinstance(value, dict):
            raise ValueError("field contract must be an object")
        missing = [
            key
            for key in ("binding", "type", "required", "authority", "producer")
            if key not in value
        ]
        if missing:
            raise ValueError("missing " + ", ".join(missing))
        unknown = sorted(set(value) - FIELD_CONTRACT_KEYS)
        if unknown:
            raise ValueError("unsupported keys: " + ", ".join(unknown))
        grounded_on = value.get("grounded_on", ())
        if grounded_on is None:
            grounded_on = ()
        if not isinstance(grounded_on, (list, tuple)) or not all(
            isinstance(item, str) and item for item in grounded_on
        ):
            raise ValueError("grounded_on must be a list of field names")
        field_name = str(value.get("name") or name)
        if not field_name:
            raise ValueError("name must be non-empty")
        return cls(
            name=field_name,
            binding=str(value["binding"]),
            type=str(value["type"]),
            required=bool(value["required"]),
            authority=str(value["authority"]),
            producer=str(value["producer"]),
            grounded_on=tuple(grounded_on),
        )


@dataclass(frozen=True)
class ConsistencyRule:
    """Placeholder for later consistency checks; no rule is evaluated in P0."""

    name: str
    fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class OutputContract:
    fields: dict[str, FieldContract]
    consistency_rules: tuple[ConsistencyRule, ...] = ()

    @classmethod
    def from_mapping(cls, value: Any) -> "OutputContract":
        if not isinstance(value, dict):
            raise ValueError("output_contract must be an object")
        raw_fields = value.get("fields")
        if not isinstance(raw_fields, dict) or not raw_fields:
            raise ValueError("fields must be a non-empty object")
        fields = {
            str(name): FieldContract.from_mapping(str(name), field_value)
            for name, field_value in raw_fields.items()
        }
        raw_rules = value.get("consistency_rules", ())
        if raw_rules is None:
            raw_rules = ()
        if not isinstance(raw_rules, (list, tuple)):
            raise ValueError("consistency_rules must be a list")
        rules = tuple(
            ConsistencyRule(
                name=str(rule.get("name", "")),
                fields=tuple(rule.get("fields", ())),
            )
            for rule in raw_rules
            if isinstance(rule, dict)
        )
        return cls(fields=fields, consistency_rules=rules)


def _node_mode(raw_node: dict[str, Any]) -> str:
    return str(raw_node.get("mode", "deterministic"))


def validate_output_contract(config: dict[str, Any]) -> list[str]:
    """Return actionable static errors for a schema-v2 ownership contract."""

    if int(config.get("schema_version", 1)) != 2:
        return []

    errors: list[str] = []
    if config.get("workflow_mode") != "authoritative_contract":
        errors.append("workflow_mode: v2 requires authoritative_contract")
    if "output_contract" not in config:
        return errors + ["output_contract: v2 requires output_contract"]

    raw_contract = config["output_contract"]
    if not isinstance(raw_contract, dict):
        return errors + ["output_contract: output_contract must be an object"]
    raw_fields = raw_contract.get("fields")
    if not isinstance(raw_fields, dict) or not raw_fields:
        return errors + ["output_contract: fields must be a non-empty object"]
    parsed_fields: dict[str, FieldContract] = {}
    for name, raw_field in raw_fields.items():
        field_name = str(name)
        producer = raw_field.get("producer", "<missing>") if isinstance(raw_field, dict) else "<invalid>"
        try:
            parsed_fields[field_name] = FieldContract.from_mapping(field_name, raw_field)
        except ValueError as exc:
            errors.append(
                f"output_contract.fields.{field_name} (node={producer}): {exc}"
            )
    if not parsed_fields:
        return errors
    contract = OutputContract(fields=parsed_fields)

    raw_nodes = config.get("nodes", config.get("agents", []))
    nodes = {
        str(node.get("id")): node
        for node in raw_nodes
        if isinstance(node, dict) and node.get("id")
    }
    modes = {node_id: _node_mode(node) for node_id, node in nodes.items()}
    execution_order = list((config.get("execution") or {}).get("order") or [])
    order_index = {str(node_id): index for index, node_id in enumerate(execution_order)}

    bindings: dict[str, FieldContract] = {}
    for field in contract.fields.values():
        path = f"output_contract.fields.{field.name}"
        node_id = field.producer or "<missing>"
        if field.authority not in FIELD_AUTHORITIES:
            errors.append(f"{path} (node={node_id}): invalid authority {field.authority!r}")
        if not field.binding.startswith("context.") or field.binding == "context.":
            errors.append(f"{path} (node={node_id}): invalid binding {field.binding!r}")
        if field.producer not in nodes:
            errors.append(f"{path} (node={node_id}): producer node does not exist")
        elif field.authority == "authoritative" and modes[field.producer] == "generative":
            errors.append(
                f"{path} (node={field.producer}): authoritative field cannot use generative producer"
            )
        elif field.authority == "generative" and modes[field.producer] != "generative":
            errors.append(
                f"{path} (node={field.producer}): generative field requires a generative producer"
            )
        elif field.binding not in (nodes[field.producer].get("outputs") or {}).values():
            errors.append(
                f"{path} (node={field.producer}): field binding is not declared by producer node"
            )

        previous = bindings.get(field.binding)
        if previous is not None and previous.name != field.name:
            errors.append(
                f"{path} (node={node_id}): duplicate canonical binding {field.binding!r} "
                f"already owned by {previous.name}"
            )
        else:
            bindings[field.binding] = field

    fields = list(contract.fields.values())
    for index, left in enumerate(fields):
        for right in fields[index + 1 :]:
            if left.binding == right.binding:
                continue
            parent, child = sorted((left.binding, right.binding), key=len)
            if child.startswith(parent + ".") and (
                left.authority != right.authority or left.producer != right.producer
            ):
                errors.append(
                    f"output_contract.fields.{child[len('context.') :]} "
                    f"(node={right.producer}): parent/child ownership conflict with "
                    f"{left.name}"
                )

    for node_id, node in nodes.items():
        if modes[node_id] != "generative":
            continue
        for target in (node.get("outputs") or {}).values():
            for field in contract.fields.values():
                if target == field.binding and field.authority == "authoritative":
                    errors.append(
                        f"output_contract.fields.{field.name} (node={node_id}): "
                        "generative node cannot directly bind authoritative final field"
                    )
    for field in fields:
        for grounded in field.grounded_on:
            referenced = contract.fields.get(grounded)
            if referenced is None:
                errors.append(
                    f"output_contract.fields.{field.name} (node={field.producer}): "
                    f"grounded_on references missing field {grounded!r}"
                )
            elif referenced.authority != "authoritative":
                errors.append(
                    f"output_contract.fields.{field.name} (node={field.producer}): "
                    f"grounded_on field {grounded!r} is generative"
                )
            elif (
                field.producer in order_index
                and referenced.producer in order_index
                and order_index[referenced.producer] >= order_index[field.producer]
            ):
                errors.append(
                    f"output_contract.fields.{field.name} (node={field.producer}): "
                    f"grounding producer {referenced.producer!r} must precede producer "
                    f"in execution order"
                )
    return errors


def output_contract_from_workflow(config: dict[str, Any]) -> OutputContract | None:
    if int(config.get("schema_version", 1)) != 2:
        return None
    return OutputContract.from_mapping(config["output_contract"])


def _contract(
    node_type: str,
    inputs: dict[str, str],
    outputs: dict[str, str],
) -> dict[str, Any]:
    return {
        "type": node_type,
        "inputs": inputs,
        "outputs": outputs,
        "required_inputs": list(inputs),
    }


NODE_CONTRACTS: dict[str, dict[str, dict[str, Any]]] = {
    "outfit_recommendation": {
        "request_parser": _contract(
            "request_parser",
            {"user_message": "context.query", "user_id": "context.user_id"},
            {
                "agent_name": "context.agent_name",
                "city_display": "context.city_display",
                "city_query": "context.city_query",
                "day_offset": "context.day_offset",
                "date_label": "context.date_label",
                "matched_keywords": "context.matched_keywords",
            },
        ),
        "question": _contract(
            "question",
            {"query": "context.query", "city": "context.city_display", "date": "context.date_label"},
            {
                "detected_purpose": "context.detected_purpose",
                "detected_style": "context.detected_style",
                "missing_fields": "context.missing_fields",
                "next_question_field": "context.next_question_field",
                "needs_clarification": "context.needs_clarification",
                "clarification_message": "context.clarification_message",
            },
        ),
        "weather": _contract(
            "weather",
            {"city_query": "context.city_query", "day_offset": "context.day_offset"},
            {"weather": "context.weather", "weather_summary": "context.weather_summary"},
        ),
        "shopping_analysis": _contract(
            "shopping_analysis",
            {"user_id": "context.user_id"},
            {
                "shopping_history": "context.shopping_history",
                "shopping_history_summary": "context.shopping_history_summary",
                "shopping_analysis": "context.shopping_analysis",
                "shopping_item_count": "context.shopping_item_count",
                "styles_text": "context.styles_text",
                "colors_text": "context.colors_text",
                "favorite_items_text": "context.favorite_items_text",
                "top_categories_text": "context.top_categories_text",
                "user_name": "context.user_name",
                "shopping_analysis_summary": "context.shopping_analysis_summary",
            },
        ),
        "recommendation": _contract(
            "recommendation",
            {"weather": "context.weather", "shopping_analysis": "context.shopping_analysis"},
            {
                "avg_temp": "context.avg_temp",
                "temp_min": "context.temp_min",
                "temp_max": "context.temp_max",
                "weather_date": "context.weather_date",
                "weather_condition": "context.weather_condition",
                "precipitation_probability": "context.precipitation_probability",
                "matched_rule_name": "context.matched_rule_name",
                "recommendation": "context.recommendation",
                "owned_recommended_items": "context.owned_recommended_items",
                "owned_recommended_items_text": "context.owned_recommended_items_text",
                "additional_items": "context.additional_items",
                "additional_items_text": "context.additional_items_text",
                "recommended_items": "context.recommended_items",
                "recommended_items_text": "context.recommended_items_text",
                "ranked_items": "context.ranked_items",
                "ranked_items_text": "context.ranked_items_text",
                "extras": "context.extras",
                "extras_text": "context.extras_text",
            },
        ),
        "compose": _contract(
            "compose",
            {"recommendation": "context.recommendation", "ranked_items": "context.ranked_items"},
            {"final_answer": "context.final_answer"},
        ),
    },
    "presentation_planning": {
        "request_parser": _contract(
            "presentation_request_parser",
            {"user_message": "context.query", "user_id": "context.user_id"},
            {
                "topic": "context.topic",
                "duration_minutes": "context.duration_minutes",
                "output_type": "context.output_type",
            },
        ),
        "question": _contract(
            "presentation_question",
            {"topic": "context.topic"},
            {
                "missing_fields": "context.missing_fields",
                "needs_clarification": "context.needs_clarification",
                "next_question_field": "context.next_question_field",
                "clarification_message": "context.clarification_message",
            },
        ),
        "topic_analysis": _contract(
            "topic_analysis",
            {"topic": "context.topic"},
            {"matched_topics": "context.matched_topics", "planning_goal": "context.planning_goal"},
        ),
        "knowledge_lookup": _contract(
            "knowledge_lookup",
            {"matched_topics": "context.matched_topics"},
            {"knowledge_points": "context.knowledge_points", "slide_suggestions": "context.slide_suggestions"},
        ),
        "outline_generation": _contract(
            "outline_generation",
            {
                "knowledge_points": "context.knowledge_points",
                "duration_minutes": "context.duration_minutes",
                "planning_goal": "context.planning_goal",
            },
            {
                "outline_sections": "context.outline_sections",
                "speaker_focus": "context.speaker_focus",
            },
        ),
        "compose": _contract(
            "presentation_compose",
            {
                "outline_sections": "context.outline_sections",
                "knowledge_points": "context.knowledge_points",
                "speaker_focus": "context.speaker_focus",
            },
            {"final_answer": "context.final_answer", "summary_cards": "context.summary_cards"},
        ),
    },
    "customer_support": {
        "request_parser": _contract(
            "support_request_parser",
            {"user_message": "context.query", "user_id": "context.user_id"},
            {"issue_text": "context.issue_text", "intent": "context.intent"},
        ),
        "question": _contract(
            "support_question",
            {"issue_text": "context.issue_text"},
            {
                "missing_fields": "context.missing_fields",
                "needs_clarification": "context.needs_clarification",
                "next_question_field": "context.next_question_field",
                "clarification_message": "context.clarification_message",
            },
        ),
        "ticket_classification": _contract(
            "ticket_classification",
            {"issue_text": "context.issue_text"},
            {
                "ticket_category_record": "context.ticket_category_record",
                "ticket_category": "context.ticket_category",
                "ticket_category_id": "context.ticket_category_id",
                "matched_keywords": "context.matched_keywords",
                "priority_candidate": "context.priority_candidate",
            },
        ),
        "policy_lookup": _contract(
            "policy_lookup",
            {"category": "context.ticket_category_record"},
            {
                "policy": "context.policy",
                "sla": "context.sla",
                "owner_team": "context.owner_team",
            },
        ),
        "routing_decision": _contract(
            "routing_decision",
            {"category": "context.ticket_category_record", "policy": "context.policy"},
            {
                "priority": "context.priority",
                "next_actions": "context.next_actions",
            },
        ),
        "compose": _contract(
            "support_compose",
            {
                "owner_team": "context.owner_team",
                "priority": "context.priority",
                "next_actions": "context.next_actions",
                "policy": "context.policy",
            },
            {"final_answer": "context.final_answer", "summary_cards": "context.summary_cards"},
        ),
    },
}


def _node_contract(runtime_type: str, node_id: str) -> dict[str, Any]:
    return deepcopy(NODE_CONTRACTS.get(runtime_type, {}).get(node_id, {}))


def _coerce_bindings(value: Any, defaults: dict[str, str]) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if value is None:
        return dict(defaults)
    if isinstance(value, list):
        if defaults:
            return dict(defaults)
        return {name: defaults.get(name, f"context.{name}") for name in value}
    raise ValueError("node inputs and outputs must be mappings or lists")


def executable_node(runtime_type: str, raw_node: dict[str, Any]) -> dict[str, Any]:
    """Return one normalized executable node while preserving old metadata."""

    node_id = str(raw_node["id"])
    contract = _node_contract(runtime_type, node_id)
    node_type = str(raw_node.get("type") or contract.get("type") or node_id)
    inputs = _coerce_bindings(raw_node.get("inputs"), contract.get("inputs", {}))
    outputs = _coerce_bindings(raw_node.get("outputs"), contract.get("outputs", {}))
    required_inputs = raw_node.get("required_inputs", contract.get("required_inputs", list(inputs)))
    normalized = {
        "id": node_id,
        "type": node_type,
        "name": raw_node.get("name", node_id),
        "role": raw_node.get("role", ""),
        "builder_equivalent": raw_node.get("builder_equivalent", ""),
        "inputs": inputs,
        "outputs": outputs,
        "required_inputs": list(required_inputs),
        "config": deepcopy(raw_node.get("config", {})),
    }
    if "mode" in raw_node:
        normalized["mode"] = raw_node["mode"]
    return normalized


def executable_nodes_from_template(template: dict[str, Any], node_ids: list[str]) -> list[dict[str, Any]]:
    by_id = {str(node["id"]): node for node in template.get("node_palette", [])}
    runtime_type = str(template.get("runtime_type", "outfit_recommendation"))
    return [executable_node(runtime_type, by_id[node_id]) for node_id in node_ids]


def upgrade_workflow_config(config: dict[str, Any]) -> dict[str, Any]:
    """Add executable nodes to old Workflow JSON without mutating the caller."""

    upgraded = deepcopy(config)
    source = upgraded.get("nodes") if "nodes" in upgraded else upgraded.get("agents", [])
    upgraded["nodes"] = [
        executable_node(str(upgraded.get("runtime_type", "outfit_recommendation")), node)
        for node in source
    ]
    upgraded.setdefault("schema_version", 1)
    return upgraded

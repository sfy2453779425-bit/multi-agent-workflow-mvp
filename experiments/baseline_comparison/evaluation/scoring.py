from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any


def _payload(fixture: Any) -> dict[str, Any]:
    return fixture.payload if hasattr(fixture, "payload") else fixture


def _lower(value: Any) -> str:
    return str(value).lower()


def derive_ground_truth(fixture: Any) -> dict[str, Any]:
    payload = _payload(fixture)
    if payload.get("domain") != "customer_support":
        return {}
    query = _lower(payload["input"]["query"])
    categories = payload["business_data"].get("categories", [])
    best_category = None
    best_matches: list[str] = []
    matches_by_id = {}
    for category in categories:
        matches = [
            str(keyword)
            for keyword in category.get("keywords", [])
            if _lower(keyword) in query
        ]
        matches_by_id[str(category.get("id", ""))] = matches

    precedence = payload.get("ground_truth", {}).get("category_precedence") or payload.get(
        "constraints", {}
    ).get("mixed_intent_precedence", [])
    if isinstance(precedence, list):
        for category_id in precedence:
            category = next(
                (item for item in categories if str(item.get("id")) == str(category_id)),
                None,
            )
            if category and matches_by_id.get(str(category_id)):
                best_category = category
                best_matches = matches_by_id[str(category_id)]
                break

    if best_category is None:
        for category in categories:
            matches = matches_by_id.get(str(category.get("id", "")), [])
            if len(matches) > len(best_matches):
                best_category = category
                best_matches = matches
    if best_category is None:
        default_id = payload["business_data"].get("default_category")
        best_category = next(
            (category for category in categories if category.get("id") == default_id),
            categories[0] if categories else {},
        )
    return {
        "category_id": best_category.get("id", ""),
        "label": best_category.get("label", ""),
        "owner_team": best_category.get("owner_team", ""),
        "priority": best_category.get("priority", ""),
        "sla": best_category.get("sla", ""),
        "policy": best_category.get("policy", ""),
        "next_actions": list(best_category.get("next_actions", [])),
        "matched_keywords": best_matches,
        "derivation": "frozen policy keyword match with first-category tie break",
    }


def _field_aliases(domain: str) -> dict[str, tuple[str, ...]]:
    if domain == "outfit":
        return {
            "weather": ("weather", "날씨", "天气"),
            "temperature": ("temperature", "temp", "기온", "온도", "°c"),
            "precipitation": ("precipitation", "rain", "강수", "비가", "비 예보", "우산"),
            "selected_items": ("selected_items", "보유 단품 기반 추천", "추천 아이템", "item"),
            "reason": ("reason", "추천 방향", "추천 이유", "추가 조건", "근거", "이유", "because"),
        }
    if domain == "presentation":
        return {
            "duration": ("duration", "15-minute", "15 minute", "15분", "15 분"),
            "outline_sections": ("outline", "opening", "problem", "architecture", "conclusion"),
            "evidence_points": ("evidence", "knowledge", "근거", "证据"),
        }
    return {
        "category": ("category", "delivery / shipping", "delivery", "배송"),
        "owner_team": ("owner", "route", "logistics support", "billing support", "support"),
        "priority": ("priority", "p1", "p2", "p3"),
        "sla": ("sla", "business day", "영업일"),
        "next_actions": ("next actions", "next steps", "조치", "actions"),
    }


def _required_fields(payload: dict[str, Any], text: str, parsed: dict[str, Any]) -> list[str]:
    aliases = _field_aliases(str(payload.get("domain", "")))
    required = payload.get("output_requirements", {}).get("required_fields", [])
    missing = []
    for field in required:
        if field == "selected_items":
            present = bool(parsed.get("selected_items"))
        elif field == "outline_sections":
            present = bool(parsed.get("outline_sections"))
        elif field in {"category", "owner_team", "priority", "sla"}:
            present = bool(parsed.get({"owner_team": "route"}.get(field, field)))
        else:
            present = any(alias.lower() in text for alias in aliases.get(field, (field,)))
        if not present:
            missing.append(field)
    return missing


# Keep ASCII identifier boundaries so an ID followed by Korean text (for
# example ``A006은``) is still recognized without matching a longer ID.
_OUTFIT_ITEM_ID_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Z]\d{3}(?![A-Za-z0-9_])", re.IGNORECASE)
_OUTFIT_EXCLUSION_RE = re.compile(
    r"(?:"
    r"\b(?:exclude|excluded|excluding|reject|rejected|rejecting|avoid|"
    r"unsuitable|inappropriate)\b"
    r"|\b(?:not|never)\s+(?:recommended?|appropriate|suitable|selected|chosen)\b"
    r"|\b(?:do|does|did|would|should|could|cannot|can't)\s+not\s+"
    r"(?:recommend|choose|select)\b"
    r"|\bshould\s+be\s+excluded\b"
    r"|추천\s*(?:하지\s*않|할\s*수\s*없|목록에서\s*제외)"
    r"|(?:부적합|적합하지\s*않|추천하지\s*않|추천할\s*수\s*없|"
    r"선택하지\s*않|선택에서\s*제외|제외|배제|피하)"
    r")",
    re.IGNORECASE,
)
_OUTFIT_SELECTION_RE = re.compile(
    r"(?:"
    r"(?<!not\s)(?<!do\s)(?<!does\s)(?<!did\s)(?<!would\s)"
    r"(?<!should\s)(?<!could\s)(?<!cannot\s)(?<!can't\s)"
    r"\b(?:recommend(?:ed|ation)?|select(?:ed|ion)?|choose|chosen|wear|use)\b"
    r"|\bselected_items\b"
    r"|추천(?!\s*(?:하지|할\s*수\s*없|목록에서\s*제외))"
    r"|선택(?!\s*(?:하지|에서\s*제외))"
    r"|착용"
    r")",
    re.IGNORECASE,
)
_OUTFIT_RANKED_ITEM_RE = re.compile(
    r"(?:^\s*(?:\d+\s*[.)]|[-•]|\*(?!\*)|\|)|"
    r"(?:\brecommended?\b|\brank(?:ed|ing)?\b|추천|순위)[^:\n|]{0,20}[:：]\s*"
    r"\d+\s*[.)])",
    re.IGNORECASE,
)


def _unique_in_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _line_context(text: str, start: int, end: int) -> str:
    physical_line_start = text.rfind("\n", 0, start) + 1
    physical_line_end = text.find("\n", end)
    if physical_line_end < 0:
        physical_line_end = len(text)
    physical_line = text[physical_line_start:physical_line_end]
    markdown_table_line = physical_line.lstrip().startswith("|")
    boundaries = "\n.!?。！？;；" + ("" if markdown_table_line else "|")
    relative_start = start - physical_line_start
    numbering = re.match(r"\s*\d+\s*[.)]", physical_line)
    ignored_prefix_end = numbering.end() if numbering else 0
    ranked_punctuation = {
        physical_line_start + match.end() - 1
        for match in re.finditer(
            r"(?<![A-Za-z0-9])\d+\s*[.)](?=\s|[A-Za-z가-힣]|$)",
            physical_line,
        )
    }
    left_boundaries = [
        physical_line_start + index
        for index, character in enumerate(physical_line[:relative_start])
        if character in boundaries
        and index >= ignored_prefix_end
        and physical_line_start + index not in ranked_punctuation
    ]
    line_start = max(left_boundaries, default=physical_line_start - 1) + 1
    candidates = [
        physical_line_start + index
        for index, character in enumerate(physical_line)
        if physical_line_start + index >= end
        and character in boundaries
        and physical_line_start + index not in ranked_punctuation
    ]
    line_end = min(candidates, default=physical_line_end)
    return text[line_start:line_end]


def _item_context_status(context: str) -> str:
    exclusion_matches = list(_OUTFIT_EXCLUSION_RE.finditer(context))
    selection_matches = list(_OUTFIT_SELECTION_RE.finditer(context))
    if exclusion_matches and selection_matches:
        last_exclusion = exclusion_matches[-1].start()
        last_selection = selection_matches[-1].start()
        return "selected" if last_selection > last_exclusion else "excluded"
    if exclusion_matches:
        return "excluded"
    if selection_matches or _OUTFIT_RANKED_ITEM_RE.search(context):
        return "selected"
    return "mentioned"


def _extract_outfit(payload: dict[str, Any], text: str) -> dict[str, Any]:
    inventory = payload.get("business_data", {}).get("shopping_history", {}).get(
        payload.get("input", {}).get("user_id", ""), []
    )
    known_ids = {str(item.get("id")) for item in inventory}
    occurrences: list[tuple[int, str, str]] = []
    for match in _OUTFIT_ITEM_ID_RE.finditer(text):
        occurrences.append((match.start(), match.group(0).upper(), _line_context(text, match.start(), match.end())))
    for item in inventory:
        item_id = str(item.get("id"))
        item_name = _lower(item.get("item"))
        if not item_name:
            continue
        for match in re.finditer(re.escape(item_name), text, re.IGNORECASE):
            occurrences.append((match.start(), item_id, _line_context(text, match.start(), match.end())))

    occurrences.sort(key=lambda value: value[0])
    mentioned_ids = _unique_in_order([item_id for _, item_id, _ in occurrences])
    unknown_ids = sorted({item_id for item_id in mentioned_ids if item_id not in known_ids})
    known_mentions = [item_id for item_id in mentioned_ids if item_id in known_ids]
    statuses: dict[str, set[str]] = {item_id: set() for item_id in known_mentions}
    selected_occurrences: list[str] = []
    ranked_selected_occurrences: list[str] = []
    excluded_occurrences: list[str] = []
    for _, item_id, context in occurrences:
        if item_id in statuses:
            status = _item_context_status(context)
            statuses[item_id].add(status)
            if status == "selected":
                selected_occurrences.append(item_id)
                if _OUTFIT_RANKED_ITEM_RE.search(context):
                    ranked_selected_occurrences.append(item_id)
            elif status == "excluded":
                excluded_occurrences.append(item_id)

    selected_order = ranked_selected_occurrences + [
        item_id
        for item_id in selected_occurrences
        if item_id not in ranked_selected_occurrences
    ]
    selected_ids = [
        item_id
        for item_id in _unique_in_order(selected_order)
        if "excluded" not in statuses[item_id]
    ]
    excluded_ids = [
        item_id
        for item_id in _unique_in_order(excluded_occurrences)
        if "selected" not in statuses[item_id]
    ]
    ambiguous_ids = [
        item_id
        for item_id in known_mentions
        if "selected" in statuses[item_id] and "excluded" in statuses[item_id]
    ]
    mentioned_only_ids = [
        item_id
        for item_id in known_mentions
        if item_id not in selected_ids and item_id not in excluded_ids and item_id not in ambiguous_ids
    ]
    unsupplied_recommendations = []
    marker = "추가 추천"
    if marker in text:
        recommendation_text = text.split(marker, 1)[1].lstrip(" :：\n")
        if "추가 조건" in recommendation_text:
            recommendation_text = recommendation_text.split("추가 조건", 1)[0].strip(" :：\n")
        if recommendation_text and not recommendation_text.startswith(("없음", "없습니다", "없어요")):
            unsupplied_recommendations.append("explicit_additional_recommendation")
    weather = payload.get("shared_context", {}).get("weather", {})
    weather_values = [
        str(weather.get("date", "")),
        str(weather.get("condition", "")).lower(),
        str(weather.get("temp_min", "")),
        str(weather.get("temp_max", "")),
        str(weather.get("precipitation_probability", "")),
    ]
    used_weather = any(value and value in text for value in weather_values)
    rain_threshold = payload.get("constraints", {}).get(
        "rain_safe_precipitation_min", 40
    )
    if not isinstance(rain_threshold, (int, float)):
        rain_threshold = 40
    rain_unsafe_inventory_ids = []
    if weather.get("precipitation_probability", 0) >= rain_threshold:
        inventory_by_id = {str(item.get("id")): item for item in inventory}
        for item_id in selected_ids:
            if inventory_by_id.get(item_id, {}).get("rain_ok") is not True:
                rain_unsafe_inventory_ids.append(item_id)
    return {
        "selected_items": selected_ids,
        "excluded_items": excluded_ids,
        "mentioned_items": known_mentions,
        "mentioned_only_items": mentioned_only_ids,
        "ambiguous_items": ambiguous_ids,
        "parse_status": "ambiguous" if ambiguous_ids else "ok",
        "unknown_inventory_ids": unknown_ids,
        "unsupplied_recommendations": unsupplied_recommendations,
        "rain_unsafe_inventory_ids": rain_unsafe_inventory_ids,
        "weather_used": used_weather,
    }


def _extract_presentation(payload: dict[str, Any], text: str) -> dict[str, Any]:
    constraints = payload.get("constraints", {})
    required_sections = constraints.get("required_sections", [])
    section_aliases = {
        "opening": ("opening", "introduction", "开始", "开场"),
        "problem": ("problem", "问题"),
        "architecture": ("architecture", "结构", "架构"),
        "multi-domain evidence": ("multi-domain", "multiple domains", "多领域"),
        "conclusion": ("conclusion", "结论", "마무리"),
    }
    sections = [
        section
        for section in required_sections
        if any(alias in text for alias in section_aliases.get(section, (section,)))
    ]
    knowledge = payload.get("business_data", {})
    knowledge_terms = [str(topic.get("title", "")).lower() for topic in knowledge.get("topics", [])]
    duration_match = re.search(r"(?<!\d)(\d+)\s*(?:-|~)?\s*(?:minutes?|분)", text)
    return {
        "duration_minutes": int(duration_match.group(1)) if duration_match else None,
        "outline_sections": sections,
        "knowledge_used": any(term and term in text for term in knowledge_terms),
    }


def _extract_support(payload: dict[str, Any], text: str) -> dict[str, Any]:
    categories = payload.get("business_data", {}).get("categories", [])
    category_id = None
    for category in categories:
        if str(category.get("id", "")).lower() in text or str(category.get("label", "")).lower() in text:
            category_id = category.get("id")
            break
    owner_team = next(
        (category.get("owner_team") for category in categories if _lower(category.get("owner_team")) in text),
        None,
    )
    priority_match = re.search(r"\bp[1-9]\b", text)
    sla_match = re.search(r"\b\d+\s+business\s+day(?:s)?\b", text)
    return {
        "category": category_id,
        "route": owner_team,
        "priority": priority_match.group(0).upper() if priority_match else None,
        "sla": sla_match.group(0) if sla_match else None,
    }


def extract_structured_fields(fixture: Any, response: str) -> dict[str, Any]:
    payload = _payload(fixture)
    text = _lower(response)
    domain = payload.get("domain")
    if domain == "outfit":
        return _extract_outfit(payload, text)
    if domain == "presentation":
        return _extract_presentation(payload, text)
    if domain == "customer_support":
        return _extract_support(payload, text)
    return {}


def score_response(fixture: Any, response: str) -> dict[str, Any]:
    payload = _payload(fixture)
    text = _lower(response)
    parsed = extract_structured_fields(payload, response)
    missing_fields = _required_fields(payload, text, parsed)
    domain = payload.get("domain")
    context_usage = False
    unsupported_fact_flags: list[str] = []

    if domain == "outfit":
        context_usage = bool(parsed.get("weather_used")) or bool(parsed.get("selected_items"))
        unsupported_fact_flags = [
            f"unknown_inventory_id:{item_id}" for item_id in parsed.get("unknown_inventory_ids", [])
        ] + [f"{item}" for item in parsed.get("unsupplied_recommendations", [])] + [
            f"rain_unsafe_inventory_id:{item_id}"
            for item_id in parsed.get("rain_unsafe_inventory_ids", [])
        ]
        constraint_satisfaction = not unsupported_fact_flags and context_usage
    elif domain == "presentation":
        context_usage = bool(parsed.get("knowledge_used"))
        constraint_satisfaction = (
            parsed.get("duration_minutes") == payload.get("constraints", {}).get("duration_minutes")
            and len(parsed.get("outline_sections", []))
            == len(payload.get("constraints", {}).get("required_sections", []))
        )
    elif domain == "customer_support":
        truth = derive_ground_truth(payload)
        context_usage = any(
            value and _lower(value) in text
            for value in (truth.get("label"), truth.get("policy"), *truth.get("next_actions", []))
        )
        constraint_satisfaction = (
            parsed.get("category") == truth.get("category_id")
            and parsed.get("route") == truth.get("owner_team")
            and parsed.get("priority") == truth.get("priority")
            and parsed.get("sla") == truth.get("sla")
        )
    else:
        constraint_satisfaction = False

    result = {
        "case_id": payload.get("case_id", ""),
        "required_fields_present": not missing_fields,
        "required_fields_missing": missing_fields,
        "context_usage": context_usage,
        "constraint_satisfaction": constraint_satisfaction,
        "completeness": not missing_fields and constraint_satisfaction,
        "unsupported_fact_flags": unsupported_fact_flags,
        "human_evaluation_status": "pending",
        "parsed": parsed,
    }
    if domain == "customer_support":
        result["ground_truth_correctness"] = constraint_satisfaction
    else:
        result["ground_truth_correctness"] = "not_applicable"
        result["open_language_quality"] = "human_evaluation_required"
    return result


def structured_agreement(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"run_count": 0, "all_match": False, "compared_fields": []}
    fields = sorted({field for record in records for field in record})
    # An empty list can be a valid structured result (for example, no
    # unsupported inventory IDs); only absent/blank scalar values are missing.
    all_present = all(
        record.get(field) not in (None, "")
        for record in records
        for field in fields
    )
    values = [
        json.dumps([record.get(field) for field in fields], ensure_ascii=False, sort_keys=True)
        for record in records
    ]
    return {
        "run_count": len(records),
        "all_match": all_present and len(set(values)) == 1,
        "compared_fields": fields,
    }


def count_touch_points(criteria: dict[str, Any], system: str) -> int:
    actions = criteria.get("configuration_touch_points", {}).get(system)
    if not isinstance(actions, list):
        raise ValueError(f"missing configuration action definition: {system}")
    return len(actions)


def compare_reuse(
    criteria: dict[str, Any],
    first_config: dict[str, Any] | None = None,
    second_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scenario = criteria.get("reuse_scenario", {})
    first = scenario.get("first_task", {})
    second = scenario.get("second_task", {})
    visible_fields = scenario.get("visible_fields", [])
    changed_fields = [field for field in visible_fields if first.get(field) != second.get(field)]
    configuration_errors = []
    for label, config in (("first", first_config), ("second", second_config)):
        if config is None:
            continue
        for key in ("runtime_type", "nodes", "execution"):
            if key not in config:
                configuration_errors.append(f"{label} config missing {key}")
    return {
        "first_task": first,
        "second_task": second,
        "changed_fields": changed_fields,
        "initial_configuration_actions": count_touch_points(criteria, "builder"),
        "reuse_configuration_actions": len(changed_fields),
        "configuration_errors": configuration_errors,
    }


def _flatten_fields(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, Mapping):
        fields = {}
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            fields.update(_flatten_fields(child, child_prefix))
        return fields
    if isinstance(value, list):
        fields = {}
        for index, child in enumerate(value):
            fields.update(_flatten_fields(child, f"{prefix}[{index}]"))
        return fields
    return {prefix: value}


def compare_workflow_reuse(
    first_config: Mapping[str, Any],
    second_config: Mapping[str, Any],
    *,
    runtime_modified: bool = False,
) -> dict[str, Any]:
    """Report auditable config and node reuse without making a quality claim."""
    first_fields = _flatten_fields(first_config)
    second_fields = _flatten_fields(second_config)
    changed_fields = sorted(
        field
        for field in first_fields.keys() & second_fields.keys()
        if first_fields[field] != second_fields[field]
    )
    added_fields = sorted(second_fields.keys() - first_fields.keys())
    removed_fields = sorted(first_fields.keys() - second_fields.keys())

    first_nodes = {
        str(node.get("id")): node
        for node in first_config.get("nodes", [])
        if isinstance(node, Mapping) and node.get("id")
    }
    second_nodes = {
        str(node.get("id")): node
        for node in second_config.get("nodes", [])
        if isinstance(node, Mapping) and node.get("id")
    }
    shared_ids = first_nodes.keys() & second_nodes.keys()

    def structural(node: Mapping[str, Any]) -> dict[str, Any]:
        return {
            key: node.get(key)
            for key in ("id", "type", "inputs", "outputs", "required_inputs")
        }

    reused_nodes = sorted(
        node_id
        for node_id in shared_ids
        if structural(first_nodes[node_id]) == structural(second_nodes[node_id])
    )
    modified_nodes = sorted(
        node_id
        for node_id in shared_ids
        if first_nodes[node_id] != second_nodes[node_id]
    )
    modified_node_configs = sorted(
        node_id
        for node_id in shared_ids
        if first_nodes[node_id].get("config") != second_nodes[node_id].get("config")
    )
    replaced_nodes = sorted(
        node_id
        for node_id in shared_ids
        if first_nodes[node_id].get("type") != second_nodes[node_id].get("type")
    )
    new_nodes = sorted(second_nodes.keys() - first_nodes.keys())
    removed_nodes = sorted(first_nodes.keys() - second_nodes.keys())

    return {
        "changed_fields": changed_fields,
        "added_fields": added_fields,
        "removed_fields": removed_fields,
        "modified_nodes": modified_nodes,
        "modified_node_configs": modified_node_configs,
        "reused_nodes": reused_nodes,
        "replaced_nodes": replaced_nodes,
        "new_nodes": new_nodes,
        "removed_nodes": removed_nodes,
        "runtime_modified": bool(runtime_modified),
        "reused_node_count": len(reused_nodes),
    }

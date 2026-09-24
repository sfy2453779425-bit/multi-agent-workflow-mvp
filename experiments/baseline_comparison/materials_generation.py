from __future__ import annotations

import csv
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "experiments" / "baseline_comparison"
V2_ROOT = PACKAGE_ROOT / "v2"
FIXTURE_ROOT = PACKAGE_ROOT / "fixtures"
HUMAN_ROOT = V2_ROOT / "human_evaluation"
VIS_ROOT = V2_ROOT / "visualization"

EXPERIMENT_ID = "builder_v2_pilot_20260916"
EVALUATION_VERSION = "evaluation-v2"
HUMAN_EVAL_SEED = 20260917
SELECTED_RUN = 1
SELECTED_CASES = (
    "customer_support_01",
    "customer_support_05",
    "outfit_01",
    "outfit_02",
    "presentation_01",
    "presentation_02",
)
FORBIDDEN_DISPLAY_TERMS = (
    "chatgpt",
    "gpt-5.6 sol",
    "claude",
    "builder",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    _write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _fixture_path(case_id: str) -> Path:
    if case_id.startswith("customer_support_"):
        domain = "customer_support"
    else:
        domain = case_id.split("_", 1)[0]
    return FIXTURE_ROOT / domain / f"{case_id}.json"


def _load_case(case_id: str) -> dict[str, Any]:
    return _read_json(_fixture_path(case_id))


def _load_responses(case_id: str) -> dict[str, Any]:
    chat_path = V2_ROOT / "llm_runs" / "chatgpt" / f"chatgpt_{case_id}_run_{SELECTED_RUN}.json"
    builder_path = V2_ROOT / "builder_runs" / case_id / f"run_{SELECTED_RUN}.json"
    chat = _read_json(chat_path)
    builder = _read_json(builder_path)
    chat_response = str(chat["response"])
    builder_response = str(builder["final_result"]["answer"])
    return {
        "chatgpt": {
            "response": chat_response,
            "source_sha256": str(chat.get("response_sha256") or _sha256_text(chat_response)),
            "run_id": chat.get("run_id", ""),
        },
        "builder": {
            "response": builder_response,
            "source_sha256": _sha256_text(builder_response),
            "run_id": builder.get("run_id", ""),
        },
    }


def _blind_text(text: str) -> str:
    replacements = (
        (r"Multi-Agent Workflow Builder", "Multi-Agent Workflow Tool"),
        (r"multi-agent workflow builder", "multi-agent workflow tool"),
        (r"Workflow Builder", "Workflow Tool"),
        (r"workflow builder", "workflow tool"),
        (r"\bChatGPT\b", "the system"),
        (r"\bGPT-5\.6 Sol\b", "the model"),
        (r"\bClaude\b", "the system"),
        (r"\bBuilder\b", "the tool"),
        (r"\bbuilder\b", "the tool"),
    )
    result = text
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result)
    return result


def _render_context(fixture: dict[str, Any]) -> str:
    domain = fixture["domain"]
    lines = [f"Language: {fixture.get('constraints', {}).get('language', 'not specified')}"]
    if domain == "outfit":
        weather = fixture["shared_context"]["weather"]
        lines.extend(
            [
                "Weather:",
                f"- City: {weather.get('city_name', '')}",
                f"- Date: {weather.get('date', '')}",
                f"- Condition: {weather.get('condition', '')}",
                f"- Temperature: {weather.get('temp_min')}–{weather.get('temp_max')}°C",
                f"- Precipitation probability: {weather.get('precipitation_probability')}%",
                "Supplied inventory:",
            ]
        )
        user_id = fixture["input"]["user_id"]
        inventory = fixture["business_data"]["shopping_history"].get(user_id, [])
        for item in inventory:
            lines.append(
                "- {id}: {item}; style={style}; warmth={warmth}; rain_ok={rain_ok}".format(
                    id=item.get("id", ""),
                    item=item.get("item", ""),
                    style=item.get("style", ""),
                    warmth=item.get("warmth", ""),
                    rain_ok=item.get("rain_ok", ""),
                )
            )
        constraints = fixture["constraints"]
        lines.extend(
            [
                "Constraints:",
                f"- Use only supplied inventory: {constraints.get('inventory_only', False)}",
                f"- Rain-safe precipitation threshold: {constraints.get('rain_safe_precipitation_min', '')}%",
                f"- Purpose: {constraints.get('purpose', '')}",
                f"- Style: {constraints.get('style', '')}",
                f"- Do not invent facts: {constraints.get('do_not_invent_facts', False)}",
            ]
        )
    elif domain == "customer_support":
        query = fixture["input"]["query"]
        lines.extend([f"Customer query: {query}", "Relevant frozen policy:"])
        query_lower = query.lower()
        categories = fixture["business_data"].get("categories", [])
        matched = [
            category
            for category in categories
            if any(str(keyword).lower() in query_lower for keyword in category.get("keywords", []))
        ]
        for category in matched or categories:
            lines.extend(
                [
                    f"- Category: {category.get('label', '')}",
                    f"  Owner team: {category.get('owner_team', '')}",
                    f"  Priority: {category.get('priority', '')}",
                    f"  SLA: {category.get('sla', '')}",
                    f"  Policy: {category.get('policy', '')}",
                    "  Next actions:",
                ]
            )
            lines.extend(f"  - {action}" for action in category.get("next_actions", []))
        precedence = fixture["constraints"].get("mixed_intent_precedence", [])
        if precedence:
            lines.append(f"Mixed-intent precedence: {' > '.join(precedence)}")
        lines.append("Do not invent facts.")
    elif domain == "presentation":
        constraints = fixture["constraints"]
        lines.extend(
            [
                f"Task request: {fixture['input']['query']}",
                f"Duration: {constraints.get('duration_minutes')} minutes",
                "Required sections: " + ", ".join(constraints.get("required_sections", [])),
                "Supplied knowledge:",
            ]
        )
        for topic in fixture["business_data"].get("topics", []):
            lines.append(f"- Topic: {topic.get('title', '')}")
            lines.extend(f"  - {point}" for point in topic.get("points", []))
        lines.extend(
            [
                f"Use supplied knowledge only: {constraints.get('use_supplied_knowledge_only', False)}",
                f"Do not invent facts: {constraints.get('do_not_invent_facts', False)}",
            ]
        )
    else:
        raise ValueError(f"Unsupported domain: {domain}")
    return _blind_text("\n".join(lines))


def _render_task(fixture: dict[str, Any]) -> str:
    return _blind_text(str(fixture["input"]["query"]))


def _random_mapping() -> dict[str, dict[str, str]]:
    rng = random.Random(HUMAN_EVAL_SEED)
    mapping = {}
    for case_id in SELECTED_CASES:
        if rng.choice((True, False)):
            mapping[case_id] = {"A": "chatgpt", "B": "builder"}
        else:
            mapping[case_id] = {"A": "builder", "B": "chatgpt"}
    return mapping


def _human_instructions() -> str:
    return """# Blind Human Evaluation Instructions

## Purpose

You will evaluate two anonymized responses for six task cases. The source of Response A and Response B is hidden. Please do not try to guess the source.

## Procedure

1. Read the task and the supplied context.
2. Read Response A and Response B.
3. Score each response independently on the four dimensions below.
4. Enter one integer from 1 to 5 for every dimension.
5. Add a short note only when it helps explain an unusual score.

Do not give a higher score only because a response is longer. Do not give a lower score only because it is shorter. Judge the response against the current task and context. If you are uncertain, a score of 3 is acceptable.

## Scoring dimensions

### Usefulness

How much practical help does the response provide for completing the task?

1 = almost no help; 2 = limited help; 3 = average; 4 = clearly helpful; 5 = very helpful.

### Clarity

How clear and easy to understand is the response?

1 = very difficult to understand; 2 = somewhat difficult; 3 = average; 4 = clear; 5 = very clear.

### Naturalness

How natural is the response for a reader who expects a normal answer to this task?

1 = very unnatural; 2 = somewhat unnatural; 3 = average; 4 = natural; 5 = very natural.

### Human-perceived completeness

How fully does the response answer the task from a reader's perspective?

1 = seriously incomplete; 2 = somewhat incomplete; 3 = basically complete; 4 = complete; 5 = very complete.

This is a human-perception measure. It is separate from the experiment's objective completeness field.

## Data entry

Use the CSV assigned to you. Each row is one response evaluation. Keep the case ID and response label unchanged. Fill in:

`usefulness`, `clarity`, `naturalness`, `human_perceived_completeness`, and optionally `optional_notes`.

Please do not add source labels or discuss which system you think produced a response.
"""


def _write_human_materials() -> dict[str, Any]:
    mapping = _random_mapping()
    records = {}
    private_mapping = {
        "experiment_id": EXPERIMENT_ID,
        "evaluation_version": EVALUATION_VERSION,
        "human_eval_random_seed": HUMAN_EVAL_SEED,
        "selected_run": SELECTED_RUN,
        "selected_cases": list(SELECTED_CASES),
        "blind_mapping": mapping,
        "cases": {},
        "note": "Organizer-only file. Do not distribute to evaluators.",
    }
    for case_id in SELECTED_CASES:
        fixture = _load_case(case_id)
        responses = _load_responses(case_id)
        task = _render_task(fixture)
        context = _render_context(fixture)
        records[case_id] = {"task": task, "context": context, "responses": responses}
        private_mapping["cases"][case_id] = {
            "run": SELECTED_RUN,
            "label_to_system": mapping[case_id],
            "original_response_sha256": {
                label: responses[system]["source_sha256"]
                for label, system in mapping[case_id].items()
            },
            "blind_response_sha256": {
                label: _sha256_text(_blind_text(responses[system]["response"]))
                for label, system in mapping[case_id].items()
            },
        }

    HUMAN_ROOT.mkdir(parents=True, exist_ok=True)
    _write_text(HUMAN_ROOT / "instructions.md", _human_instructions())
    _write_json(HUMAN_ROOT / "human_evaluation_mapping.json", private_mapping)

    columns = [
        "evaluator_id",
        "case_id",
        "response_label",
        "task",
        "context",
        "response",
        "usefulness",
        "clarity",
        "naturalness",
        "human_perceived_completeness",
        "optional_notes",
    ]
    for evaluator_number in range(1, 6):
        path = HUMAN_ROOT / f"evaluator_{evaluator_number:02d}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for case_id in SELECTED_CASES:
                for label in ("A", "B"):
                    system = mapping[case_id][label]
                    writer.writerow(
                        {
                            "evaluator_id": f"evaluator_{evaluator_number:02d}",
                            "case_id": case_id,
                            "response_label": label,
                            "task": records[case_id]["task"],
                            "context": records[case_id]["context"],
                            "response": _blind_text(responses_for_case(records, case_id, system)),
                            "usefulness": "",
                            "clarity": "",
                            "naturalness": "",
                            "human_perceived_completeness": "",
                            "optional_notes": "",
                        }
                    )

    selected_root = HUMAN_ROOT / "selected_responses"
    selected_root.mkdir(parents=True, exist_ok=True)
    for case_id in SELECTED_CASES:
        record = records[case_id]
        response_a = _blind_text(record["responses"][mapping[case_id]["A"]]["response"])
        response_b = _blind_text(record["responses"][mapping[case_id]["B"]]["response"])
        content = (
            f"# {case_id}\n\n"
            "## Task\n\n"
            f"{record['task']}\n\n"
            "## Context\n\n"
            f"{record['context']}\n\n"
            "## Response A\n\n"
            f"{response_a}\n\n"
            "## Response B\n\n"
            f"{response_b}\n"
        )
        _write_text(selected_root / f"{case_id}.md", content)
    return private_mapping


def responses_for_case(records: dict[str, Any], case_id: str, system: str) -> str:
    return str(records[case_id]["responses"][system]["response"])


def _write_objective_figure_data() -> None:
    VIS_ROOT.mkdir(parents=True, exist_ok=True)
    quality_path = V2_ROOT / "results" / "evaluation_v2" / "case_quality.csv"
    repeatability_path = V2_ROOT / "results" / "evaluation_v2" / "repeatability.csv"
    failure_path = V2_ROOT / "results" / "evaluation_v1" / "failure_localization.json"
    reuse_path = V2_ROOT / "results" / "evaluation_v1" / "workflow_reuse_quantitative.csv"
    quality_rows = list(csv.DictReader(quality_path.open(encoding="utf-8", newline="")))
    repeatability_rows = list(csv.DictReader(repeatability_path.open(encoding="utf-8", newline="")))
    failure = _read_json(failure_path)
    reuse_rows = list(csv.DictReader(reuse_path.open(encoding="utf-8", newline="")))
    rows: list[dict[str, Any]] = []

    metrics = (
        ("required_fields_present", "Required fields"),
        ("constraint_satisfaction", "Constraint satisfaction"),
        ("completeness", "Completeness"),
    )
    for system in ("ChatGPT", "Builder"):
        selected = [row for row in quality_rows if row["system"] == system]
        for field, label in metrics:
            rows.append(
                {
                    "figure": "Figure 1",
                    "scope": "Overall",
                    "system": system,
                    "metric": label,
                    "value": sum(row[field] == "True" for row in selected),
                    "denominator": len(selected),
                    "unit": "count",
                    "category": "",
                    "sequence": "",
                    "status": "",
                    "source": "results/evaluation_v2/case_quality.csv",
                }
            )

    for row in repeatability_rows:
        if row["system"] not in ("ChatGPT", "Builder"):
            continue
        scope = "Overall" if row["case_id"] == "" else row["case_id"]
        if row["case_id"] in {"customer_support_01", "customer_support_02", "customer_support_03", "customer_support_04", "customer_support_05"}:
            scope = "Customer Support"
        elif row["case_id"] in {"presentation_01", "presentation_02"}:
            scope = "Presentation"
        elif row["case_id"] in {"outfit_01", "outfit_02", "outfit_03"}:
            scope = "Outfit"
        rows.append(
            {
                "figure": "Figure 2",
                "scope": scope,
                "system": row["system"],
                "metric": "Structured repeatability",
                "value": 1 if row["structured_fields_match"] == "True" else 0,
                "denominator": 1,
                "unit": "case",
                "category": row["case_id"],
                "sequence": "",
                "status": row["structured_fields_match"],
                "source": "results/evaluation_v2/repeatability.csv",
            }
        )

    for system in ("ChatGPT", "Builder"):
        for scope, case_ids in (
            ("Customer Support", {f"customer_support_{i:02d}" for i in range(1, 6)}),
            ("Presentation", {"presentation_01", "presentation_02"}),
            ("Outfit", {"outfit_01", "outfit_02", "outfit_03"}),
            ("Overall", {f"customer_support_{i:02d}" for i in range(1, 6)} | {"presentation_01", "presentation_02", "outfit_01", "outfit_02", "outfit_03"}),
        ):
            selected = [row for row in repeatability_rows if row["system"] == system and row["case_id"] in case_ids]
            rows.append(
                {
                    "figure": "Figure 2 summary",
                    "scope": scope,
                    "system": system,
                    "metric": "Structured repeatability",
                    "value": sum(row["structured_fields_match"] == "True" for row in selected),
                    "denominator": len(selected),
                    "unit": "case",
                    "category": "",
                    "sequence": "",
                    "status": "",
                    "source": "results/evaluation_v2/repeatability.csv",
                }
            )

    for sequence, trace in enumerate(failure.get("trace", []), start=1):
        rows.append(
            {
                "figure": "Figure 3",
                "scope": "Controlled failure",
                "system": "Builder",
                "metric": "Node status",
                "value": 1,
                "denominator": 1,
                "unit": "status",
                "category": trace.get("node_id", ""),
                "sequence": sequence,
                "status": trace.get("status", ""),
                "source": "results/evaluation_v1/failure_localization.json",
            }
        )

    reuse_by_condition = {row["condition"]: row for row in reuse_rows}
    manual = reuse_by_condition["manual"]
    builder = reuse_by_condition["builder"]
    reuse_metrics = (
        ("Manual", "Changed leaf values", manual["semantic_changed_leaf_values_count"]),
        ("Manual", "Removed fields", manual["semantic_removed_fields_count"]),
        ("Manual", "Modified nodes", manual["semantic_modified_nodes_count"]),
        ("Manual", "Observed configuration actions", manual["manual_observed_actions_count"]),
        ("Template Builder", "Exposed task-level inputs", builder["builder_exposed_inputs_actions_count"]),
        ("Template Builder", "Template-generated fields", builder["generated_fields_count"]),
        ("Template Builder", "Reused nodes", builder["generated_node_definitions_count"]),
        ("Template Builder", "Input bindings", builder["generated_input_bindings_count"]),
        ("Template Builder", "Output bindings", builder["generated_output_bindings_count"]),
        ("Template Builder", "Required-input declarations", builder["generated_required_input_declarations_count"]),
        ("Template Builder", "Execution-order entries", builder["generated_execution_order_count"]),
    )
    for condition, metric, value in reuse_metrics:
        rows.append(
            {
                "figure": "Figure 4",
                "scope": condition,
                "system": condition,
                "metric": metric,
                "value": value,
                "denominator": "",
                "unit": "count",
                "category": "",
                "sequence": "",
                "status": "",
                "source": "results/evaluation_v1/workflow_reuse_quantitative.csv",
            }
        )

    columns = [
        "figure",
        "scope",
        "system",
        "metric",
        "value",
        "denominator",
        "unit",
        "category",
        "sequence",
        "status",
        "source",
    ]
    with (VIS_ROOT / "objective_figure_data.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_professor_materials() -> None:
    _write_text(
        V2_ROOT / "professor_update_summary.md",
        """# Professor Update Summary

## Professor Question

Why not just use ChatGPT?

## Experiment

This pilot used 10 frozen cases, three independent runs per case, and the same ChatGPT model setting across the 30 ChatGPT runs. Builder results were evaluated under the same frozen fixtures and requirements.

## Finding 1: ChatGPT performed strongly

- Constraint satisfaction: 30/30
- Customer Support structured repeatability: 5/5 cases
- Presentation structured repeatability: 2/2 cases

The main objective gaps were missing required fields and lower structured repeatability in Outfit.

## Finding 2: The Builder kept a fixed workflow contract

- Required fields: 30/30
- Objective completeness: 30/30
- Structured repeatability: 10/10 cases

The Builder also exposes validation, node trace, failure localization, and template-generated workflow structure.

## Finding 3: The value is workflow engineering evidence

The pilot does not show that the Builder produces better language or better answers in every task. It shows a different type of evidence: a domain workflow can be represented as ordered nodes, validated before execution, traced during execution, and reused through a template.

## Conclusion

ChatGPT is strong for direct task completion, while the Builder provides additional value when tasks require fixed output contracts, repeatable execution, validation, and observable workflow behavior.

This is a pilot result. It does not establish a general model ranking, an overall winner, or a speed advantage.

## Human Evaluation Status

Blind evaluation materials are prepared for six representative cases. Human scores have not yet been collected, so no human-quality conclusion is included here.
""",
    )
    _write_text(
        V2_ROOT / "evaluation_methodology_note.md",
        """# Evaluation Methodology Note

## Parser correction

The first analysis version was `evaluation-v1`. During review, an Evaluation Parser defect was found in the Outfit parser: any known inventory ID mentioned in a response could be treated as a selected recommendation. This incorrectly included items that the response explicitly excluded or only described.

The raw ChatGPT responses were not edited, regenerated, or re-collected. Prompt files, fixtures, Builder v2, templates, Workflow Runtime, and business policy data were not changed.

The parser was corrected to separate:

- selected or recommended items
- excluded or rejected items
- ordinary inventory mentions
- ambiguous cases when the disposition cannot be determined safely

The full 30 raw ChatGPT records were reanalyzed as `evaluation-v2`.

## Effect on the pilot measurements

The measured change was:

```text
Constraint satisfaction: 27/30 → 30/30
Completeness: 22/30 → 23/30
Required fields: 23/30 → 23/30
Structured repeatability: 7/10 → 7/10
```

The change comes from correcting the measurement logic. It does not mean that a ChatGPT response was regenerated or improved after the fact.

The official results for the current pilot are the `evaluation-v2` results. `evaluation-v1` is retained as a historical snapshot for audit and comparison.
""",
    )


def generate() -> None:
    manifest = _read_json(V2_ROOT / "manifest.json")
    metadata = _read_json(V2_ROOT / "results" / "evaluation_v2" / "metadata.json")
    if manifest.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("Frozen experiment_id does not match the material specification")
    if metadata.get("evaluation_version") != EVALUATION_VERSION:
        raise ValueError("evaluation-v2 metadata is required")
    _write_human_materials()
    _write_objective_figure_data()
    _write_professor_materials()


if __name__ == "__main__":
    generate()
    print(f"Generated blind evaluation materials and objective data under {V2_ROOT}")

import json
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from agent_builder import MultiAgentWorkflowEngine  # noqa: E402
import web_app  # noqa: E402


OUTPUT_DIR = ROOT / "outputs" / "harness_comparison"


MANUAL_HARNESS_SPECS: dict[str, dict[str, Any]] = {
    "presentation_planning": {
        "case_title_zh": "发表规划任务",
        "case_title_kr": "발표 기획 업무",
        "query": "Prepare a 15-minute presentation outline about Harness Engineering and Multi-Agent Workflow Builder MVP.",
        "user_id": "user_a",
        "runtime_type": "presentation_planning",
        "data_file": "presentation_knowledge.json",
        "harness_components": [
            "Model role definitions",
            "Tool binding",
            "Context and memory schema",
            "Constraints",
            "Feedback loop",
            "Verification and trace rule",
            "Execution environment",
        ],
        "agents": [
            {
                "id": "request_parser",
                "name": "Presentation Request Parser Node",
                "role": "Extract presentation topic, target duration and expected output from the user request.",
                "builder_equivalent": "Start Node + Parser/Prompt Node",
            },
            {
                "id": "question",
                "name": "Presentation Question Node",
                "role": "Ask for the missing presentation topic before planning.",
                "builder_equivalent": "Condition Node + User Input Node",
            },
            {
                "id": "topic_analysis",
                "name": "Topic Analysis Node",
                "role": "Identify relevant concepts and decide which knowledge notes are needed.",
                "builder_equivalent": "Classifier Node + Tag Extraction Node",
            },
            {
                "id": "knowledge_lookup",
                "name": "Knowledge Lookup Node",
                "role": "Load local knowledge notes for the matched presentation topics.",
                "builder_equivalent": "Local Knowledge / RAG Node",
            },
            {
                "id": "outline_generation",
                "name": "Outline Generation Node",
                "role": "Create a section-by-section presentation outline from the topic and knowledge notes.",
                "builder_equivalent": "Planning / LLM Decision Node",
            },
            {
                "id": "compose",
                "name": "Presentation Compose Node",
                "role": "Render the final outline with evidence points and execution trace.",
                "builder_equivalent": "Output Template Node",
            },
        ],
        "question_agent": {
            "required_fields": ["topic"],
            "clarification_questions": {
                "topic": "Please provide the presentation topic before generating an outline."
            },
        },
    },
    "customer_support": {
        "case_title_zh": "客服工单分流任务",
        "case_title_kr": "고객 문의 분류 업무",
        "query": "Customer says the delivery is late and asks whether the order can be refunded.",
        "user_id": "user_a",
        "runtime_type": "customer_support",
        "data_file": "support_policy.json",
        "harness_components": [
            "Model role definitions",
            "Tool binding",
            "Context and memory schema",
            "Constraints",
            "Feedback loop",
            "Verification and trace rule",
            "Execution environment",
        ],
        "agents": [
            {
                "id": "request_parser",
                "name": "Support Request Parser Node",
                "role": "Extract issue keywords, customer intent and available ticket context.",
                "builder_equivalent": "Start Node + Parser/Prompt Node",
            },
            {
                "id": "question",
                "name": "Support Question Node",
                "role": "Ask for missing issue details before routing the ticket.",
                "builder_equivalent": "Condition Node + User Input Node",
            },
            {
                "id": "ticket_classification",
                "name": "Ticket Classification Node",
                "role": "Classify the ticket category by matching local policy keywords.",
                "builder_equivalent": "Classifier Node",
            },
            {
                "id": "policy_lookup",
                "name": "Policy Lookup Node",
                "role": "Load the local support policy for the matched ticket category.",
                "builder_equivalent": "Local Knowledge / RAG Node",
            },
            {
                "id": "routing_decision",
                "name": "Routing Decision Node",
                "role": "Decide ticket owner, priority and next actions from classification and policy.",
                "builder_equivalent": "Rule/LLM Decision Node",
            },
            {
                "id": "compose",
                "name": "Support Compose Node",
                "role": "Render the ticket summary, routing decision and response draft.",
                "builder_equivalent": "Output Template Node",
            },
        ],
        "question_agent": {
            "required_fields": ["issue_text"],
            "clarification_questions": {
                "issue_text": "Please describe the customer issue before routing the ticket."
            },
        },
    },
}


def build_manual_harness_config(case_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow_id": f"generic_harness_{case_id}_workflow",
        "workflow_name": f"Generic Harness {spec['case_title_zh']} Workflow",
        "description": (
            "Manual generic Harness Engineering baseline. The Agent roles, tool binding, "
            "constraints, verification and execution order are hand-defined for this case."
        ),
        "runtime_type": spec["runtime_type"],
        "base_agent_config": None,
        "data_file": spec["data_file"],
        "data_dir": str((ROOT / "data").resolve()),
        "default_query": spec["query"],
        "default_user_id": spec["user_id"],
        "agents": spec["agents"],
        "execution": {
            "type": "sequential",
            "order": [agent["id"] for agent in spec["agents"]],
            "generated_by": "GenericHarnessManualSpec",
            "builder_mode": "manual_harness",
        },
        "question_agent": spec["question_agent"],
        "generic_harness": {
            "components": spec["harness_components"],
            "manual_setup_note": "Each domain keeps its own handwritten Agent and component definitions.",
        },
    }


def run_config(config: dict[str, Any], query: str, user_id: str) -> Any:
    with tempfile.TemporaryDirectory(prefix="harness_comparison_") as temp_dir:
        path = Path(temp_dir) / "workflow.json"
        path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        return MultiAgentWorkflowEngine(path).run(query, user_id=user_id)


def touch_points_manual(spec: dict[str, Any]) -> int:
    return (
        len(spec["agents"])
        + len(spec["harness_components"])
        + 1  # execution order
        + 1  # question rule
        + 1  # data binding
        + 1  # runtime type
    )


def touch_points_builder() -> int:
    return 3  # preset, workflow name, user request


def compare_case(case_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    manual_config = build_manual_harness_config(case_id, spec)
    manual_result = run_config(manual_config, spec["query"], spec["user_id"])

    builder_detail = web_app.api_builder_compose(
        {
            "preset": case_id,
            "workflow_name": f"Builder Workspace {spec['case_title_zh']} Workflow",
            "query": spec["query"],
        }
    )
    builder_run = web_app.api_builder_run(
        {
            "preset": case_id,
            "workflow_name": f"Builder Workspace {spec['case_title_zh']} Workflow",
            "query": spec["query"],
            "user": spec["user_id"],
        }
    )

    manual_touch_points = touch_points_manual(spec)
    builder_touch_points = touch_points_builder()
    builder_config = builder_detail["generated_config"]

    return {
        "case_id": case_id,
        "case_title_zh": spec["case_title_zh"],
        "case_title_kr": spec["case_title_kr"],
        "query": spec["query"],
        "generic_harness": {
            "construction": "manual_harness_spec",
            "generated_by": manual_config["execution"]["generated_by"],
            "manual_agent_definitions": len(spec["agents"]),
            "manual_harness_component_sections": len(spec["harness_components"]),
            "construction_touch_points": manual_touch_points,
            "workflow_json_bytes": len(json.dumps(manual_config, ensure_ascii=False)),
            "trace_count": len(manual_result.trace),
            "needs_clarification": bool(manual_result.context.get("needs_clarification")),
            "builder_standardized_json": False,
            "domain_switch": "Copy and rewrite Agent roles, tool binding, rules and execution order for the next domain.",
        },
        "builder_workspace": {
            "construction": "builder_workspace_generated_workflow",
            "generated_by": builder_config["execution"]["generated_by"],
            "source_template": builder_config["execution"]["source_template"],
            "manual_agent_definitions": 0,
            "manual_harness_component_sections": 0,
            "construction_touch_points": builder_touch_points,
            "workflow_json_bytes": len(json.dumps(builder_config, ensure_ascii=False)),
            "trace_count": len(builder_run["trace"]),
            "needs_clarification": bool(builder_run["needs_clarification"]),
            "builder_standardized_json": True,
            "domain_switch": "Select another Builder preset and generate a new executable Workflow JSON.",
        },
        "delta": {
            "manual_agent_definitions_reduced": len(spec["agents"]),
            "manual_component_sections_reduced": len(spec["harness_components"]),
            "touch_points_reduced": manual_touch_points - builder_touch_points,
            "trace_count_equal": len(manual_result.trace) == len(builder_run["trace"]),
        },
    }


def run_experiment(write_outputs: bool = True) -> dict[str, Any]:
    cases = [compare_case(case_id, spec) for case_id, spec in MANUAL_HARNESS_SPECS.items()]
    result = {
        "experiment": "Generic Harness Engineering vs Builder Workspace",
        "method": (
            "Both approaches use the same local execution engine. The comparison isolates how the "
            "workflow is constructed: manual Harness specification vs Builder Workspace generated JSON."
        ),
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "builder_presets_available": len(web_app.api_builder_presets()["presets"]),
            "all_cases_trace_count_equal": all(case["delta"]["trace_count_equal"] for case in cases),
            "average_manual_touch_points": round(
                sum(case["generic_harness"]["construction_touch_points"] for case in cases) / len(cases), 2
            ),
            "average_builder_touch_points": round(
                sum(case["builder_workspace"]["construction_touch_points"] for case in cases) / len(cases), 2
            ),
            "average_touch_points_reduced": round(
                sum(case["delta"]["touch_points_reduced"] for case in cases) / len(cases), 2
            ),
        },
    }

    if write_outputs:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "harness_comparison_results.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (OUTPUT_DIR / "harness_comparison_report_zh.md").write_text(render_report_zh(result), encoding="utf-8")
        (OUTPUT_DIR / "harness_comparison_report_kr.md").write_text(render_report_kr(result), encoding="utf-8")
    return result


def render_report_zh(result: dict[str, Any]) -> str:
    trace_equal = "是" if result["summary"]["all_cases_trace_count_equal"] else "否"
    lines = [
        "# Harness Engineering 对比实验结果",
        "",
        "## 实验设计",
        "",
        "本实验不是比较模型聪明程度，而是比较 Workflow 构建方式。",
        "两组都使用同一个本地执行引擎，差异只放在构建阶段：",
        "",
        "- Generic Harness Engineering：手动定义 Agent、Tool、Context/Memory、Constraints、Feedback Loop、Verification、Execution Environment。",
        "- Builder Workspace：选择业务领域 Preset，生成标准 Workflow JSON，再执行并输出 Trace。",
        "",
        "## 总体结果",
        "",
        f"- 对比任务数：{result['summary']['case_count']}",
        f"- Builder 可用 Preset 数：{result['summary']['builder_presets_available']}",
        f"- Generic Harness 平均构建触点：{result['summary']['average_manual_touch_points']}",
        f"- Builder Workspace 平均构建触点：{result['summary']['average_builder_touch_points']}",
        f"- 平均减少构建触点：{result['summary']['average_touch_points_reduced']}",
        f"- 两组 Trace 步数是否一致：{trace_equal}",
        "",
        "## 任务对比",
        "",
        "| 任务 | Generic Harness 构建触点 | Builder Workspace 构建触点 | 减少 | Generic Trace | Builder Trace | Builder 生成来源 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for case in result["cases"]:
        lines.append(
            "| {title} | {manual} | {builder} | {delta} | {manual_trace} | {builder_trace} | {source} |".format(
                title=case["case_title_zh"],
                manual=case["generic_harness"]["construction_touch_points"],
                builder=case["builder_workspace"]["construction_touch_points"],
                delta=case["delta"]["touch_points_reduced"],
                manual_trace=case["generic_harness"]["trace_count"],
                builder_trace=case["builder_workspace"]["trace_count"],
                source=case["builder_workspace"]["generated_by"],
            )
        )

    lines.extend(
        [
            "",
            "## 可放进 PPT 的结论",
            "",
            "Harness Engineering 可以解决 Agent 的运行结构问题，但它本身仍然要求开发者手动定义不同业务的 Agent、Tool、上下文、约束和验证规则。",
            "",
            "本项目的价值不是重新发明 Harness，而是把 Harness 思路上升为 Builder Workspace：通过业务 Template/Preset 生成可执行 Workflow JSON，并在多个领域保持同样的顺序执行和 Trace 验证结构。",
            "",
            "因此，面对“用 Harness Engineering 不就可以了吗”的问题，可以回答：",
            "",
            f"> Harness 是通用运行框架，本项目解决的是业务 Workflow 如何被模板化、生成、迁移和验证。实验中，同样两个任务下，Generic Harness 平均需要手动维护 {result['summary']['average_manual_touch_points']} 个构建触点，而 Builder Workspace 平均只需要 {result['summary']['average_builder_touch_points']} 个构建触点，就能生成标准 JSON 并执行 6 步 Trace。",
            "",
        ]
    )
    return "\n".join(lines)


def render_report_kr(result: dict[str, Any]) -> str:
    trace_equal = "예" if result["summary"]["all_cases_trace_count_equal"] else "아니오"
    lines = [
        "# Harness Engineering 대비 실험 결과",
        "",
        "## 실험 설계",
        "",
        "본 실험은 모델 성능 비교가 아니라 Workflow 구성 방식 비교입니다.",
        "두 방식 모두 같은 로컬 실행 엔진을 사용하고, 차이는 구성 단계에만 둡니다.",
        "",
        "- Generic Harness Engineering: Agent, Tool, Context/Memory, Constraints, Feedback Loop, Verification, Execution Environment를 수동 정의",
        "- Builder Workspace: 업무 Preset 선택 후 표준 Workflow JSON을 생성하고 Trace를 출력",
        "",
        "## 전체 결과",
        "",
        f"- 비교 업무 수: {result['summary']['case_count']}",
        f"- Builder Preset 수: {result['summary']['builder_presets_available']}",
        f"- Generic Harness 평균 구성 접점: {result['summary']['average_manual_touch_points']}",
        f"- Builder Workspace 평균 구성 접점: {result['summary']['average_builder_touch_points']}",
        f"- 평균 감소 접점: {result['summary']['average_touch_points_reduced']}",
        f"- 두 방식의 Trace 단계 수 동일 여부: {trace_equal}",
        "",
        "## 업무별 비교",
        "",
        "| 업무 | Generic Harness 구성 접점 | Builder Workspace 구성 접점 | 감소 | Generic Trace | Builder Trace | Builder 생성 출처 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for case in result["cases"]:
        lines.append(
            "| {title} | {manual} | {builder} | {delta} | {manual_trace} | {builder_trace} | {source} |".format(
                title=case["case_title_kr"],
                manual=case["generic_harness"]["construction_touch_points"],
                builder=case["builder_workspace"]["construction_touch_points"],
                delta=case["delta"]["touch_points_reduced"],
                manual_trace=case["generic_harness"]["trace_count"],
                builder_trace=case["builder_workspace"]["trace_count"],
                source=case["builder_workspace"]["generated_by"],
            )
        )

    lines.extend(
        [
            "",
            "## 발표용 결론",
            "",
            "Harness Engineering은 Agent 실행 구조를 단순화할 수 있지만, 업무별 Agent, Tool, Context, 제약조건, 검증 규칙은 여전히 직접 정의해야 합니다.",
            "",
            "본 프로젝트의 차별점은 Harness를 다시 만드는 것이 아니라, 업무 Workflow를 Template/Preset으로 정의하고 Builder Workspace에서 실행 가능한 Workflow JSON으로 생성한 뒤 여러 도메인에서 동일한 Trace 구조로 검증하는 것입니다.",
            "",
            "> Harness는 범용 실행 프레임워크이고, 저희 MVP는 업무 Workflow를 템플릿화하고 생성, 이전, 검증하는 Builder 구조를 구현한 것입니다.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    result = run_experiment(write_outputs=True)
    print("Harness comparison experiment completed.")
    print(f"Cases: {result['summary']['case_count']}")
    print(f"Average manual touch points: {result['summary']['average_manual_touch_points']}")
    print(f"Average builder touch points: {result['summary']['average_builder_touch_points']}")
    print(f"Outputs: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

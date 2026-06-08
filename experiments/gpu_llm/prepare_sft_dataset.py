import argparse
import json
from pathlib import Path


PROJECT_SUMMARIES = [
    {
        "instruction": "Explain what our project is in one paragraph.",
        "input": "Project: Template-based Multi-Agent Workflow Builder MVP. Domains: outfit recommendation, presentation planning, customer support routing.",
        "output": "This project is a template-based Multi-Agent Workflow Builder MVP. It uses reusable business templates to generate executable workflow JSON, then runs each workflow through a unified multi-node execution engine with trace verification. Outfit recommendation is only one sample workflow; the same builder structure also supports commute outfit recommendation, presentation planning, and customer support ticket routing.",
    },
    {
        "instruction": "Explain why this project is not just an outfit recommendation app.",
        "input": "Need a Korean answer for a project report.",
        "output": "본 프로젝트의 핵심은 의류 추천 App 자체가 아니라 템플릿 기반 Multi-Agent Workflow Builder MVP입니다. 의류 추천은 Builder가 생성하고 실행할 수 있는 대표 Sample Workflow이며, 동일한 구조는 통근 의류 추천, 발표 기획, 고객지원 티켓 분류 등 다른 업무에도 적용됩니다.",
    },
    {
        "instruction": "Differentiate a workflow builder from a simple chatbot.",
        "input": "Need 5 concise bullets.",
        "output": "1. A chatbot mainly replies to user messages, while a workflow builder executes a defined process. 2. A workflow builder separates nodes such as parser, question, tool, decision, and compose. 3. It can bind external tools and local data sources. 4. It produces traceable execution steps instead of only text. 5. Templates allow the same structure to be reused across domains.",
    },
    {
        "instruction": "Create a concise Korean explanation of the project.",
        "input": "Explain for a professor.",
        "output": "본 프로젝트는 단순 챗봇이 아니라, 여러 기능 Node로 구성된 Multi-Agent Workflow를 템플릿 기반으로 생성하고 실행하는 Builder MVP입니다. 사용자는 업무 Preset을 선택하고 입력을 제공하면, 시스템은 표준 Workflow JSON을 생성한 뒤 실행 Trace를 통해 각 Node의 역할과 결과를 검증합니다.",
    },
    {
        "instruction": "Create a Chinese explanation of the project.",
        "input": "Explain for teammates.",
        "output": "我们的项目不是单纯的聊天机器人，也不是只做穿搭推荐。它是一个基于模板的 Multi-Agent Workflow Builder MVP，可以把不同业务场景拆成固定节点，通过模板生成可执行 Workflow JSON，并用统一引擎运行和验证 Trace。",
    },
]


WORKFLOW_CASES = [
    {
        "name": "outfit_recommendation",
        "domain": "personalized outfit recommendation",
        "request": "다음 주 칭다오 여행 가는데 내 쇼핑 기록을 참고해서 옷을 추천해줘.",
        "nodes": ["Request Parser", "Question", "Weather Tool", "Shopping History Analysis", "Recommendation", "Compose"],
        "missing": "none",
        "data": "city=Qingdao, date=next week, purpose=travel, style=casual, shopping_history=user_a",
        "result": "ranked outfit recommendation with owned items, weather reason, and optional extra items",
    },
    {
        "name": "commute_outfit",
        "domain": "work commute outfit recommendation",
        "request": "내일 서울에 출근하는데 포멀한 느낌으로 입고 싶어.",
        "nodes": ["Request Parser", "Question", "Weather Tool", "User Profile", "Commute Rule", "Compose"],
        "missing": "none",
        "data": "city=Seoul, date=tomorrow, purpose=commute, style=formal, profile=user_b",
        "result": "formal commute outfit with weather-aware outerwear and ranked item list",
    },
    {
        "name": "presentation_planning",
        "domain": "presentation planning",
        "request": "다음 발표에서 우리 Builder MVP와 기존 도구의 차이를 설명해야 해.",
        "nodes": ["Request Parser", "Question", "Topic Analysis", "Knowledge Lookup", "Outline Generation", "Compose"],
        "missing": "presentation duration",
        "data": "topic=Builder MVP, evidence=harness comparison and GPU experiment, audience=professor",
        "result": "15-minute presentation outline with problem, method, demo, experiment, and future work",
    },
    {
        "name": "customer_support_ticket",
        "domain": "customer support ticket routing",
        "request": "배송 완료라고 나오는데 상품을 못 받았어요. 환불 가능한가요?",
        "nodes": ["Request Parser", "Question", "Intent Detection", "Policy Lookup", "Priority Routing", "Compose"],
        "missing": "order id",
        "data": "issue=delivery missing, refund question=yes, policy=support_policy.json",
        "result": "ticket category, priority, responsible team, missing information question, and response draft",
    },
]


QUESTION_CASES = [
    ("옷 추천해줘.", ["도시", "날짜", "목적/스타일"], "도시를 먼저 물어본 뒤 날짜와 목적/스타일을 확인한다."),
    ("내일 입을 옷 추천해줘.", ["도시", "목적/스타일"], "날짜는 있으므로 도시와 착용 목적을 물어본다."),
    ("서울에서 입을 옷 추천해줘.", ["날짜", "목적/스타일"], "도시는 있으므로 날짜와 목적/스타일을 물어본다."),
    ("다음 주 부산 여행 옷 추천해줘.", ["스타일"], "도시, 날짜, 목적은 충분하므로 선호 스타일만 확인한다."),
    ("발표 준비 도와줘.", ["발표 주제", "시간", "청중"], "발표 Workflow는 주제, 발표 시간, 청중을 우선 확인한다."),
    ("고객 문의 처리해줘.", ["문의 내용", "주문번호", "긴급도"], "고객지원 Workflow는 구체적 문의 내용과 주문번호를 먼저 확인한다."),
]


RECOMMENDATION_CONTEXTS = [
    {
        "weather": "서울, 내일 18도, 흐림, 강수확률 20%",
        "history": "검정 슬랙스, 흰 셔츠, 네이비 재킷, 회색 후드티, 운동화",
        "style": "깔끔한 캐주얼",
        "output": "1순위: 흰 셔츠 + 검정 슬랙스 + 네이비 재킷. 흐린 18도 날씨에 적당하고 깔끔한 인상을 준다. 2순위: 회색 후드티 + 검정 슬랙스 + 운동화. 편안하지만 너무 가볍지 않다. 3순위: 흰 셔츠 + 검정 슬랙스. 실내 일정이 많을 때 적합하다.",
    },
    {
        "weather": "칭다오, 다음 주 26도, 맑음, 강수확률 10%",
        "history": "흰 티셔츠, 베이지 치노팬츠, 데님 셔츠, 샌들, 얇은 셔츠",
        "style": "여행용 캐주얼",
        "output": "1순위: 흰 티셔츠 + 베이지 치노팬츠 + 얇은 셔츠. 26도 맑은 날씨와 여행 일정에 가장 적합하다. 2순위: 흰 티셔츠 + 데님 셔츠 + 치노팬츠. 사진 촬영과 이동에 모두 무난하다. 3순위: 흰 티셔츠 + 치노팬츠 + 샌들. 더운 낮 시간대에 적합하다.",
    },
    {
        "weather": "부산, 주말 12도, 비, 강수확률 70%",
        "history": "트렌치코트, 니트, 청바지, 방수 운동화, 검정 우산",
        "style": "차분한 데일리",
        "output": "1순위: 니트 + 청바지 + 트렌치코트 + 방수 운동화. 12도 비 날씨에 보온과 방수 모두 고려된다. 2순위: 니트 + 청바지 + 검정 우산. 외부 이동이 짧을 때 적합하다. 3순위: 트렌치코트 + 청바지. 실내 일정 중심일 때 선택할 수 있다.",
    },
]


PROFESSOR_QUESTIONS = [
    {
        "instruction": "Answer why Harness Engineering alone is not enough.",
        "input": "Professor asks: If Harness Engineering can solve it, why do we need your builder?",
        "output": "Harness Engineering is useful as a general execution structure, but developers still need to manually define roles, tools, context, constraints, verification rules, and execution order for every business case. Our Builder Workspace turns those repeated manual definitions into reusable domain templates and generates standardized executable workflow JSON. In our comparison, the generic harness path required 17 construction touch points, while Builder Workspace required 3.",
    },
    {
        "instruction": "Answer whether Flowise, Dify, or Langflow already solve the project.",
        "input": "Need Korean presentation answer.",
        "output": "저희는 Flowise, Dify, Langflow 같은 기존 Builder를 대체하려는 것이 아닙니다. 기존 도구는 범용 Workflow 제작에는 유용하지만, 추천 도메인에서 필요한 정보 보완, 쇼핑 이력 분석, 날씨 반영, 추천 우선순위화 같은 도메인 특화 Template은 별도로 정의해야 합니다. 본 프로젝트는 그 도메인 Workflow Template 구조를 설계하고 로컬 MVP로 검증합니다.",
    },
    {
        "instruction": "Answer why AI-generated separate agents are not enough.",
        "input": "Professor asks: Why not just ask AI to create each agent separately?",
        "output": "AI can generate code fragments, but separate generation does not guarantee consistent node interfaces, execution order, trace format, tool binding, or verification rules. Our Builder defines a stable workflow schema first, then generates or runs agents inside that schema. The value is consistency and reuse, not one-time code generation.",
    },
]


LOCAL_LLM_NODE_EXAMPLES = [
    {
        "instruction": "Summarize the value of Local LLM Node.",
        "input": "A100 experiment: Qwen2.5-1.5B base, 99 token/s, peak memory about 2.96GB.",
        "output": "The A100 experiment shows that Qwen2.5-1.5B can run locally with about 2.96GB peak GPU memory and 99 token/s generation speed. This is suitable for a stable Local LLM Compose Node or Workflow Explanation Node in the Builder MVP.",
    },
    {
        "instruction": "Summarize the value of Local LLM Node.",
        "input": "A100 experiment: Qwen2.5-7B base, 65 token/s, peak memory about 14.56GB.",
        "output": "The A100 experiment shows that Qwen2.5-7B can run locally with about 14.56GB peak GPU memory and 65 token/s generation speed. It is heavier than 1.5B but can be used as a higher-quality Local LLM candidate for reasoning or compose nodes.",
    },
    {
        "instruction": "Explain the LoRA experiment result honestly.",
        "input": "LoRA ran successfully but did not improve the average keyword score.",
        "output": "The LoRA adapter was successfully trained, loaded, and evaluated, so the technical integration is feasible. However, the current small SFT dataset did not improve the average keyword score over the base model. The correct conclusion is that LoRA is feasible but needs a larger and more diverse workflow-specific dataset.",
    },
    {
        "instruction": "Generate local LLM compose-node prompt.",
        "input": "Context contains workflow_name, user_query, tool_results, decision_result, ranked_items.",
        "output": "You are the Compose Node of a Multi-Agent Workflow. Use the structured workflow context, tool results, decision result, and ranked items to produce a concise final answer. Do not invent tool outputs. Explain the recommendation or decision in a practical way and preserve the ranking order from the workflow context.",
    },
]


def add(row_list: list[dict], instruction: str, input_text: str, output: str, category: str) -> None:
    row_list.append(
        {
            "instruction": instruction,
            "input": input_text,
            "output": output,
            "meta": {"category": category},
        }
    )


def workflow_outline(case: dict) -> str:
    node_text = " -> ".join(f"{name} Node" if not name.endswith("Node") else name for name in case["nodes"])
    return (
        f"Workflow: {node_text}. "
        f"The workflow handles the {case['domain']} domain. "
        f"Input data: {case['data']}. "
        f"Missing information: {case['missing']}. "
        f"Final result: {case['result']}."
    )


def workflow_trace(case: dict) -> str:
    steps = []
    for index, node in enumerate(case["nodes"], start=1):
        if "Parser" in node:
            detail = f"extracts domain, intent, and key fields from the request: {case['request']}"
        elif "Question" in node:
            detail = f"checks missing context and asks about {case['missing']} if needed"
        elif "Weather" in node:
            detail = "retrieves or normalizes weather context when the template requires weather"
        elif "Shopping" in node or "User Profile" in node:
            detail = "summarizes user-owned data and preference signals"
        elif "Policy" in node or "Knowledge" in node:
            detail = "retrieves domain rules or knowledge required for the decision"
        elif "Recommendation" in node or "Routing" in node or "Outline" in node:
            detail = "generates the ranked decision or structured intermediate result"
        else:
            detail = "renders the final user-facing answer and preserves trace evidence"
        steps.append(f"{index}. {node} Node {detail}.")
    return "Trace: " + " ".join(steps)


def generate_workflow_examples() -> list[dict]:
    rows: list[dict] = []
    for case in WORKFLOW_CASES:
        add(
            rows,
            f"Generate a workflow outline for {case['name']}.",
            f"User request: {case['request']}",
            workflow_outline(case),
            "workflow_decomposition",
        )
        add(
            rows,
            f"Generate a node trace for {case['name']}.",
            f"Template={case['name']}; request={case['request']}",
            workflow_trace(case),
            "workflow_trace",
        )
        add(
            rows,
            f"Explain the reusable template value of {case['name']}.",
            f"Domain={case['domain']}; nodes={', '.join(case['nodes'])}",
            (
                f"The {case['name']} template is reusable because it fixes the domain-specific node order, "
                f"input fields, missing-information policy, and final output type. Users do not need to redesign "
                f"the workflow from scratch; they select the template and provide a request."
            ),
            "template_value",
        )
        add(
            rows,
            f"Write a concise Korean project-report paragraph for {case['name']}.",
            f"Request={case['request']}; result={case['result']}",
            (
                f"{case['name']} Workflow는 사용자의 자연어 요청을 여러 Node로 분해하여 순차적으로 실행한다. "
                f"각 Node는 입력 분석, 정보 보완, 도구/데이터 조회, 판단, 최종 응답 생성을 담당하며, "
                f"실행 Trace를 통해 처리 과정을 검증할 수 있다."
            ),
            "korean_report",
        )
    return rows


def generate_question_examples() -> list[dict]:
    rows: list[dict] = []
    for request, missing_fields, expected in QUESTION_CASES:
        add(
            rows,
            "Generate Question Node follow-up questions.",
            f"User request: {request}; missing fields: {', '.join(missing_fields)}",
            (
                f"Question Node result: {expected} "
                f"Follow-up questions should be asked one at a time in priority order: "
                f"{' -> '.join(missing_fields)}."
            ),
            "question_node",
        )
        add(
            rows,
            "Explain why the workflow should stop before tool execution.",
            f"User request: {request}; missing fields: {', '.join(missing_fields)}",
            (
                "The workflow should short-circuit at the Question Node because required context is missing. "
                f"Running later nodes could call tools with incomplete inputs. The system should first ask about "
                f"{', '.join(missing_fields)} and resume the workflow only after the answer is provided."
            ),
            "question_short_circuit",
        )
    return rows


def generate_recommendation_examples() -> list[dict]:
    rows: list[dict] = []
    for item in RECOMMENDATION_CONTEXTS:
        add(
            rows,
            "Generate ranked outfit recommendations using weather and shopping history.",
            f"Weather: {item['weather']}\nShopping history: {item['history']}\nUser style: {item['style']}",
            item["output"],
            "recommendation_ranking",
        )
        add(
            rows,
            "Explain why ranked recommendation is better than a flat answer.",
            f"Weather: {item['weather']}; style={item['style']}",
            (
                "Ranked recommendation is better because it exposes the decision priority. "
                "The first item should fit the weather, user style, and owned wardrobe best; lower-ranked items "
                "serve as alternatives for different comfort or schedule conditions."
            ),
            "recommendation_reasoning",
        )
    return rows


def generate_core_examples() -> list[dict]:
    rows: list[dict] = []
    rows.extend(tag_examples(PROJECT_SUMMARIES, "project_identity"))
    rows.extend(tag_examples(PROFESSOR_QUESTIONS, "professor_answer"))
    rows.extend(tag_examples(LOCAL_LLM_NODE_EXAMPLES, "local_llm_node"))
    rows.extend(generate_workflow_examples())
    rows.extend(generate_question_examples())
    rows.extend(generate_recommendation_examples())
    return rows


def tag_examples(examples: list[dict], category: str) -> list[dict]:
    tagged = []
    for item in examples:
        row = dict(item)
        meta = dict(row.get("meta", {}))
        meta.setdefault("category", category)
        row["meta"] = meta
        tagged.append(row)
    return tagged


def expand_examples(base_examples: list[dict[str, str]], target_count: int, repeat: int) -> list[dict[str, str]]:
    rows = []
    rounds = 0
    while len(rows) < target_count:
        for item in base_examples:
            if len(rows) >= target_count:
                break
            row = dict(item)
            meta = dict(row.get("meta", {}))
            meta["synthetic_round"] = rounds
            row["meta"] = meta
            rows.append(row)
        rounds += 1
        if repeat and rounds >= repeat:
            break
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare SFT data for workflow-builder LoRA training.")
    parser.add_argument("--output", default="data/workflow_builder_sft.jsonl")
    parser.add_argument("--target-count", type=int, default=160, help="number of examples to write")
    parser.add_argument("--repeat", type=int, default=0, help="legacy option: stop after this many rounds")
    parser.add_argument("--summary", default="", help="optional path to write category counts")
    args = parser.parse_args()

    base_examples = generate_core_examples()
    rows = expand_examples(base_examples, args.target_count, args.repeat)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

    category_counts: dict[str, int] = {}
    for row in rows:
        category = row.get("meta", {}).get("category", "uncategorized")
        category_counts[category] = category_counts.get(category, 0) + 1

    summary = {
        "output": str(output),
        "base_unique_examples": len(base_examples),
        "written_examples": len(rows),
        "category_counts": category_counts,
    }
    if args.summary:
        summary_path = Path(args.summary)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from agent_builder.engine import AgentBuilderEngine, TraceStep
from agent_builder.local_llm import LocalLLMNode, LocalLLMNodeConfig
from agent_builder.node_registry import NodeExecutionResult, NodeRegistry
from agent_builder.shopping import analyze_shopping_history
from agent_builder.workflow_runtime import WorkflowRuntime
from agent_builder.workflow_schema import upgrade_workflow_config
from weather_agent.tools import CITY_ALIASES, WeatherTool


DEFAULT_PURPOSE_KEYWORDS = (
    "여행", "출장", "통학", "출근", "학교", "데이트", "행사", "휴가", "비즈니스", "쇼핑", "출퇴근",
)
DEFAULT_STYLE_KEYWORDS = (
    "캐주얼", "포멀", "스트릿", "미니멀", "스포티", "정장", "비즈니스",
)
DEFAULT_PURPOSE_KEYWORDS = DEFAULT_PURPOSE_KEYWORDS + (
    "travel", "trip", "tour", "commute", "work", "office", "business",
    "casual", "date", "旅行", "旅游", "通勤", "上班", "出差", "约会",
)
DEFAULT_STYLE_KEYWORDS = DEFAULT_STYLE_KEYWORDS + (
    "casual", "formal", "minimal", "business", "sporty", "street",
    "休闲", "正式", "极简", "商务", "运动", "街头",
)
DEFAULT_CLARIFICATION_MESSAGE = (
    "정보가 부족합니다. 여행 목적과 선호 스타일을 알려주세요. (예: 출장 / 캐주얼 등)"
)
DEFAULT_CLARIFICATION_QUESTIONS = {
    "city": "어느 도시나 여행지를 기준으로 추천할까요? (예: 서울, 칭다오)",
    "date": "언제 입을 옷인가요? (예: 내일, 다음 주)",
    "purpose_or_style": "여행/출근/데이트 같은 목적이나 캐주얼/포멀 같은 선호 스타일을 알려주세요.",
}
DATE_KEYWORDS = (
    "다음 주", "다음주", "next week",
    "모레", "day after tomorrow",
    "내일", "tomorrow",
    "오늘", "today",
)


@dataclass(frozen=True)
class WorkflowResult:
    workflow_name: str
    answer: str
    trace: list[TraceStep]
    context: dict[str, Any]


class MultiAgentWorkflowEngine:
    """Run Workflow JSON through a registry-backed sequential runtime."""

    def __init__(
        self,
        workflow_config_path: str | Path,
        data_dir: str | Path | None = None,
        weather_tool: WeatherTool | None = None,
        local_llm_config: dict[str, Any] | LocalLLMNodeConfig | None = None,
        registry: NodeRegistry | None = None,
    ):
        self.workflow_config_path = Path(workflow_config_path)
        self.workflow_config = upgrade_workflow_config(self._load_json(self.workflow_config_path))
        self.runtime_type = self.workflow_config.get("runtime_type", "outfit_recommendation")

        base_config_value = self.workflow_config.get("base_agent_config")
        if base_config_value:
            base_config = Path(base_config_value)
            if not base_config.is_absolute():
                base_config = self.workflow_config_path.parent / base_config
            self.base_engine = AgentBuilderEngine(
                base_config,
                data_dir=data_dir,
                weather_tool=weather_tool,
            )
            self.data_dir = self.base_engine.data_dir
            self.weather_tool = self.base_engine.weather_tool
        else:
            self.base_engine = None
            configured_data_dir = self.workflow_config.get("data_dir")
            if configured_data_dir:
                self.data_dir = Path(configured_data_dir)
            elif data_dir:
                self.data_dir = Path(data_dir)
            else:
                self.data_dir = self.workflow_config_path.parent.parent / "data"
            self.weather_tool = weather_tool or WeatherTool()

        configured_llm = local_llm_config or self.workflow_config.get("local_llm_node", {})
        self.local_llm_node = LocalLLMNode(configured_llm)
        self.registry = registry or self._build_registry()
        self.runtime = WorkflowRuntime(self.workflow_config, self.registry)

    def _build_registry(self) -> NodeRegistry:
        registry = NodeRegistry()
        handlers = {
            "request_parser": self._handle_outfit_request_parser,
            "question": self._handle_outfit_question,
            "weather": self._handle_outfit_weather,
            "shopping_analysis": self._handle_outfit_shopping_analysis,
            "recommendation": self._handle_outfit_recommendation,
            "compose": self._handle_outfit_compose,
            "presentation_request_parser": self._handle_presentation_request_parser,
            "presentation_question": self._handle_presentation_question,
            "topic_analysis": self._handle_topic_analysis,
            "knowledge_lookup": self._handle_knowledge_lookup,
            "outline_generation": self._handle_outline_generation,
            "presentation_compose": self._handle_presentation_compose,
            "support_request_parser": self._handle_support_request_parser,
            "support_question": self._handle_support_question,
            "ticket_classification": self._handle_ticket_classification,
            "policy_lookup": self._handle_policy_lookup,
            "routing_decision": self._handle_routing_decision,
            "support_compose": self._handle_support_compose,
        }
        for node_type, handler in handlers.items():
            registry.register(node_type, handler)
        return registry

    def run(self, user_message: str | None = None, user_id: str | None = None) -> WorkflowResult:
        query = (user_message or self.workflow_config.get("default_query") or "").strip()
        selected_user = user_id or self.workflow_config.get("default_user_id", "user_a")
        runtime_result = self.runtime.run(
            {
                "query": query,
                "user_id": selected_user,
                "runtime_type": self.runtime_type,
                "workflow_name": self.workflow_config.get("workflow_name", ""),
            }
        )
        context = runtime_result.context
        trace = runtime_result.trace
        if runtime_result.failed_node:
            answer = f"Workflow failed at node '{runtime_result.failed_node}': {runtime_result.error}"
        else:
            answer = str(context.get("final_answer") or context.get("clarification_message") or "")
            answer = self._maybe_run_local_llm_node(trace, context, answer)
        return self._finalize(trace, context, answer)

    def _finalize(
        self,
        trace: list[TraceStep],
        context: dict[str, Any],
        answer: str,
    ) -> WorkflowResult:
        context["workflow_name"] = self.workflow_config["workflow_name"]
        context["workflow_agents"] = self.workflow_config.get("agents", [])
        context["workflow_nodes"] = self.workflow_config.get("nodes", [])
        context["workflow_execution"] = self.workflow_config.get("execution", {})
        return WorkflowResult(
            workflow_name=self.workflow_config["workflow_name"],
            answer=answer,
            trace=trace,
            context=context,
        )

    # Outfit handlers -----------------------------------------------------

    def _handle_outfit_request_parser(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        if self.base_engine is None:
            raise ValueError("outfit workflow requires base_agent_config")
        inputs = node_config["inputs"]
        parsed = self.base_engine._plan(
            str(inputs["user_message"]),
            str(inputs["user_id"]),
        )
        return NodeExecutionResult(
            outputs=parsed,
            detail=(
                f"city={parsed['city_display']}, date={parsed['date_label']}, "
                f"user={parsed['user_id']}"
            ),
            data={
                "workflow": str(self.workflow_config_path),
                "base_config": str(self.base_engine.config_path),
                "intent": self.base_engine.config.get("intent"),
                "matched_keywords": parsed["matched_keywords"],
            },
        )

    def _handle_outfit_question(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        question_config = self.workflow_config.get("question_agent", {})
        purpose_keywords = list(DEFAULT_PURPOSE_KEYWORDS) + list(
            question_config.get("purpose_keywords", [])
        )
        style_keywords = list(DEFAULT_STYLE_KEYWORDS) + list(
            question_config.get("style_keywords", [])
        )
        query = str(node_config["inputs"].get("query", context["query"]))
        lower = query.lower()
        detected_purpose = [kw for kw in purpose_keywords if kw.lower() in lower]
        detected_style = [kw for kw in style_keywords if kw.lower() in lower]
        missing_fields = self._find_missing_context(lower, detected_purpose, detected_style)
        next_question_field = missing_fields[0] if missing_fields else ""
        clarification_questions = {
            **DEFAULT_CLARIFICATION_QUESTIONS,
            **question_config.get("clarification_questions", {}),
        }
        clarification_message = (
            clarification_questions.get(next_question_field, question_config.get("clarification_message"))
            if missing_fields
            else ""
        )
        outputs = {
            "detected_purpose": detected_purpose,
            "detected_style": detected_style,
            "missing_fields": missing_fields,
            "next_question_field": next_question_field,
            "needs_clarification": bool(missing_fields),
            "clarification_message": clarification_message,
        }
        if missing_fields:
            detail = f"missing={', '.join(missing_fields)} → {next_question_field} 질문"
        else:
            detail = (
                f"purpose={', '.join(detected_purpose) or '(없음)'}, "
                f"style={', '.join(detected_style) or '(없음)'} → 정보 충분"
            )
        return NodeExecutionResult(
            outputs=outputs,
            detail=detail,
            data=outputs,
            halt=bool(missing_fields),
            halt_reason="clarification" if missing_fields else "",
        )

    def _handle_outfit_weather(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        inputs = node_config["inputs"]
        weather = self.weather_tool.get_daily_weather(
            str(inputs["city_query"]),
            int(inputs["day_offset"]),
        )
        summary = {
            "date": weather.date,
            "condition": weather.condition,
            "temp_min": weather.temp_min,
            "temp_max": weather.temp_max,
            "precipitation_probability": weather.precipitation_probability,
        }
        context["executed_tools"].append("weather")
        return NodeExecutionResult(
            outputs={"weather": weather, "weather_summary": summary},
            detail=(
                f"{context['city_display']} {context['date_label']} weather loaded: "
                f"{weather.condition}"
            ),
            data=summary,
        )

    def _handle_outfit_shopping_analysis(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        if self.base_engine is None:
            raise ValueError("shopping analysis requires base_agent_config")
        tools = self.base_engine.config.get("tools", {})
        filename = tools.get("shopping_history", {}).get("file", "shopping_history.json")
        records = self._load_json(self.data_dir / filename)
        user_id = str(node_config["inputs"]["user_id"])
        shopping_items = records.get(user_id)
        if shopping_items is None:
            raise ValueError(f"unknown user_id: {user_id}")

        analysis = analyze_shopping_history(shopping_items)
        history_summary = {
            "records": len(shopping_items),
            "source": filename,
            "sample_items": [item.get("item") for item in shopping_items[:3]],
        }
        analysis_summary = {
            "total_items": analysis["total_items"],
            "top_styles": analysis["top_styles"],
            "top_colors": analysis["top_colors"],
            "top_categories": analysis["top_categories"],
            "favorite_items": analysis["favorite_items"],
        }
        context["executed_tools"].append("shopping_history")
        return NodeExecutionResult(
            outputs={
                "shopping_history": shopping_items,
                "shopping_history_summary": history_summary,
                "shopping_analysis": analysis,
                "shopping_item_count": analysis["total_items"],
                "styles_text": ", ".join(analysis["top_styles"]),
                "colors_text": ", ".join(analysis["top_colors"]),
                "favorite_items_text": ", ".join(analysis["favorite_items"]),
                "top_categories_text": ", ".join(analysis["top_categories"]),
                "user_name": user_id,
                "shopping_analysis_summary": analysis_summary,
            },
            detail=(
                f"styles={', '.join(analysis['top_styles'])}, "
                f"colors={', '.join(analysis['top_colors'])}, records={analysis['total_items']}"
            ),
            data=analysis_summary,
        )

    def _handle_outfit_recommendation(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        if self.base_engine is None:
            raise ValueError("recommendation requires base_agent_config")
        working = dict(context)
        working["weather"] = node_config["inputs"]["weather"]
        working["shopping_analysis"] = node_config["inputs"]["shopping_analysis"]
        self.base_engine._decide(working)
        output_names = (
            "avg_temp", "temp_min", "temp_max", "weather_date", "weather_condition",
            "precipitation_probability", "matched_rule_name", "recommendation",
            "owned_recommended_items", "owned_recommended_items_text", "additional_items",
            "additional_items_text", "recommended_items", "recommended_items_text",
            "ranked_items", "ranked_items_text", "extras", "extras_text",
        )
        outputs = {name: working[name] for name in output_names}
        return NodeExecutionResult(
            outputs=outputs,
            detail=f"rule={working['matched_rule_name']}, items={len(working['recommended_items'])}",
            data={
                "avg_temp": working["avg_temp"],
                "recommended_items": working["recommended_items"],
                "ranked_items": working.get("ranked_items", []),
                "extras": working["extras"],
            },
        )

    def _handle_outfit_compose(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        if self.base_engine is None:
            raise ValueError("compose requires base_agent_config")
        working = dict(context)
        working["recommendation"] = node_config["inputs"].get(
            "recommendation", working.get("recommendation")
        )
        working["ranked_items"] = node_config["inputs"].get(
            "ranked_items", working.get("ranked_items")
        )
        return NodeExecutionResult(
            outputs={"final_answer": self.base_engine._render(working)},
            detail="final response rendered from output_template",
            data={
                "template_id": self.base_engine.config.get("agent_id"),
                "workflow_id": self.workflow_config.get("workflow_id"),
            },
        )

    # Presentation handlers ----------------------------------------------

    def _handle_presentation_request_parser(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        topic = str(node_config["inputs"].get("user_message", context["query"]))
        duration = self._extract_duration_minutes(topic, default=15)
        outputs = {
            "topic": topic,
            "duration_minutes": duration,
            "output_type": "presentation_outline",
        }
        return NodeExecutionResult(
            outputs=outputs,
            detail=f"topic extracted, duration={duration} minutes",
            data=outputs,
        )

    def _handle_presentation_question(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        topic = node_config["inputs"].get("topic", context.get("topic"))
        missing = ["topic"] if not topic else []
        question = (
            self.workflow_config.get("question_agent", {})
            .get("clarification_questions", {})
            .get("topic", "Please provide the presentation topic.")
        )
        outputs = {
            "missing_fields": missing,
            "needs_clarification": bool(missing),
            "next_question_field": "topic" if missing else "",
            "clarification_message": question if missing else "",
        }
        return NodeExecutionResult(
            outputs=outputs,
            detail="topic missing" if missing else "presentation context is complete",
            data=outputs,
            halt=bool(missing),
            halt_reason="clarification" if missing else "",
        )

    def _handle_topic_analysis(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        knowledge = self._load_runtime_data()
        topic = str(node_config["inputs"]["topic"])
        matched_topics = self._match_knowledge_topics(topic, knowledge)
        goal = "Build a defensible presentation outline from local knowledge notes."
        return NodeExecutionResult(
            outputs={"matched_topics": matched_topics, "planning_goal": goal},
            detail="matched topics: " + ", ".join(self._topic_titles(matched_topics)),
            data={
                "matched_topic_ids": [topic["id"] for topic in matched_topics],
                "planning_goal": goal,
            },
        )

    def _handle_knowledge_lookup(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        knowledge_points: list[str] = []
        slide_suggestions: list[str] = []
        matched_topics = node_config["inputs"].get("matched_topics", [])
        for topic in matched_topics:
            knowledge_points.extend(topic.get("points", [])[:2])
            slide_suggestions.extend(topic.get("slide_suggestions", [])[:2])
        context["executed_tools"].append("presentation_knowledge")
        return NodeExecutionResult(
            outputs={
                "knowledge_points": knowledge_points,
                "slide_suggestions": slide_suggestions,
            },
            detail=f"loaded {len(knowledge_points)} knowledge points from local notes",
            data={
                "knowledge_points": knowledge_points,
                "slide_suggestions": slide_suggestions,
                "source": self.workflow_config.get("data_file"),
            },
        )

    def _handle_outline_generation(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        working = dict(context)
        working["knowledge_points"] = node_config["inputs"].get("knowledge_points", [])
        working["duration_minutes"] = node_config["inputs"].get(
            "duration_minutes", working.get("duration_minutes", 15)
        )
        working["planning_goal"] = node_config["inputs"].get(
            "planning_goal", working.get("planning_goal", "")
        )
        outline_sections = self._build_presentation_outline(working)
        speaker_focus = [
            "Position the project as a workflow builder, not as a single recommendation feature.",
            "Use multiple domains to prove template portability.",
            "Show trace output as executable evidence.",
        ]
        return NodeExecutionResult(
            outputs={"outline_sections": outline_sections, "speaker_focus": speaker_focus},
            detail=f"generated {len(outline_sections)} outline sections",
            data={"outline_sections": outline_sections, "speaker_focus": speaker_focus},
        )

    def _handle_presentation_compose(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        working = dict(context)
        working["outline_sections"] = node_config["inputs"].get(
            "outline_sections", working.get("outline_sections", [])
        )
        working["knowledge_points"] = node_config["inputs"].get(
            "knowledge_points", working.get("knowledge_points", [])
        )
        working["speaker_focus"] = node_config["inputs"].get(
            "speaker_focus", working.get("speaker_focus", [])
        )
        answer = self._render_presentation_answer(working)
        summary_cards = [
            {
                "title": "Presentation Topic",
                "rows": [
                    {"label": "Duration", "value": f"{working['duration_minutes']} minutes"},
                    {"label": "Matched Topics", "value": ", ".join(self._topic_titles(working.get("matched_topics", [])))},
                ],
            },
            {
                "title": "Knowledge Evidence",
                "rows": [
                    {"label": "Points", "value": str(len(working["knowledge_points"]))},
                    {"label": "Trace", "value": "6 nodes executed"},
                ],
            },
            {
                "title": "Outline Result",
                "rows": [
                    {"label": str(i + 1), "value": section}
                    for i, section in enumerate(working["outline_sections"][:4])
                ],
            },
        ]
        return NodeExecutionResult(
            outputs={"final_answer": answer, "summary_cards": summary_cards},
            detail="final presentation outline rendered",
            data={"summary_cards": summary_cards},
        )

    # Customer support handlers ------------------------------------------

    def _handle_support_request_parser(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        issue_text = str(node_config["inputs"].get("user_message", context["query"]))
        intent = self._detect_support_intent(issue_text)
        outputs = {"issue_text": issue_text, "intent": intent}
        return NodeExecutionResult(
            outputs=outputs,
            detail=f"support intent={intent}",
            data=outputs,
        )

    def _handle_support_question(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        issue_text = node_config["inputs"].get("issue_text", context.get("issue_text"))
        missing = ["issue_text"] if not issue_text else []
        question = (
            self.workflow_config.get("question_agent", {})
            .get("clarification_questions", {})
            .get("issue_text", "Please describe the customer issue.")
        )
        outputs = {
            "missing_fields": missing,
            "needs_clarification": bool(missing),
            "next_question_field": "issue_text" if missing else "",
            "clarification_message": question if missing else "",
        }
        return NodeExecutionResult(
            outputs=outputs,
            detail="issue text missing" if missing else "ticket context is complete",
            data=outputs,
            halt=bool(missing),
            halt_reason="clarification" if missing else "",
        )

    def _handle_ticket_classification(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        policy_data = self._load_runtime_data()
        issue_text = str(node_config["inputs"]["issue_text"])
        category, matched_keywords = self._classify_support_ticket(issue_text, policy_data)
        outputs = {
            "ticket_category_record": category,
            "ticket_category": category["label"],
            "ticket_category_id": category["id"],
            "matched_keywords": matched_keywords,
            "priority_candidate": category["priority"],
        }
        return NodeExecutionResult(
            outputs=outputs,
            detail=f"category={category['label']}, matched={', '.join(matched_keywords) or 'default'}",
            data={
                "category": category["label"],
                "priority_candidate": category["priority"],
                "matched_keywords": matched_keywords,
            },
        )

    def _handle_policy_lookup(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        category = node_config["inputs"].get("category", context["ticket_category_record"])
        outputs = {
            "policy": category["policy"],
            "sla": category["sla"],
            "owner_team": category["owner_team"],
        }
        context["executed_tools"].append("support_policy")
        return NodeExecutionResult(
            outputs=outputs,
            detail=f"loaded policy for {category['label']}",
            data={**outputs, "source": self.workflow_config.get("data_file")},
        )

    def _handle_routing_decision(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        category = node_config["inputs"].get("category", context["ticket_category_record"])
        policy = node_config["inputs"].get("policy", context["policy"])
        outputs = {
            "priority": category["priority"],
            "next_actions": category["next_actions"],
        }
        return NodeExecutionResult(
            outputs=outputs,
            detail=f"route to {context['owner_team']} with priority {outputs['priority']}",
            data={"owner_team": context["owner_team"], "policy": policy, **outputs},
        )

    def _handle_support_compose(
        self, context: dict[str, Any], node_config: dict[str, Any]
    ) -> NodeExecutionResult:
        working = dict(context)
        for key in ("owner_team", "priority", "next_actions", "policy"):
            if key in node_config["inputs"]:
                working[key] = node_config["inputs"][key]
        answer = self._render_support_answer(working)
        summary_cards = [
            {
                "title": "Ticket Classification",
                "rows": [
                    {"label": "Category", "value": context["ticket_category"]},
                    {"label": "Intent", "value": context["intent"]},
                ],
            },
            {
                "title": "Routing Decision",
                "rows": [
                    {"label": "Owner", "value": context["owner_team"]},
                    {"label": "Priority", "value": context["priority"]},
                    {"label": "SLA", "value": context["sla"]},
                ],
            },
            {
                "title": "Next Actions",
                "rows": [
                    {"label": str(i + 1), "value": action}
                    for i, action in enumerate(context["next_actions"])
                ],
            },
        ]
        return NodeExecutionResult(
            outputs={"final_answer": answer, "summary_cards": summary_cards},
            detail="support ticket response rendered",
            data={"summary_cards": summary_cards},
        )

    # Shared helpers ------------------------------------------------------

    def _find_missing_context(
        self,
        lower: str,
        detected_purpose: list[str],
        detected_style: list[str],
    ) -> list[str]:
        missing_fields = []
        if not any(alias in lower for alias in CITY_ALIASES):
            missing_fields.append("city")
        if not any(keyword in lower for keyword in DATE_KEYWORDS):
            missing_fields.append("date")
        if not detected_purpose and not detected_style:
            missing_fields.append("purpose_or_style")
        return missing_fields

    def _extract_duration_minutes(self, query: str, default: int) -> int:
        for token in query.replace("-", " ").split():
            cleaned = "".join(ch for ch in token if ch.isdigit())
            if cleaned:
                value = int(cleaned)
                if 1 <= value <= 180:
                    return value
        return default

    def _load_runtime_data(self) -> dict[str, Any]:
        data_file = self.workflow_config.get("data_file")
        if not data_file:
            raise ValueError(f"{self.runtime_type} workflow requires data_file")
        return self._load_json(self.data_dir / data_file)

    def _match_knowledge_topics(
        self,
        query: str,
        knowledge: dict[str, Any],
    ) -> list[dict[str, Any]]:
        lower = query.lower()
        scored = []
        for topic in knowledge.get("topics", []):
            keywords = topic.get("keywords", [])
            score = sum(1 for keyword in keywords if keyword.lower() in lower)
            if score:
                scored.append((score, topic))
        if scored:
            return [topic for _, topic in sorted(scored, key=lambda item: item[0], reverse=True)[:3]]

        default_ids = set(knowledge.get("default_topic_ids", []))
        defaults = [topic for topic in knowledge.get("topics", []) if topic.get("id") in default_ids]
        return defaults or list(knowledge.get("topics", []))[:2]

    @staticmethod
    def _topic_titles(topics: list[Any]) -> list[str]:
        return [topic.get("title", "") if isinstance(topic, dict) else str(topic) for topic in topics]

    def _build_presentation_outline(self, context: dict[str, Any]) -> list[str]:
        matched = ", ".join(self._topic_titles(context.get("matched_topics", [])))
        return [
            f"Opening: define the presentation topic and why {matched} matters.",
            "Problem: explain why a single-domain MVP is not enough to prove a builder.",
            "Architecture: show Template -> Workflow JSON -> Multi-Agent Engine -> Trace.",
            "Multi-domain evidence: compare recommendation, presentation planning and support ticket workflows.",
            "Conclusion: position the current semester as the executable foundation for next semester.",
        ]

    def _render_presentation_answer(self, context: dict[str, Any]) -> str:
        lines = [
            "[Presentation Planning Workflow]",
            f"Topic: {context['topic']}",
            f"Duration: {context['duration_minutes']} minutes",
            "Matched knowledge: " + ", ".join(self._topic_titles(context.get("matched_topics", []))),
            "",
            "Outline",
        ]
        lines.extend(f"{index}. {section}" for index, section in enumerate(context["outline_sections"], start=1))
        lines.append("")
        lines.append("Key evidence")
        lines.extend(f"- {point}" for point in context.get("knowledge_points", [])[:5])
        lines.append("")
        lines.append("Trace proof: this outline was produced by a 6-node generated workflow.")
        return "\n".join(lines)

    @staticmethod
    def _detect_support_intent(query: str) -> str:
        lower = query.lower()
        if any(word in lower for word in ("refund", "return", "cancel", "money back")):
            return "refund_or_return"
        if any(word in lower for word in ("late", "delivery", "shipping", "tracking")):
            return "delivery_status"
        if any(word in lower for word in ("login", "password", "account", "locked")):
            return "account_access"
        return "technical_help"

    @staticmethod
    def _classify_support_ticket(
        query: str,
        policy_data: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        lower = query.lower()
        best_category: dict[str, Any] | None = None
        best_keywords: list[str] = []
        for category in policy_data.get("categories", []):
            matched = [keyword for keyword in category.get("keywords", []) if keyword.lower() in lower]
            if len(matched) > len(best_keywords):
                best_category = category
                best_keywords = matched

        if best_category is not None:
            return best_category, best_keywords

        default_id = policy_data.get("default_category")
        for category in policy_data.get("categories", []):
            if category.get("id") == default_id:
                return category, []
        return policy_data["categories"][0], []

    @staticmethod
    def _render_support_answer(context: dict[str, Any]) -> str:
        lines = [
            "[Customer Support Ticket Workflow]",
            f"Category: {context['ticket_category']}",
            f"Intent: {context['intent']}",
            f"Owner team: {context['owner_team']}",
            f"Priority: {context['priority']} / SLA: {context['sla']}",
            "",
            "Policy basis:",
            context["policy"],
            "",
            "Next actions",
        ]
        lines.extend(f"{index}. {action}" for index, action in enumerate(context["next_actions"], start=1))
        lines.append("")
        lines.append(
            "Response draft: We have classified the issue and routed it to "
            f"{context['owner_team']} for follow-up."
        )
        return "\n".join(lines)

    def _maybe_run_local_llm_node(
        self,
        trace: list[TraceStep],
        context: dict[str, Any],
        answer: str,
    ) -> str:
        if not self.local_llm_node.enabled:
            return answer

        context["workflow_name"] = self.workflow_config["workflow_name"]
        started_at = datetime.now(timezone.utc).isoformat()
        started = perf_counter()
        result = self.local_llm_node.run(context)
        finished_at = datetime.now(timezone.utc).isoformat()
        context["local_llm"] = {
            "provider": result.provider,
            "model": result.model,
            "metrics": result.metrics,
        }
        context["local_llm_prompt"] = result.prompt
        context["executed_agents"].append("local_llm")
        trace.append(
            TraceStep(
                name="Local LLM Node",
                detail=f"{result.provider} provider executed with model={result.model}",
                data=context["local_llm"],
                node_id="local_llm",
                node_type="local_llm",
                status="SUCCESS",
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=round((perf_counter() - started) * 1000, 3),
                input={"workflow_name": self.workflow_config["workflow_name"]},
                output={"provider": result.provider, "model": result.model},
            )
        )
        return answer + "\n\n" + result.text

    def _load_json(self, path: Path) -> Any:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

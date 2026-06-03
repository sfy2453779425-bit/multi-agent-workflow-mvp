import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_builder.engine import AgentBuilderEngine, TraceStep
from agent_builder.shopping import analyze_shopping_history
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
    """Runs a configured sequential workflow made of small Agent steps."""

    def __init__(
        self,
        workflow_config_path: str | Path,
        data_dir: str | Path | None = None,
        weather_tool: WeatherTool | None = None,
    ):
        self.workflow_config_path = Path(workflow_config_path)
        self.workflow_config = self._load_json(self.workflow_config_path)
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
        else:
            self.base_engine = None
            configured_data_dir = self.workflow_config.get("data_dir")
            if configured_data_dir:
                self.data_dir = Path(configured_data_dir)
            elif data_dir:
                self.data_dir = Path(data_dir)
            else:
                self.data_dir = self.workflow_config_path.parent.parent / "data"

    def run(self, user_message: str | None = None, user_id: str | None = None) -> WorkflowResult:
        query = (user_message or self.workflow_config.get("default_query") or "").strip()
        selected_user = user_id or self.workflow_config.get("default_user_id", "user_a")

        if self.runtime_type == "presentation_planning":
            return self._run_presentation_planning(query, selected_user)
        if self.runtime_type == "customer_support":
            return self._run_customer_support(query, selected_user)

        if self.base_engine is None:
            raise ValueError("outfit workflow requires base_agent_config")

        trace: list[TraceStep] = []
        context = self._run_request_parser(query, selected_user)
        trace.append(self._trace_request_parser(context))

        self._run_question_agent(context)
        trace.append(self._trace_question(context))

        if context.get("needs_clarification"):
            return self._finalize(
                trace,
                context,
                answer=context["clarification_message"],
            )

        self._run_weather_agent(context)
        trace.append(self._trace_weather(context))

        self._run_shopping_analysis_agent(context)
        trace.append(self._trace_shopping(context))

        self.base_engine._decide(context)
        context["executed_agents"].append("recommendation")
        trace.append(self._trace_recommendation(context))

        answer = self.base_engine._render(context)
        context["executed_agents"].append("compose")
        trace.append(self._trace_compose(context))

        return self._finalize(trace, context, answer=answer)

    def _run_presentation_planning(self, query: str, user_id: str) -> WorkflowResult:
        trace: list[TraceStep] = []
        context: dict[str, Any] = {
            "query": query,
            "user_id": user_id,
            "runtime_type": self.runtime_type,
            "executed_agents": [],
            "executed_tools": [],
        }

        context["topic"] = query
        context["duration_minutes"] = self._extract_duration_minutes(query, default=15)
        context["output_type"] = "presentation_outline"
        context["executed_agents"].append("request_parser")
        trace.append(
            self._runtime_trace(
                "request_parser",
                f"topic extracted, duration={context['duration_minutes']} minutes",
                {
                    "topic": context["topic"],
                    "duration_minutes": context["duration_minutes"],
                    "output_type": context["output_type"],
                },
            )
        )

        context["missing_fields"] = [] if context["topic"] else ["topic"]
        context["needs_clarification"] = bool(context["missing_fields"])
        context["next_question_field"] = "topic" if context["needs_clarification"] else ""
        context["clarification_message"] = (
            self.workflow_config.get("question_agent", {})
            .get("clarification_questions", {})
            .get("topic", "Please provide the presentation topic.")
        )
        context["executed_agents"].append("question")
        trace.append(
            self._runtime_trace(
                "question",
                "topic missing" if context["needs_clarification"] else "presentation context is complete",
                {
                    "missing_fields": context["missing_fields"],
                    "needs_clarification": context["needs_clarification"],
                },
            )
        )
        if context["needs_clarification"]:
            return self._finalize(trace, context, answer=context["clarification_message"])

        knowledge = self._load_runtime_data()
        matched_topics = self._match_knowledge_topics(query, knowledge)
        context["matched_topics"] = [topic["title"] for topic in matched_topics]
        context["planning_goal"] = "Build a defensible presentation outline from local knowledge notes."
        context["executed_agents"].append("topic_analysis")
        trace.append(
            self._runtime_trace(
                "topic_analysis",
                "matched topics: " + ", ".join(context["matched_topics"]),
                {
                    "matched_topic_ids": [topic["id"] for topic in matched_topics],
                    "planning_goal": context["planning_goal"],
                },
            )
        )

        knowledge_points = []
        slide_suggestions = []
        for topic in matched_topics:
            knowledge_points.extend(topic.get("points", [])[:2])
            slide_suggestions.extend(topic.get("slide_suggestions", [])[:2])
        context["knowledge_points"] = knowledge_points
        context["slide_suggestions"] = slide_suggestions
        context["executed_agents"].append("knowledge_lookup")
        context["executed_tools"].append("presentation_knowledge")
        trace.append(
            self._runtime_trace(
                "knowledge_lookup",
                f"loaded {len(knowledge_points)} knowledge points from local notes",
                {
                    "knowledge_points": knowledge_points,
                    "slide_suggestions": slide_suggestions,
                    "source": self.workflow_config.get("data_file"),
                },
            )
        )

        outline_sections = self._build_presentation_outline(context)
        context["outline_sections"] = outline_sections
        context["speaker_focus"] = [
            "Position the project as a workflow builder, not as a single recommendation feature.",
            "Use multiple domains to prove template portability.",
            "Show trace output as executable evidence.",
        ]
        context["executed_agents"].append("outline_generation")
        trace.append(
            self._runtime_trace(
                "outline_generation",
                f"generated {len(outline_sections)} outline sections",
                {
                    "outline_sections": outline_sections,
                    "speaker_focus": context["speaker_focus"],
                },
            )
        )

        answer = self._render_presentation_answer(context)
        context["summary_cards"] = [
            {
                "title": "Presentation Topic",
                "rows": [
                    {"label": "Duration", "value": f"{context['duration_minutes']} minutes"},
                    {"label": "Matched Topics", "value": ", ".join(context["matched_topics"])},
                ],
            },
            {
                "title": "Knowledge Evidence",
                "rows": [
                    {"label": "Points", "value": str(len(context["knowledge_points"]))},
                    {"label": "Trace", "value": "6 nodes executed"},
                ],
            },
            {
                "title": "Outline Result",
                "rows": [
                    {"label": str(i + 1), "value": section}
                    for i, section in enumerate(context["outline_sections"][:4])
                ],
            },
        ]
        context["executed_agents"].append("compose")
        trace.append(
            self._runtime_trace(
                "compose",
                "final presentation outline rendered",
                {"summary_cards": context["summary_cards"]},
            )
        )
        return self._finalize(trace, context, answer=answer)

    def _run_customer_support(self, query: str, user_id: str) -> WorkflowResult:
        trace: list[TraceStep] = []
        context: dict[str, Any] = {
            "query": query,
            "user_id": user_id,
            "runtime_type": self.runtime_type,
            "issue_text": query,
            "executed_agents": [],
            "executed_tools": [],
        }

        context["intent"] = self._detect_support_intent(query)
        context["executed_agents"].append("request_parser")
        trace.append(
            self._runtime_trace(
                "request_parser",
                f"support intent={context['intent']}",
                {"issue_text": context["issue_text"], "intent": context["intent"]},
            )
        )

        context["missing_fields"] = [] if context["issue_text"] else ["issue_text"]
        context["needs_clarification"] = bool(context["missing_fields"])
        context["next_question_field"] = "issue_text" if context["needs_clarification"] else ""
        context["clarification_message"] = (
            self.workflow_config.get("question_agent", {})
            .get("clarification_questions", {})
            .get("issue_text", "Please describe the customer issue.")
        )
        context["executed_agents"].append("question")
        trace.append(
            self._runtime_trace(
                "question",
                "issue text missing" if context["needs_clarification"] else "ticket context is complete",
                {
                    "missing_fields": context["missing_fields"],
                    "needs_clarification": context["needs_clarification"],
                },
            )
        )
        if context["needs_clarification"]:
            return self._finalize(trace, context, answer=context["clarification_message"])

        policy_data = self._load_runtime_data()
        category, matched_keywords = self._classify_support_ticket(query, policy_data)
        context["ticket_category"] = category["label"]
        context["ticket_category_id"] = category["id"]
        context["matched_keywords"] = matched_keywords
        context["priority_candidate"] = category["priority"]
        context["executed_agents"].append("ticket_classification")
        trace.append(
            self._runtime_trace(
                "ticket_classification",
                f"category={context['ticket_category']}, matched={', '.join(matched_keywords) or 'default'}",
                {
                    "category": context["ticket_category"],
                    "priority_candidate": context["priority_candidate"],
                    "matched_keywords": matched_keywords,
                },
            )
        )

        context["policy"] = category["policy"]
        context["sla"] = category["sla"]
        context["owner_team"] = category["owner_team"]
        context["executed_agents"].append("policy_lookup")
        context["executed_tools"].append("support_policy")
        trace.append(
            self._runtime_trace(
                "policy_lookup",
                f"loaded policy for {context['ticket_category']}",
                {
                    "owner_team": context["owner_team"],
                    "sla": context["sla"],
                    "policy": context["policy"],
                    "source": self.workflow_config.get("data_file"),
                },
            )
        )

        context["priority"] = category["priority"]
        context["next_actions"] = category["next_actions"]
        context["executed_agents"].append("routing_decision")
        trace.append(
            self._runtime_trace(
                "routing_decision",
                f"route to {context['owner_team']} with priority {context['priority']}",
                {
                    "owner_team": context["owner_team"],
                    "priority": context["priority"],
                    "next_actions": context["next_actions"],
                },
            )
        )

        answer = self._render_support_answer(context)
        context["summary_cards"] = [
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
        context["executed_agents"].append("compose")
        trace.append(
            self._runtime_trace(
                "compose",
                "support ticket response rendered",
                {"summary_cards": context["summary_cards"]},
            )
        )
        return self._finalize(trace, context, answer=answer)

    def _finalize(
        self,
        trace: list[TraceStep],
        context: dict[str, Any],
        answer: str,
    ) -> WorkflowResult:
        context["workflow_name"] = self.workflow_config["workflow_name"]
        context["workflow_agents"] = self.workflow_config.get("agents", [])
        context["workflow_execution"] = self.workflow_config.get("execution", {})
        return WorkflowResult(
            workflow_name=self.workflow_config["workflow_name"],
            answer=answer,
            trace=trace,
            context=context,
        )

    def _run_request_parser(self, query: str, user_id: str) -> dict[str, Any]:
        context = self.base_engine._plan(query, user_id)
        context["executed_agents"] = ["request_parser"]
        context["executed_tools"] = []
        return context

    def _run_question_agent(self, context: dict[str, Any]) -> None:
        question_config = self.workflow_config.get("question_agent", {})
        purpose_keywords = list(DEFAULT_PURPOSE_KEYWORDS) + list(
            question_config.get("purpose_keywords", [])
        )
        style_keywords = list(DEFAULT_STYLE_KEYWORDS) + list(
            question_config.get("style_keywords", [])
        )
        clarification_message = question_config.get(
            "clarification_message", DEFAULT_CLARIFICATION_MESSAGE
        )

        lower = context["query"].lower()
        detected_purpose = [kw for kw in purpose_keywords if kw.lower() in lower]
        detected_style = [kw for kw in style_keywords if kw.lower() in lower]
        missing_fields = self._find_missing_context(lower, detected_purpose, detected_style)
        needs_clarification = bool(missing_fields)
        next_question_field = missing_fields[0] if missing_fields else ""
        clarification_questions = {
            **DEFAULT_CLARIFICATION_QUESTIONS,
            **question_config.get("clarification_questions", {}),
        }
        next_question = clarification_questions.get(next_question_field, clarification_message)

        context["detected_purpose"] = detected_purpose
        context["detected_style"] = detected_style
        context["missing_fields"] = missing_fields
        context["next_question_field"] = next_question_field
        context["needs_clarification"] = needs_clarification
        context["clarification_message"] = next_question if needs_clarification else ""
        context["executed_agents"].append("question")

    def _find_missing_context(
        self,
        lower: str,
        detected_purpose: list[str],
        detected_style: list[str],
    ) -> list[str]:
        missing_fields = []
        if not self._has_explicit_city(lower):
            missing_fields.append("city")
        if not any(keyword in lower for keyword in DATE_KEYWORDS):
            missing_fields.append("date")
        if not detected_purpose and not detected_style:
            missing_fields.append("purpose_or_style")
        return missing_fields

    def _has_explicit_city(self, lower: str) -> bool:
        return any(alias in lower for alias in CITY_ALIASES)

    def _run_weather_agent(self, context: dict[str, Any]) -> None:
        weather = self.base_engine.weather_tool.get_daily_weather(
            context["city_query"],
            context["day_offset"],
        )
        context["weather"] = weather
        context["weather_summary"] = {
            "date": weather.date,
            "condition": weather.condition,
            "temp_min": weather.temp_min,
            "temp_max": weather.temp_max,
            "precipitation_probability": weather.precipitation_probability,
        }
        context["executed_agents"].append("weather")
        context["executed_tools"].append("weather")

    def _run_shopping_analysis_agent(self, context: dict[str, Any]) -> None:
        tools = self.base_engine.config.get("tools", {})
        filename = tools.get("shopping_history", {}).get("file", "shopping_history.json")
        records = self._load_json(self.data_dir / filename)
        shopping_items = records.get(context["user_id"])
        if shopping_items is None:
            raise ValueError(f"unknown user_id: {context['user_id']}")

        analysis = analyze_shopping_history(shopping_items)
        context["shopping_history"] = shopping_items
        context["shopping_history_summary"] = {
            "records": len(shopping_items),
            "source": filename,
            "sample_items": [item.get("item") for item in shopping_items[:3]],
        }
        context["shopping_analysis"] = analysis
        context["shopping_item_count"] = analysis["total_items"]
        context["styles_text"] = ", ".join(analysis["top_styles"])
        context["colors_text"] = ", ".join(analysis["top_colors"])
        context["favorite_items_text"] = ", ".join(analysis["favorite_items"])
        context["top_categories_text"] = ", ".join(analysis["top_categories"])
        context["user_name"] = context["user_id"]
        context["shopping_analysis_summary"] = {
            "total_items": analysis["total_items"],
            "top_styles": analysis["top_styles"],
            "top_colors": analysis["top_colors"],
            "top_categories": analysis["top_categories"],
            "favorite_items": analysis["favorite_items"],
        }
        context["executed_agents"].append("shopping_analysis")
        context["executed_tools"].append("shopping_history")

    def _trace_request_parser(self, context: dict[str, Any]) -> TraceStep:
        return TraceStep(
            name="Request Parser Node",
            detail=(
                f"city={context['city_display']}, date={context['date_label']}, "
                f"user={context['user_id']}"
            ),
            data={
                "workflow": str(self.workflow_config_path),
                "base_config": str(self.base_engine.config_path),
                "intent": self.base_engine.config.get("intent"),
                "matched_keywords": context["matched_keywords"],
            },
        )

    def _trace_question(self, context: dict[str, Any]) -> TraceStep:
        if context.get("needs_clarification"):
            missing = ", ".join(context.get("missing_fields", []))
            detail = f"missing={missing} → {context.get('next_question_field')} 질문"
        else:
            purpose = ", ".join(context.get("detected_purpose", [])) or "(없음)"
            style = ", ".join(context.get("detected_style", [])) or "(없음)"
            detail = f"purpose={purpose}, style={style} → 정보 충분"
        return TraceStep(
            name="Question Node",
            detail=detail,
            data={
                "detected_purpose": context.get("detected_purpose", []),
                "detected_style": context.get("detected_style", []),
                "missing_fields": context.get("missing_fields", []),
                "next_question_field": context.get("next_question_field", ""),
                "needs_clarification": context.get("needs_clarification", False),
                "clarification_message": context.get("clarification_message", ""),
            },
        )

    def _trace_weather(self, context: dict[str, Any]) -> TraceStep:
        return TraceStep(
            name="Weather Tool Node",
            detail=(
                f"{context['city_display']} {context['date_label']} weather loaded: "
                f"{context['weather_summary']['condition']}"
            ),
            data=context["weather_summary"],
        )

    def _trace_shopping(self, context: dict[str, Any]) -> TraceStep:
        return TraceStep(
            name="Shopping History Analysis Node",
            detail=(
                f"styles={context['styles_text']}, colors={context['colors_text']}, "
                f"records={context['shopping_item_count']}"
            ),
            data=context["shopping_analysis_summary"],
        )

    def _trace_recommendation(self, context: dict[str, Any]) -> TraceStep:
        return TraceStep(
            name="Recommendation Node",
            detail=f"rule={context['matched_rule_name']}, items={len(context['recommended_items'])}",
            data={
                "avg_temp": context["avg_temp"],
                "recommended_items": context["recommended_items"],
                "ranked_items": context.get("ranked_items", []),
                "extras": context["extras"],
            },
        )

    def _trace_compose(self, context: dict[str, Any]) -> TraceStep:
        return TraceStep(
            name="Compose Node",
            detail="final response rendered from output_template",
            data={
                "template_id": self.base_engine.config.get("agent_id"),
                "workflow_id": self.workflow_config.get("workflow_id"),
            },
        )

    def _runtime_trace(self, node_id: str, detail: str, data: dict[str, Any]) -> TraceStep:
        return TraceStep(name=self._node_name(node_id), detail=detail, data=data)

    def _node_name(self, node_id: str) -> str:
        for agent in self.workflow_config.get("agents", []):
            if agent.get("id") == node_id:
                return agent.get("name", node_id)
        return node_id

    def _load_runtime_data(self) -> dict[str, Any]:
        data_file = self.workflow_config.get("data_file")
        if not data_file:
            raise ValueError(f"{self.runtime_type} workflow requires data_file")
        return self._load_json(self.data_dir / data_file)

    def _extract_duration_minutes(self, query: str, default: int) -> int:
        for token in query.replace("-", " ").split():
            cleaned = "".join(ch for ch in token if ch.isdigit())
            if cleaned:
                value = int(cleaned)
                if 1 <= value <= 180:
                    return value
        return default

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

    def _build_presentation_outline(self, context: dict[str, Any]) -> list[str]:
        matched = ", ".join(context.get("matched_topics", []))
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
            "Matched knowledge: " + ", ".join(context.get("matched_topics", [])),
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

    def _detect_support_intent(self, query: str) -> str:
        lower = query.lower()
        if any(word in lower for word in ("refund", "return", "cancel", "money back")):
            return "refund_or_return"
        if any(word in lower for word in ("late", "delivery", "shipping", "tracking")):
            return "delivery_status"
        if any(word in lower for word in ("login", "password", "account", "locked")):
            return "account_access"
        return "technical_help"

    def _classify_support_ticket(
        self,
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

    def _render_support_answer(self, context: dict[str, Any]) -> str:
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

    def _load_json(self, path: Path) -> Any:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

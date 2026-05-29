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
        base_config = Path(self.workflow_config["base_agent_config"])
        if not base_config.is_absolute():
            base_config = self.workflow_config_path.parent / base_config
        self.base_engine = AgentBuilderEngine(
            base_config,
            data_dir=data_dir,
            weather_tool=weather_tool,
        )
        self.data_dir = self.base_engine.data_dir

    def run(self, user_message: str | None = None, user_id: str | None = None) -> WorkflowResult:
        query = (user_message or self.workflow_config.get("default_query") or "").strip()
        selected_user = user_id or self.workflow_config.get("default_user_id", "user_a")

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

    def _load_json(self, path: Path) -> Any:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

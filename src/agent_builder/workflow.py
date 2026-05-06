import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_builder.engine import AgentBuilderEngine, TraceStep
from agent_builder.shopping import analyze_shopping_history
from weather_agent.tools import WeatherTool


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
            name="Request Parser Agent",
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

    def _trace_weather(self, context: dict[str, Any]) -> TraceStep:
        return TraceStep(
            name="Weather Agent",
            detail=(
                f"{context['city_display']} {context['date_label']} weather loaded: "
                f"{context['weather_summary']['condition']}"
            ),
            data=context["weather_summary"],
        )

    def _trace_shopping(self, context: dict[str, Any]) -> TraceStep:
        return TraceStep(
            name="Shopping Analysis Agent",
            detail=(
                f"styles={context['styles_text']}, colors={context['colors_text']}, "
                f"records={context['shopping_item_count']}"
            ),
            data=context["shopping_analysis_summary"],
        )

    def _trace_recommendation(self, context: dict[str, Any]) -> TraceStep:
        return TraceStep(
            name="Recommendation Agent",
            detail=f"rule={context['matched_rule_name']}, items={len(context['recommended_items'])}",
            data={
                "avg_temp": context["avg_temp"],
                "recommended_items": context["recommended_items"],
                "extras": context["extras"],
            },
        )

    def _trace_compose(self, context: dict[str, Any]) -> TraceStep:
        return TraceStep(
            name="Compose Agent",
            detail="final response rendered from output_template",
            data={
                "template_id": self.base_engine.config.get("agent_id"),
                "workflow_id": self.workflow_config.get("workflow_id"),
            },
        )

    def _load_json(self, path: Path) -> Any:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

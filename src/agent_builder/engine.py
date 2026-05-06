import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_builder.shopping import analyze_shopping_history, select_owned_items
from weather_agent.tools import CITY_ALIASES, WeatherTool


@dataclass(frozen=True)
class TraceStep:
    name: str
    detail: str
    data: dict[str, Any]


@dataclass(frozen=True)
class BuilderResult:
    agent_name: str
    answer: str
    trace: list[TraceStep]
    context: dict[str, Any]


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class AgentBuilderEngine:
    """Runs different Agents from JSON configs with one shared execution path."""

    def __init__(
        self,
        config_path: str | Path,
        data_dir: str | Path | None = None,
        weather_tool: WeatherTool | None = None,
    ):
        self.config_path = Path(config_path)
        self.config = self._load_json(self.config_path)
        self.data_dir = Path(data_dir) if data_dir else self.config_path.parent.parent / "data"
        self.weather_tool = weather_tool or WeatherTool()

    def run(self, user_message: str | None = None, user_id: str | None = None) -> BuilderResult:
        query = (user_message or self.config.get("default_query") or "").strip()
        selected_user = user_id or self.config.get("default_user_id", "user_a")

        trace: list[TraceStep] = []
        context = self._plan(query, selected_user)
        trace.append(
            TraceStep(
                name="Plan",
                detail=(
                    f"agent={self.config['agent_name']}, city={context['city_display']}, "
                    f"date={context['date_label']}, user={selected_user}"
                ),
                data={
                    "config": str(self.config_path),
                    "intent": self.config.get("intent"),
                    "matched_keywords": context["matched_keywords"],
                },
            )
        )

        self._act(context)
        trace.append(
            TraceStep(
                name="Act",
                detail="configured tools executed: " + ", ".join(context["executed_tools"]),
                data={
                    "weather": context.get("weather_summary"),
                    "shopping_history": context.get("shopping_history_summary"),
                },
            )
        )

        self._analyze(context)
        trace.append(
            TraceStep(
                name="Analyze",
                detail=(
                    f"styles={context['styles_text']}, colors={context['colors_text']}, "
                    f"items={context['shopping_item_count']}"
                ),
                data=context["shopping_analysis_summary"],
            )
        )

        self._decide(context)
        trace.append(
            TraceStep(
                name="Decide",
                detail=f"rule={context['matched_rule_name']}, extras={context['extras_text'] or 'none'}",
                data={
                    "avg_temp": context["avg_temp"],
                    "recommended_items": context["recommended_items"],
                    "extras": context["extras"],
                },
            )
        )

        answer = self._render(context)
        trace.append(
            TraceStep(
                name="Compose",
                detail="output_template rendered from config",
                data={"template_id": self.config.get("agent_id")},
            )
        )

        return BuilderResult(
            agent_name=self.config["agent_name"],
            answer=answer,
            trace=trace,
            context=context,
        )

    def _plan(self, query: str, user_id: str) -> dict[str, Any]:
        lower = query.lower()
        city_display, city_query = self._extract_city(lower)
        day_offset, date_label = self._extract_date(lower)
        keywords = self.config.get("intent_keywords", [])
        matched_keywords = [keyword for keyword in keywords if keyword.lower() in lower]

        return {
            "query": query,
            "agent_name": self.config["agent_name"],
            "user_id": user_id,
            "city_display": city_display,
            "city_query": city_query,
            "day_offset": day_offset,
            "date_label": date_label,
            "matched_keywords": matched_keywords,
            "executed_tools": [],
        }

    def _act(self, context: dict[str, Any]) -> None:
        tools = self.config.get("tools", {})
        if tools.get("weather", {}).get("enabled", False):
            weather = self.weather_tool.get_daily_weather(
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
            context["executed_tools"].append("weather")

        if tools.get("shopping_history", {}).get("enabled", False):
            filename = tools["shopping_history"].get("file", "shopping_history.json")
            records = self._load_json(self.data_dir / filename)
            shopping_items = records.get(context["user_id"])
            if shopping_items is None:
                raise ValueError(f"unknown user_id: {context['user_id']}")
            context["shopping_history"] = shopping_items
            context["shopping_history_summary"] = {
                "records": len(shopping_items),
                "source": filename,
                "sample_items": [item.get("item") for item in shopping_items[:3]],
            }
            context["executed_tools"].append("shopping_history")

    def _analyze(self, context: dict[str, Any]) -> None:
        shopping_items = context.get("shopping_history", [])
        analysis = analyze_shopping_history(shopping_items)
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

    def _decide(self, context: dict[str, Any]) -> None:
        weather = context["weather"]
        avg_temp = round((weather.temp_min + weather.temp_max) / 2, 1)
        context["avg_temp"] = avg_temp
        context["temp_min"] = weather.temp_min
        context["temp_max"] = weather.temp_max
        context["weather_date"] = weather.date
        context["weather_condition"] = weather.condition
        context["precipitation_probability"] = weather.precipitation_probability

        rule = self._match_temperature_rule(avg_temp)
        context["matched_rule_name"] = rule.get("name", "default")
        context["recommendation"] = self._format(rule.get("recommendation", ""), context)

        items = [self._format(item, context) for item in rule.get("items", [])]
        owned_items = select_owned_items(
            context.get("shopping_history", []),
            avg_temp=avg_temp,
            precipitation_probability=weather.precipitation_probability,
            target_categories=rule.get("owned_item_categories", []),
        )
        extras = self._match_extras(context)
        context["owned_recommended_items"] = owned_items
        context["owned_recommended_items_text"] = ", ".join(owned_items)
        context["additional_items"] = items + [extra["item"] for extra in extras if extra.get("item")]
        context["additional_items_text"] = ", ".join(context["additional_items"])
        context["recommended_items"] = owned_items + context["additional_items"]
        context["recommended_items_text"] = ", ".join(context["recommended_items"])
        context["extras"] = extras
        context["extras_text"] = ", ".join(extra["text"] for extra in extras if extra.get("text"))

    def _render(self, context: dict[str, Any]) -> str:
        template = self.config["output_template"]
        return self._format(template, context)

    def _match_temperature_rule(self, avg_temp: float) -> dict[str, Any]:
        for rule in self.config.get("temperature_rules", []):
            min_temp = rule.get("min_avg_temp")
            max_temp = rule.get("max_avg_temp")
            if min_temp is not None and avg_temp < min_temp:
                continue
            if max_temp is not None and avg_temp > max_temp:
                continue
            return rule
        return {
            "name": "fallback",
            "recommendation": "기본 추천을 사용합니다.",
            "items": [],
        }

    def _match_extras(self, context: dict[str, Any]) -> list[dict[str, str]]:
        weather = context["weather"]
        extras = []
        for extra in self.config.get("conditional_extras", []):
            if not self._extra_matches(extra, weather):
                continue
            extras.append(
                {
                    "item": self._format(extra.get("item", ""), context),
                    "text": self._format(extra.get("text", ""), context),
                }
            )
        return extras

    def _extra_matches(self, extra: dict[str, Any], weather: Any) -> bool:
        if "precipitation_min" in extra:
            if weather.precipitation_probability < extra["precipitation_min"]:
                return False
        if "temp_gap_min" in extra:
            if weather.temp_max - weather.temp_min < extra["temp_gap_min"]:
                return False
        if "weather_codes" in extra:
            if weather.weather_code not in set(extra["weather_codes"]):
                return False
        return True

    def _extract_city(self, lower_text: str) -> tuple[str, str]:
        for alias in sorted(CITY_ALIASES, key=len, reverse=True):
            if alias in lower_text:
                return CITY_ALIASES[alias]
        default_city = self.config.get("default_city", {"display": "서울", "query": "Seoul"})
        return default_city["display"], default_city["query"]

    def _extract_date(self, lower_text: str) -> tuple[int, str]:
        if "모레" in lower_text or "day after tomorrow" in lower_text:
            return 2, "모레"
        if "내일" in lower_text or "tomorrow" in lower_text:
            return 1, "내일"
        return 0, "오늘"

    def _format(self, template: str, context: dict[str, Any]) -> str:
        return template.format_map(SafeDict(context))

    def _load_json(self, path: Path) -> Any:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

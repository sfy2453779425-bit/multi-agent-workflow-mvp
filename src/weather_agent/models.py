from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Intent:
    raw_text: str
    city_display: str
    city_query: str
    day_offset: int
    date_label: str
    wants_weather: bool
    wants_clothing: bool


@dataclass(frozen=True)
class WeatherReport:
    city_name: str
    country: str
    date: str
    condition: str
    weather_code: int
    temp_min: float
    temp_max: float
    precipitation_probability: int
    latitude: float
    longitude: float


@dataclass(frozen=True)
class TraceStep:
    name: str
    description: str
    detail: str
    data: dict[str, Any] | None = None


@dataclass(frozen=True)
class AgentResult:
    answer: str
    intent: Intent
    weather: WeatherReport
    trace: list[TraceStep]

import json
from dataclasses import asdict
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from .models import WeatherReport


CITY_ALIASES = {
    "서울": ("서울", "Seoul"),
    "seoul": ("서울", "Seoul"),
    "부산": ("부산", "Busan"),
    "busan": ("부산", "Busan"),
    "인천": ("인천", "Incheon"),
    "incheon": ("인천", "Incheon"),
    "대구": ("대구", "Daegu"),
    "daegu": ("대구", "Daegu"),
    "대전": ("대전", "Daejeon"),
    "daejeon": ("대전", "Daejeon"),
    "광주": ("광주", "Gwangju"),
    "gwangju": ("광주", "Gwangju"),
    "제주": ("제주", "Jeju City"),
    "jeju": ("제주", "Jeju City"),
    "수원": ("수원", "Suwon"),
    "suwon": ("수원", "Suwon"),
    "도쿄": ("도쿄", "Tokyo"),
    "tokyo": ("도쿄", "Tokyo"),
    "오사카": ("오사카", "Osaka"),
    "osaka": ("오사카", "Osaka"),
    "뉴욕": ("뉴욕", "New York"),
    "new york": ("뉴욕", "New York"),
}


WEATHER_CODE_TEXT = {
    0: "맑음",
    1: "대체로 맑음",
    2: "부분적으로 흐림",
    3: "흐림",
    45: "안개",
    48: "서리 안개",
    51: "약한 이슬비",
    53: "이슬비",
    55: "강한 이슬비",
    56: "약한 어는 이슬비",
    57: "강한 어는 이슬비",
    61: "약한 비",
    63: "비",
    65: "강한 비",
    66: "약한 어는 비",
    67: "강한 어는 비",
    71: "약한 눈",
    73: "눈",
    75: "강한 눈",
    77: "싸락눈",
    80: "약한 소나기",
    81: "소나기",
    82: "강한 소나기",
    85: "약한 눈 소나기",
    86: "강한 눈 소나기",
    95: "뇌우",
    96: "우박을 동반한 뇌우",
    99: "강한 우박을 동반한 뇌우",
}


def weather_code_to_text(code: int) -> str:
    return WEATHER_CODE_TEXT.get(code, f"알 수 없음({code})")


class WeatherTool:
    """Bound external tool used by the template Agent's Act step."""

    geocoding_endpoint = "https://geocoding-api.open-meteo.com/v1/search"
    forecast_endpoint = "https://api.open-meteo.com/v1/forecast"

    def _get_json(self, url: str, timeout: int = 12) -> dict[str, Any]:
        try:
            with urlopen(url, timeout=timeout) as response:
                payload = response.read().decode("utf-8")
        except Exception as exc:  # Network errors differ by OS and Python version.
            raise RuntimeError(f"외부 API 호출 실패: {exc}") from exc
        return json.loads(payload)

    def geocode(self, city_query: str) -> dict[str, Any]:
        params = urlencode(
            {
                "name": city_query,
                "count": 1,
                "language": "ko",
                "format": "json",
            }
        )
        data = self._get_json(f"{self.geocoding_endpoint}?{params}")
        results = data.get("results") or []
        if not results:
            raise ValueError(f"도시 좌표를 찾을 수 없습니다: {city_query}")
        return results[0]

    def get_daily_weather(
        self,
        city_query: str,
        day_offset: int,
        timezone: str = "Asia/Seoul",
    ) -> WeatherReport:
        location = self.geocode(city_query)
        forecast_days = max(day_offset + 1, 3)
        params = urlencode(
            {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "daily": ",".join(
                    [
                        "weather_code",
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "precipitation_probability_max",
                    ]
                ),
                "timezone": timezone,
                "forecast_days": forecast_days,
            }
        )
        data = self._get_json(f"{self.forecast_endpoint}?{params}")
        daily = data["daily"]
        idx = day_offset
        weather_code = int(daily["weather_code"][idx])
        precipitation = daily.get("precipitation_probability_max", [0] * forecast_days)[idx]
        if precipitation is None:
            precipitation = 0

        return WeatherReport(
            city_name=location.get("name", city_query),
            country=location.get("country", ""),
            date=daily["time"][idx],
            condition=weather_code_to_text(weather_code),
            weather_code=weather_code,
            temp_min=float(daily["temperature_2m_min"][idx]),
            temp_max=float(daily["temperature_2m_max"][idx]),
            precipitation_probability=int(precipitation),
            latitude=float(location["latitude"]),
            longitude=float(location["longitude"]),
        )

    def describe_tool_call(self, report: WeatherReport) -> dict[str, Any]:
        data = asdict(report)
        data["tool"] = "Open-Meteo Geocoding API + Forecast API"
        return data

from .models import AgentResult, Intent, TraceStep, WeatherReport
from .tools import CITY_ALIASES, WeatherTool


class TemplateWeatherAgent:
    """A deterministic Plan-Act-Compose Agent generated from a weather template."""

    template_name = "weather_clothing_template_v1"
    fixed_flow = ("Plan", "Act", "Compose")

    def __init__(self, weather_tool: WeatherTool | None = None):
        self.weather_tool = weather_tool or WeatherTool()

    def run(self, user_message: str) -> AgentResult:
        trace: list[TraceStep] = []

        intent = self._plan(user_message)
        trace.append(
            TraceStep(
                name="Plan",
                description="사용자 입력에서 도시, 날짜, 작업 유형을 추출",
                detail=(
                    f"city={intent.city_display}, date={intent.date_label}, "
                    f"weather={intent.wants_weather}, clothing={intent.wants_clothing}"
                ),
                data={
                    "city_query": intent.city_query,
                    "day_offset": intent.day_offset,
                    "template": self.template_name,
                },
            )
        )

        weather = self._act(intent)
        trace.append(
            TraceStep(
                name="Act",
                description="템플릿에 바인딩된 날씨 도구를 호출",
                detail=(
                    f"{weather.city_name}({weather.latitude:.3f}, "
                    f"{weather.longitude:.3f}) forecast API 호출 완료"
                ),
                data=self.weather_tool.describe_tool_call(weather),
            )
        )

        answer = self._compose(intent, weather)
        trace.append(
            TraceStep(
                name="Compose",
                description="고정 규칙으로 날씨 요약과 추천 문장을 생성",
                detail="날씨 조건, 평균기온, 강수확률을 기반으로 최종 응답 생성",
                data={
                    "average_temp": round((weather.temp_min + weather.temp_max) / 2, 1),
                    "precipitation_probability": weather.precipitation_probability,
                },
            )
        )

        return AgentResult(answer=answer, intent=intent, weather=weather, trace=trace)

    def _plan(self, user_message: str) -> Intent:
        text = user_message.strip()
        lower = text.lower()
        city_display, city_query = self._extract_city(lower)
        day_offset, date_label = self._extract_date(lower)
        wants_clothing = any(
            token in lower
            for token in ["옷", "옷차림", "코디", "입어", "추천", "clothes", "wear"]
        )
        wants_weather = any(token in lower for token in ["날씨", "weather"]) or not wants_clothing

        return Intent(
            raw_text=text,
            city_display=city_display,
            city_query=city_query,
            day_offset=day_offset,
            date_label=date_label,
            wants_weather=wants_weather,
            wants_clothing=wants_clothing,
        )

    def _extract_city(self, lower_text: str) -> tuple[str, str]:
        for alias in sorted(CITY_ALIASES, key=len, reverse=True):
            if alias in lower_text:
                return CITY_ALIASES[alias]
        raise ValueError(
            "도시를 찾을 수 없습니다. 예: '서울 내일 날씨 알려주고 옷 추천해줘'"
        )

    def _extract_date(self, lower_text: str) -> tuple[int, str]:
        if "모레" in lower_text or "day after tomorrow" in lower_text:
            return 2, "모레"
        if "내일" in lower_text or "tomorrow" in lower_text:
            return 1, "내일"
        if "오늘" in lower_text or "today" in lower_text:
            return 0, "오늘"
        return 0, "오늘"

    def _act(self, intent: Intent) -> WeatherReport:
        return self.weather_tool.get_daily_weather(intent.city_query, intent.day_offset)

    def _compose(self, intent: Intent, weather: WeatherReport) -> str:
        avg_temp = (weather.temp_min + weather.temp_max) / 2
        lines = [
            f"[{self.template_name}] Plan -> Act -> Compose 실행 완료",
            (
                f"{intent.city_display}의 {intent.date_label}({weather.date}) 날씨는 "
                f"{weather.condition}입니다. 최저 {weather.temp_min:.1f}°C, "
                f"최고 {weather.temp_max:.1f}°C, 강수확률은 "
                f"{weather.precipitation_probability}%입니다."
            ),
        ]

        if intent.wants_clothing:
            lines.append(f"옷 추천: {self._recommend_clothing(avg_temp, weather)}")

        lines.append(
            "근거: 템플릿이 도시/날짜를 먼저 고정하고, Weather API 호출 후 "
            "규칙 기반 Compose 단계에서 응답을 생성했습니다."
        )
        return "\n".join(lines)

    def _recommend_clothing(self, avg_temp: float, weather: WeatherReport) -> str:
        if avg_temp <= 0:
            base = "두꺼운 패딩, 목도리, 장갑처럼 보온성이 높은 옷차림"
        elif avg_temp <= 5:
            base = "두꺼운 코트나 패딩, 니트, 보온 이너"
        elif avg_temp <= 11:
            base = "코트나 점퍼, 니트, 긴 바지"
        elif avg_temp <= 16:
            base = "자켓이나 가디건, 긴팔 상의"
        elif avg_temp <= 22:
            base = "얇은 긴팔이나 셔츠, 가벼운 겉옷"
        elif avg_temp <= 27:
            base = "반팔에 얇은 겉옷을 함께 준비하는 옷차림"
        else:
            base = "반팔, 얇은 셔츠, 통풍이 잘 되는 옷차림"

        extras: list[str] = []
        rainy_codes = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}
        snowy_codes = {71, 73, 75, 77, 85, 86}
        if weather.precipitation_probability >= 50 or weather.weather_code in rainy_codes:
            extras.append("우산")
        if weather.weather_code in snowy_codes:
            extras.append("미끄럽지 않은 신발")
        if weather.temp_max - weather.temp_min >= 10:
            extras.append("일교차 대비용 겉옷")

        if extras:
            return f"{base}을 추천합니다. 추가로 {', '.join(extras)}을 준비하세요."
        return f"{base}을 추천합니다."

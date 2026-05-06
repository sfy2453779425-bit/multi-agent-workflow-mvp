import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from weather_agent import TemplateWeatherAgent, WeatherReport  # noqa: E402


class FakeWeatherTool:
    def get_daily_weather(self, city_query, day_offset):
        self.city_query = city_query
        self.day_offset = day_offset
        return WeatherReport(
            city_name="서울",
            country="대한민국",
            date="2026-04-19",
            condition="흐림",
            weather_code=3,
            temp_min=9.0,
            temp_max=18.0,
            precipitation_probability=30,
            latitude=37.566,
            longitude=126.978,
        )

    def describe_tool_call(self, report):
        return {"tool": "fake-weather", "city": report.city_name}


class TemplateWeatherAgentTest(unittest.TestCase):
    def test_runs_fixed_flow_for_weather_and_clothing(self):
        tool = FakeWeatherTool()
        agent = TemplateWeatherAgent(weather_tool=tool)

        result = agent.run("서울 내일 날씨 알려주고 옷 추천해줘")

        self.assertEqual(["Plan", "Act", "Compose"], [step.name for step in result.trace])
        self.assertEqual("Seoul", tool.city_query)
        self.assertEqual(1, tool.day_offset)
        self.assertTrue(result.intent.wants_clothing)
        self.assertIn("옷 추천", result.answer)

    def test_requires_city(self):
        agent = TemplateWeatherAgent(weather_tool=FakeWeatherTool())

        with self.assertRaises(ValueError):
            agent.run("내일 날씨 알려줘")


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_builder import AgentBuilderEngine, MultiAgentWorkflowEngine  # noqa: E402
from weather_agent import WeatherReport  # noqa: E402


class FakeWeatherTool:
    def get_daily_weather(self, city_query, day_offset):
        return WeatherReport(
            city_name="서울",
            country="대한민국",
            date="2026-04-27",
            condition="흐림",
            weather_code=3,
            temp_min=10.0,
            temp_max=21.0,
            precipitation_probability=20,
            latitude=37.566,
            longitude=126.978,
        )


class AgentBuilderEngineTest(unittest.TestCase):
    def test_same_engine_runs_outfit_config(self):
        engine = AgentBuilderEngine(
            ROOT / "configs" / "outfit_agent.json",
            weather_tool=FakeWeatherTool(),
        )

        result = engine.run("서울 내일 옷 추천해줘", user_id="user_a")

        self.assertEqual("Personalized Outfit Agent", result.agent_name)
        self.assertEqual(["Plan", "Act", "Analyze", "Decide", "Compose"], [s.name for s in result.trace])
        self.assertIn("보유 단품 기반 추천", result.answer)
        self.assertIn("쇼핑 기록 분석", result.answer)
        self.assertIn("블랙 후드티", result.answer)

    def test_same_engine_runs_travel_config(self):
        engine = AgentBuilderEngine(
            ROOT / "configs" / "travel_pack_agent.json",
            weather_tool=FakeWeatherTool(),
        )

        result = engine.run("서울 내일 여행 준비물 추천해줘", user_id="user_a")

        self.assertEqual("Travel Packing Agent", result.agent_name)
        self.assertIn("챙길 물건", result.answer)
        self.assertIn("쇼핑 기록 분석", result.answer)
        self.assertIn("보조 배터리", result.answer)

    def test_same_engine_runs_commute_config(self):
        engine = AgentBuilderEngine(
            ROOT / "configs" / "commute_agent.json",
            weather_tool=FakeWeatherTool(),
        )

        result = engine.run("서울 내일 학교 갈 때 뭐 챙겨야 해?", user_id="user_a")

        self.assertEqual("Commute Preparation Agent", result.agent_name)
        self.assertEqual(["Plan", "Act", "Analyze", "Decide", "Compose"], [s.name for s in result.trace])
        self.assertIn("통학/출근 준비 방향", result.answer)
        self.assertIn("교통카드", result.answer)

    def test_user_profile_changes_output_without_code_change(self):
        engine = AgentBuilderEngine(
            ROOT / "configs" / "outfit_agent.json",
            weather_tool=FakeWeatherTool(),
        )

        user_a = engine.run("서울 내일 옷 추천해줘", user_id="user_a")
        user_b = engine.run("서울 내일 옷 추천해줘", user_id="user_b")

        self.assertIn("블랙 후드티", user_a.answer)
        self.assertIn("화이트 옥스포드 셔츠", user_b.answer)
        self.assertNotEqual(user_a.answer, user_b.answer)

    def test_multi_agent_workflow_runs_outfit_process(self):
        engine = MultiAgentWorkflowEngine(
            ROOT / "configs" / "outfit_workflow.json",
            weather_tool=FakeWeatherTool(),
        )

        result = engine.run("서울 내일 옷 추천해줘", user_id="user_a")

        self.assertEqual("Outfit Multi-Agent Workflow", result.workflow_name)
        self.assertEqual(
            [
                "Request Parser Agent",
                "Weather Agent",
                "Shopping Analysis Agent",
                "Recommendation Agent",
                "Compose Agent",
            ],
            [s.name for s in result.trace],
        )
        self.assertIn("보유 단품 기반 추천", result.answer)
        self.assertIn("블랙 후드티", result.answer)
        self.assertEqual(
            ["request_parser", "weather", "shopping_analysis", "recommendation", "compose"],
            result.context["executed_agents"],
        )


if __name__ == "__main__":
    unittest.main()

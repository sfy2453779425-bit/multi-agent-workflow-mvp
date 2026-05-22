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
        self.assertIn("추천 순위", result.answer)
        self.assertIn("1. ", result.answer)
        self.assertIn("보유 단품 기반 추천", result.answer)
        self.assertIn("쇼핑 기록 분석", result.answer)
        self.assertIn("블랙 후드티", result.answer)

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

        result = engine.run("서울 내일 출근할 때 옷 추천해줘", user_id="user_a")

        self.assertEqual("Outfit Recommendation Workflow", result.workflow_name)
        self.assertEqual(
            [
                "Request Parser Node",
                "Question Node",
                "Weather Tool Node",
                "Shopping History Analysis Node",
                "Recommendation Node",
                "Compose Node",
            ],
            [s.name for s in result.trace],
        )
        self.assertIn("보유 단품 기반 추천", result.answer)
        self.assertIn("추천 순위", result.answer)
        self.assertIn("블랙 후드티", result.answer)
        self.assertEqual(
            [
                "request_parser",
                "question",
                "weather",
                "shopping_analysis",
                "recommendation",
                "compose",
            ],
            result.context["executed_agents"],
        )
        self.assertFalse(result.context["needs_clarification"])
        self.assertIn("출근", result.context["detected_purpose"])

    def test_question_agent_asks_city_first_when_information_missing(self):
        engine = MultiAgentWorkflowEngine(
            ROOT / "configs" / "outfit_workflow.json",
            weather_tool=FakeWeatherTool(),
        )

        result = engine.run("옷 추천해줘", user_id="user_a")

        self.assertEqual(
            ["Request Parser Node", "Question Node"],
            [s.name for s in result.trace],
        )
        self.assertEqual(
            ["request_parser", "question"],
            result.context["executed_agents"],
        )
        self.assertTrue(result.context["needs_clarification"])
        self.assertEqual("city", result.context["next_question_field"])
        self.assertEqual(["city", "date", "purpose_or_style"], result.context["missing_fields"])
        self.assertIn("어느 도시", result.answer)
        self.assertNotIn("weather", result.context.get("executed_tools", []))

    def test_question_agent_continues_to_next_missing_field(self):
        engine = MultiAgentWorkflowEngine(
            ROOT / "configs" / "outfit_workflow.json",
            weather_tool=FakeWeatherTool(),
        )

        result = engine.run("옷 추천해줘 칭다오", user_id="user_a")

        self.assertTrue(result.context["needs_clarification"])
        self.assertEqual("date", result.context["next_question_field"])
        self.assertIn("언제", result.answer)

    def test_question_agent_asks_purpose_or_style_last(self):
        engine = MultiAgentWorkflowEngine(
            ROOT / "configs" / "outfit_workflow.json",
            weather_tool=FakeWeatherTool(),
        )

        result = engine.run("칭다오 다음 주 옷 추천해줘", user_id="user_a")

        self.assertTrue(result.context["needs_clarification"])
        self.assertEqual("purpose_or_style", result.context["next_question_field"])
        self.assertIn("여행/출근/데이트", result.answer)

    def test_question_agent_passes_when_style_keyword_present(self):
        engine = MultiAgentWorkflowEngine(
            ROOT / "configs" / "outfit_workflow.json",
            weather_tool=FakeWeatherTool(),
        )

        result = engine.run("서울 내일 캐주얼하게 옷 추천해줘", user_id="user_a")

        self.assertFalse(result.context["needs_clarification"])
        self.assertIn("캐주얼", result.context["detected_style"])
        self.assertEqual(6, len(result.trace))

    def test_question_agent_passes_after_followup_context_is_complete(self):
        engine = MultiAgentWorkflowEngine(
            ROOT / "configs" / "outfit_workflow.json",
            weather_tool=FakeWeatherTool(),
        )

        result = engine.run("옷 추천해줘 칭다오 다음 주 여행", user_id="user_a")

        self.assertFalse(result.context["needs_clarification"])
        self.assertEqual(6, len(result.trace))
        self.assertIn("추천 순위", result.answer)


if __name__ == "__main__":
    unittest.main()

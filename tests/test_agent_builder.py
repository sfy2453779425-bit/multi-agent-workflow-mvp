import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_builder import AgentBuilderEngine, MultiAgentWorkflowEngine, TemplateWorkflowBuilder  # noqa: E402
from desktop_app import merge_followup_query  # noqa: E402
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

    def test_desktop_followup_query_merge(self):
        self.assertEqual("옷 추천해줘 칭다오", merge_followup_query("옷 추천해줘", "칭다오"))
        self.assertEqual("칭다오", merge_followup_query("", "칭다오"))
        self.assertEqual("옷 추천해줘", merge_followup_query("옷 추천해줘", ""))


    def test_template_builder_generates_outfit_workflow_config(self):
        builder = TemplateWorkflowBuilder(
            ROOT / "configs" / "builder_templates" / "outfit_recommendation_template.json"
        )

        generated = builder.build_workflow_config()

        self.assertEqual(
            [
                "request_parser",
                "question",
                "weather",
                "shopping_analysis",
                "recommendation",
                "compose",
            ],
            generated["execution"]["order"],
        )
        self.assertEqual(6, len(generated["agents"]))
        self.assertEqual("TemplateWorkflowBuilder", generated["execution"]["generated_by"])
        self.assertIn("question_agent", generated)

    def test_template_builder_rejects_missing_required_node(self):
        builder = TemplateWorkflowBuilder(
            ROOT / "configs" / "builder_templates" / "outfit_recommendation_template.json"
        )

        validation = builder.validate_node_ids(["request_parser", "question"])

        self.assertFalse(validation.ok)
        self.assertTrue(any("missing required nodes" in error for error in validation.errors))

    def test_generated_template_workflow_runs(self):
        import json
        import tempfile

        builder = TemplateWorkflowBuilder(
            ROOT / "configs" / "builder_templates" / "outfit_recommendation_template.json"
        )
        generated = builder.build_workflow_config(absolute_base_config=True)

        with tempfile.TemporaryDirectory(prefix="workflow_builder_test_") as temp_dir:
            generated_path = Path(temp_dir) / "generated_outfit_workflow.json"
            generated_path.write_text(
                json.dumps(generated, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            engine = MultiAgentWorkflowEngine(generated_path, weather_tool=FakeWeatherTool())
            result = engine.run("칭다오 다음 주 여행 캐주얼 옷 추천해줘", user_id="user_a")

        self.assertFalse(result.context["needs_clarification"])
        self.assertEqual(6, len(result.trace))
        self.assertIn("추천", result.answer)


    def test_builder_supports_multiple_recommendation_templates(self):
        outfit_builder = TemplateWorkflowBuilder(
            ROOT / "configs" / "builder_templates" / "outfit_recommendation_template.json"
        )
        commute_builder = TemplateWorkflowBuilder(
            ROOT / "configs" / "builder_templates" / "commute_outfit_template.json"
        )

        outfit_config = outfit_builder.build_workflow_config()
        commute_config = commute_builder.build_workflow_config()

        self.assertNotEqual(outfit_builder.template_name, commute_builder.template_name)
        self.assertNotEqual(outfit_config["workflow_id"], commute_config["workflow_id"])
        self.assertEqual(outfit_config["execution"]["order"], commute_config["execution"]["order"])
        self.assertIn("출근", commute_config["default_query"])

    def test_generated_commute_template_workflow_runs(self):
        import json
        import tempfile

        builder = TemplateWorkflowBuilder(
            ROOT / "configs" / "builder_templates" / "commute_outfit_template.json"
        )
        generated = builder.build_workflow_config(absolute_base_config=True)

        with tempfile.TemporaryDirectory(prefix="workflow_builder_commute_test_") as temp_dir:
            generated_path = Path(temp_dir) / "generated_commute_workflow.json"
            generated_path.write_text(
                json.dumps(generated, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            engine = MultiAgentWorkflowEngine(generated_path, weather_tool=FakeWeatherTool())
            result = engine.run("서울 내일 출근 포멀 옷 추천해줘", user_id="user_b")

        self.assertFalse(result.context["needs_clarification"])
        self.assertEqual(6, len(result.trace))
        self.assertIn("추천", result.answer)


    def test_builder_lists_four_templates_across_domains(self):
        template_dir = ROOT / "configs" / "builder_templates"
        template_names = {path.name for path in template_dir.glob("*_template.json")}

        self.assertIn("outfit_recommendation_template.json", template_names)
        self.assertIn("commute_outfit_template.json", template_names)
        self.assertIn("presentation_planning_template.json", template_names)
        self.assertIn("customer_support_ticket_template.json", template_names)

    def test_cross_domain_templates_generate_runtime_workflow_configs(self):
        presentation = TemplateWorkflowBuilder(
            ROOT / "configs" / "builder_templates" / "presentation_planning_template.json"
        ).build_workflow_config(absolute_base_config=True)
        support = TemplateWorkflowBuilder(
            ROOT / "configs" / "builder_templates" / "customer_support_ticket_template.json"
        ).build_workflow_config(absolute_base_config=True)

        self.assertEqual("presentation_planning", presentation["runtime_type"])
        self.assertEqual("presentation_knowledge.json", presentation["data_file"])
        self.assertIn("outline_generation", presentation["execution"]["order"])
        self.assertEqual("customer_support", support["runtime_type"])
        self.assertEqual("support_policy.json", support["data_file"])
        self.assertIn("routing_decision", support["execution"]["order"])

    def test_generated_presentation_template_workflow_runs(self):
        import json
        import tempfile

        builder = TemplateWorkflowBuilder(
            ROOT / "configs" / "builder_templates" / "presentation_planning_template.json"
        )
        generated = builder.build_workflow_config(absolute_base_config=True)

        with tempfile.TemporaryDirectory(prefix="workflow_builder_presentation_test_") as temp_dir:
            generated_path = Path(temp_dir) / "generated_presentation_workflow.json"
            generated_path.write_text(
                json.dumps(generated, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            engine = MultiAgentWorkflowEngine(generated_path)
            result = engine.run()

        self.assertFalse(result.context["needs_clarification"])
        self.assertEqual(6, len(result.trace))
        self.assertIn("Presentation Planning Workflow", result.answer)
        self.assertIn("summary_cards", result.context)

    def test_generated_customer_support_template_workflow_runs(self):
        import json
        import tempfile

        builder = TemplateWorkflowBuilder(
            ROOT / "configs" / "builder_templates" / "customer_support_ticket_template.json"
        )
        generated = builder.build_workflow_config(absolute_base_config=True)

        with tempfile.TemporaryDirectory(prefix="workflow_builder_support_test_") as temp_dir:
            generated_path = Path(temp_dir) / "generated_support_workflow.json"
            generated_path.write_text(
                json.dumps(generated, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            engine = MultiAgentWorkflowEngine(generated_path)
            result = engine.run()

        self.assertFalse(result.context["needs_clarification"])
        self.assertEqual(6, len(result.trace))
        self.assertIn("Customer Support Ticket Workflow", result.answer)
        self.assertEqual("Logistics Support", result.context["owner_team"])

    def test_web_builder_workspace_composes_custom_workflow(self):
        import web_app

        detail = web_app.api_builder_compose(
            {
                "preset": "presentation_planning",
                "workflow_name": "Team Final Presentation Workflow",
            }
        )

        self.assertEqual("custom_workspace", detail["builder_mode"])
        self.assertEqual("Team Final Presentation Workflow", detail["generated_config"]["workflow_name"])
        self.assertEqual("BuilderWorkspace", detail["generated_config"]["execution"]["generated_by"])
        self.assertEqual("presentation_planning_template.json", detail["generated_config"]["execution"]["source_template"])
        self.assertEqual(6, len(detail["nodes"]))

    def test_web_builder_workspace_runs_custom_workflow(self):
        import web_app

        result = web_app.api_builder_run(
            {
                "preset": "customer_support",
                "workflow_name": "Support Routing Built In Workspace",
                "query": "The delivery is late and the customer asks for refund support.",
                "user": "user_a",
            }
        )

        self.assertEqual("custom_workspace", result["builder_mode"])
        self.assertEqual("Support Routing Built In Workspace", result["workflow_name"])
        self.assertEqual(6, len(result["trace"]))
        self.assertTrue(result["summary"]["summary_cards"])
        self.assertEqual("BuilderWorkspace", result["generated_config"]["execution"]["generated_by"])

    def test_harness_comparison_experiment_produces_builder_delta(self):
        from experiments.harness_comparison import run_experiment

        result = run_experiment(write_outputs=False)

        self.assertEqual(2, result["summary"]["case_count"])
        self.assertEqual(4, result["summary"]["builder_presets_available"])
        self.assertEqual(17.0, result["summary"]["average_manual_touch_points"])
        self.assertEqual(3.0, result["summary"]["average_builder_touch_points"])
        for case in result["cases"]:
            self.assertEqual("GenericHarnessManualSpec", case["generic_harness"]["generated_by"])
            self.assertEqual("BuilderWorkspace", case["builder_workspace"]["generated_by"])
            self.assertEqual(6, case["generic_harness"]["trace_count"])
            self.assertEqual(6, case["builder_workspace"]["trace_count"])
            self.assertEqual(14, case["delta"]["touch_points_reduced"])


if __name__ == "__main__":
    unittest.main()

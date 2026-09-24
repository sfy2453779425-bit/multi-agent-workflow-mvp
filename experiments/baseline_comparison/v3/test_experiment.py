import unittest

try:
    from experiments.baseline_comparison.v3 import experiment
except ImportError:
    experiment = None


class ExperimentToolTests(unittest.TestCase):
    def test_experiment_module_exists(self):
        self.assertIsNotNone(experiment, "v3 experiment tools have not been implemented")

    @unittest.skipIf(experiment is None, "v3 experiment tools have not been implemented")
    def test_codex_parser_preserves_final_text_and_usage(self):
        raw = (
            '{"type":"thread.started","thread_id":"t1"}\n'
            '{"type":"item.completed","item":{"type":"agent_message","text":"Answer  "}}\n'
            '{"type":"turn.completed","status":"completed","usage":{"input_tokens":9,"output_tokens":4}}\n'
        )
        result = experiment.parse_codex_output(raw)
        self.assertEqual(result["text"], "Answer  ")
        self.assertEqual(result["model_returned"], "not_available_cli")
        self.assertEqual(result["usage"]["output_tokens"], 4)
        self.assertEqual(result["finish_reason"], "completed")

    @unittest.skipIf(experiment is None, "v3 experiment tools have not been implemented")
    def test_claude_parser_uses_result_without_rewriting(self):
        raw = r'{"result":"\n완성된 답변  ","modelUsage":{"claude-opus-5-5":{"outputTokens":7}},"usage":{"output_tokens":7},"stop_reason":"end_turn"}'
        result = experiment.parse_claude_output(raw)
        self.assertEqual(result["text"], "\n완성된 답변  ")
        self.assertEqual(result["model_returned"], ["claude-opus-5-5"])
        self.assertEqual(result["usage"]["output_tokens"], 7)
        self.assertEqual(result["finish_reason"], "end_turn")

    @unittest.skipIf(experiment is None, "v3 experiment tools have not been implemented")
    def test_only_transport_failures_are_retryable(self):
        self.assertTrue(experiment.retryable_transport_error("request timed out"))
        self.assertTrue(experiment.retryable_transport_error("HTTP 429 rate limited"))
        self.assertTrue(experiment.retryable_transport_error("HTTP 503 unavailable"))
        self.assertFalse(experiment.retryable_transport_error("HTTP 401 unauthorized"))
        self.assertFalse(experiment.retryable_transport_error("empty model response"))

    @unittest.skipIf(experiment is None, "v3 experiment tools have not been implemented")
    def test_schedule_has_each_case_run_system_once_in_stable_order(self):
        rows = experiment.build_schedule(["case-a", "case-b"], ["GPT-CLI", "Claude-CLI", "Builder"], 2)
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0], {"schedule_index": 1, "case_id": "case-a", "run": 1, "system": "GPT-CLI"})
        self.assertEqual(rows[-1], {"schedule_index": 12, "case_id": "case-b", "run": 2, "system": "Builder"})
        self.assertEqual(len({(row["case_id"], row["run"], row["system"]) for row in rows}), 12)


if __name__ == "__main__":
    unittest.main()

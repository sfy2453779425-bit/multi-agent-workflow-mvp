import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from experiments.ac_formal_v2.cli_gpt.run_gpt_cli import (
    extract_codex_output,
    retryable_cli_failure,
    _clean_env,
)
from experiments.ac_formal_v2.import_cli import claude_model_name, claude_text, _jsonl_records
from experiments.ac_formal_v2.common import PROVIDERS, build_schedule


class CliCollectionTests(unittest.TestCase):
    def test_schedule_uses_gpt6_astra_for_all_gpt_calls(self):
        self.assertIn(("gpt", "gpt-6-astra"), PROVIDERS)
        rows = [row for row in build_schedule() if row["provider"] == "gpt"]
        self.assertEqual(len(rows), 18)
        self.assertTrue(all(row["model_requested"] == "gpt-6-astra" for row in rows))

    def test_codex_jsonl_extracts_final_text_and_usage(self):
        stdout = "\n".join((
            '{"type":"item.completed","item":{"type":"agent_message","text":"final answer"}}',
            '{"type":"turn.completed","usage":{"input_tokens":12,"output_tokens":7},"status":"completed"}',
        ))
        result = extract_codex_output(stdout)
        self.assertEqual(result["raw_text"], "final answer")
        self.assertEqual(result["usage"]["output_tokens"], 7)
        self.assertEqual(result["finish_reason"], "completed")

    def test_only_transport_failures_are_retryable(self):
        self.assertTrue(retryable_cli_failure("connection timed out"))
        self.assertTrue(retryable_cli_failure("HTTP 503 service unavailable"))
        self.assertTrue(retryable_cli_failure("HTTP 429 too many requests"))
        self.assertFalse(retryable_cli_failure("invalid JSON in final answer"))
        self.assertFalse(retryable_cli_failure("HTTP 401 unauthorized"))

    def test_gpt_environment_excludes_api_keys(self):
        home = Path("C:/temporary/codex-home")
        env = _clean_env(home)
        self.assertEqual(env["CODEX_HOME"], str(home))
        self.assertTrue({"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"}.isdisjoint(env))

    def test_claude_raw_cli_json_preserves_final_text_and_model(self):
        raw = {
            "result": "reply text",
            "modelUsage": {"claude-opus-5-5": {"inputTokens": 9, "outputTokens": 5}},
        }
        self.assertEqual(claude_text(raw), "reply text")
        self.assertEqual(claude_model_name(raw), "claude-opus-5-5")

    def test_import_stops_on_missing_or_empty_log(self):
        with TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing.jsonl"
            with self.assertRaises(RuntimeError):
                _jsonl_records(missing)
            missing.touch()
            with self.assertRaises(RuntimeError):
                _jsonl_records(missing)


if __name__ == "__main__":
    unittest.main()

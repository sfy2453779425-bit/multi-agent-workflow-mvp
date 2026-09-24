import unittest

from experiments.ac_formal_v2.collect import (
    PARSE_OK,
    as_completed,
    _base_artifact,
    build_anthropic_payload,
    build_openai_payload,
    build_schedule,
    extract_anthropic_text,
    extract_openai_text,
    is_retryable_status,
    is_transport_failure,
    prepare_frozen,
)


class CollectionToolTests(unittest.TestCase):
    def test_collection_imports_shared_runtime_symbols(self):
        self.assertEqual(PARSE_OK, "PARSE_OK")
        self.assertTrue(callable(as_completed))

    def test_cli_prepare_function_is_importable(self):
        self.assertTrue(callable(prepare_frozen))

    def test_schedule_is_frozen_and_contains_54_unique_cells(self):
        first = build_schedule(seed=20260924)
        second = build_schedule(seed=20260924)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 54)
        self.assertEqual(
            len({(row["case_id"], row["provider"], row["run_id"]) for row in first}),
            54,
        )
        self.assertTrue(all(row["schedule_seed"] == 20260924 for row in first))
        for provider in ("deepseek", "gpt", "claude"):
            worker_rows = [row for row in first if row["provider"] == provider]
            self.assertEqual(len(worker_rows), 18)
            self.assertEqual(
                [row["run_id"] for row in worker_rows],
                [run_id for run_id in (1, 2, 3) for _ in range(6)],
            )

    def test_provider_payloads_preserve_canonical_user_text(self):
        messages = [{"role": "user", "content": "canonical exact text\nline 2"}]
        gpt = build_openai_payload("gpt-5.6", messages, 1024, "none")
        claude = build_anthropic_payload("claude-opus-5-5", messages, 1024)
        self.assertEqual(gpt["input"][0]["content"], messages[0]["content"])
        self.assertEqual(claude["messages"][0]["content"], messages[0]["content"])
        self.assertNotIn("temperature", gpt)
        self.assertNotIn("top_p", gpt)
        self.assertNotIn("thinking", claude)

    def test_extractors_read_only_visible_text(self):
        openai = {"output": [{"type": "message", "content": [{"type": "output_text", "text": "ok"}]}]}
        anthropic = {"content": [{"type": "text", "text": "ok"}]}
        self.assertEqual(extract_openai_text(openai), "ok")
        self.assertEqual(extract_anthropic_text(anthropic), "ok")
        self.assertEqual(extract_openai_text({"output": [{"type": "reasoning", "summary": []}]}), "")

    def test_only_network_retryable_statuses_are_retried(self):
        self.assertTrue(is_retryable_status(429))
        self.assertTrue(is_retryable_status(503))
        self.assertFalse(is_retryable_status(400))
        self.assertFalse(is_retryable_status(200))
        self.assertTrue(is_transport_failure("NETWORK_FAILED", None))
        self.assertTrue(is_transport_failure("HTTP_FAILED", 503))
        self.assertFalse(is_transport_failure("HTTP_FAILED", 400))

    def test_base_artifact_declares_provider_format_and_payload_fields(self):
        row = {"provider": "gpt", "model_requested": "gpt-5.6", "run_id": 1}
        prompt = {"case_id": "SMOKE01", "case_type": "synthetic", "case_hash": "case", "prompt_text_hash": "prompt"}
        artifact = _base_artifact(row=row, prompt=prompt, provider="gpt", smoke=True)
        self.assertEqual(artifact["api_format"], "responses")
        self.assertIn("provider_payload", artifact)
        self.assertIn("raw_model_text_hash", artifact)


if __name__ == "__main__":
    unittest.main()

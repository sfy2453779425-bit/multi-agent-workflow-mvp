import sys
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from agent_builder.local_llm import LocalLLMNode, LocalLLMNodeConfig  # noqa: E402
from experiments.gpu_llm.local_llm_api_server import (  # noqa: E402
    GenerateRequest,
    build_generate_response,
    parse_generate_payload,
)


class LocalLLMApiServerTest(unittest.TestCase):
    def test_local_llm_node_replays_downloaded_gpu_result(self):
        node = LocalLLMNode(
            LocalLLMNodeConfig(
                enabled=True,
                provider="replay",
                model="Qwen/Qwen2.5-1.5B-Instruct",
                replay_path=str(
                    ROOT
                    / "_local_artifacts"
                    / "gpu_results"
                    / "gpu_llm_results"
                    / "single_Qwen_Qwen2.5-1.5B-Instruct_20260603_185728.json"
                ),
            )
        )

        result = node.run({"workflow_name": "Outfit Recommendation Workflow"})

        self.assertEqual("replay", result.provider)
        self.assertEqual("Qwen/Qwen2.5-1.5B-Instruct", result.model)
        self.assertIn("[Local LLM Node - GPU Replay]", result.text)
        self.assertIn("Qingdao has a subtropical humid climate", result.text)
        self.assertEqual(74.385, result.metrics["tokens_per_second"])

    def test_parse_generate_payload_normalizes_optional_values(self):
        request = parse_generate_payload(
            {
                "model": "Qwen/Qwen2.5-1.5B-Instruct",
                "role": "compose",
                "prompt": "Summarize the workflow result.",
                "context": {"workflow_name": "Outfit Recommendation Workflow"},
            }
        )

        self.assertEqual(
            GenerateRequest(
                model="Qwen/Qwen2.5-1.5B-Instruct",
                role="compose",
                prompt="Summarize the workflow result.",
                context={"workflow_name": "Outfit Recommendation Workflow"},
                max_new_tokens=220,
                temperature=0.2,
                adapter_path="",
            ),
            request,
        )

    def test_build_generate_response_matches_local_llm_node_contract(self):
        request = GenerateRequest(
            model="Qwen/Qwen2.5-1.5B-Instruct",
            role="compose",
            prompt="prompt",
            context={"workflow_name": "Customer Support Ticket Workflow"},
            max_new_tokens=64,
            temperature=0.1,
            adapter_path="lora_outputs/workflow_builder_v2",
        )

        response = build_generate_response(
            request=request,
            answer="ranked workflow answer",
            infer_seconds=1.25,
            generated_tokens=80,
            peak_memory_mb=3040.8,
            device="cuda:0",
        )

        self.assertEqual("ranked workflow answer", response["answer"])
        self.assertEqual("Qwen/Qwen2.5-1.5B-Instruct", response["model"])
        self.assertEqual("compose", response["role"])
        self.assertEqual("remote_local_llm", response["provider"])
        self.assertEqual(64.0, response["metrics"]["tokens_per_second"])
        self.assertEqual(3040.8, response["metrics"]["peak_memory_mb"])
        self.assertEqual("lora_outputs/workflow_builder_v2", response["adapter_path"])

    def test_builder_demo_accepts_local_llm_config_file(self):
        completed = subprocess.run(
            [
                sys.executable,
                "builder_demo.py",
                "--workflow",
                "--local-llm-config",
                "configs/local_llm_node.mock.json",
                "--user",
                "user_a",
                "Seoul tomorrow casual outfit recommendation",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

        self.assertEqual(0, completed.returncode, completed.stdout)
        self.assertIn("Workflow Trace (7 Nodes)", completed.stdout)
        self.assertIn("Local LLM Node", completed.stdout)
        self.assertIn("[Local LLM Node]", completed.stdout)

    def test_builder_demo_accepts_replay_local_llm_config_file(self):
        completed = subprocess.run(
            [
                sys.executable,
                "builder_demo.py",
                "--workflow",
                "--local-llm-config",
                "configs/local_llm_node.replay.json",
                "--user",
                "user_a",
                "Seoul tomorrow casual outfit recommendation",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

        self.assertEqual(0, completed.returncode, completed.stdout)
        self.assertIn("Workflow Trace (7 Nodes)", completed.stdout)
        self.assertIn("Local LLM Node", completed.stdout)
        self.assertIn("GPU Replay", completed.stdout)


if __name__ == "__main__":
    unittest.main()

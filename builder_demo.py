import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from agent_builder import AgentBuilderEngine, MultiAgentWorkflowEngine  # noqa: E402


DEFAULT_CONFIGS = [
    ROOT / "configs" / "outfit_agent.json",
    ROOT / "configs" / "travel_pack_agent.json",
    ROOT / "configs" / "commute_agent.json",
]
DEFAULT_WORKFLOW_CONFIG = ROOT / "configs" / "outfit_workflow.json"


def run_one(config_path: Path, query: str | None, user_id: str) -> None:
    engine = AgentBuilderEngine(config_path)
    result = engine.run(query, user_id=user_id)

    print("=" * 64)
    print(f"Config: {config_path.name}")
    print(f"Agent: {result.agent_name}")
    print()
    print("Trace")
    for index, step in enumerate(result.trace, start=1):
        print(f"{index}. {step.name}: {step.detail}")
    print()
    print("Answer")
    print(result.answer)
    print()


def run_workflow(config_path: Path, query: str | None, user_id: str) -> None:
    engine = MultiAgentWorkflowEngine(config_path)
    result = engine.run(query, user_id=user_id)

    print("=" * 64)
    print(f"Workflow Config: {config_path.name}")
    print(f"Workflow: {result.workflow_name}")
    print()
    print("Multi-Agent Trace")
    for index, step in enumerate(result.trace, start=1):
        print(f"{index}. {step.name}: {step.detail}")
    print()
    print("Answer")
    print(result.answer)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the same Agent Builder engine with different JSON configs."
    )
    parser.add_argument("query", nargs="?", default=None)
    parser.add_argument("--config", default=None, help="Path to one agent config JSON.")
    parser.add_argument("--workflow-config", default=None, help="Path to one workflow config JSON.")
    parser.add_argument("--user", default="user_a", help="user_a or user_b")
    parser.add_argument(
        "--workflow",
        action="store_true",
        help="Run the multi-agent workflow MVP.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all demo configs to prove config switching.",
    )
    args = parser.parse_args()

    if args.workflow:
        workflow_config = Path(args.workflow_config) if args.workflow_config else DEFAULT_WORKFLOW_CONFIG
        if not workflow_config.is_absolute():
            workflow_config = ROOT / workflow_config
        run_workflow(workflow_config, args.query, args.user)
        return

    if args.all:
        for config in DEFAULT_CONFIGS:
            run_one(config, args.query, args.user)
        return

    config_path = Path(args.config) if args.config else DEFAULT_CONFIGS[0]
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    run_one(config_path, args.query, args.user)


if __name__ == "__main__":
    main()

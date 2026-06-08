import argparse
import json
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from agent_builder import AgentBuilderEngine, MultiAgentWorkflowEngine, TemplateWorkflowBuilder  # noqa: E402


DEFAULT_CONFIGS = [
    ROOT / "configs" / "outfit_agent.json",
]
DEFAULT_WORKFLOW_CONFIG = ROOT / "configs" / "outfit_workflow.json"
DEFAULT_BUILDER_TEMPLATE = ROOT / "configs" / "builder_templates" / "outfit_recommendation_template.json"
BUILDER_TEMPLATE_DIR = ROOT / "configs" / "builder_templates"


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


def load_local_llm_config(config_path: Path | None) -> dict | None:
    if config_path is None:
        return None
    return json.loads(config_path.read_text(encoding="utf-8"))


def run_workflow(config_path: Path, query: str | None, user_id: str, local_llm_config: dict | None = None) -> None:
    engine = MultiAgentWorkflowEngine(config_path, local_llm_config=local_llm_config)
    result = engine.run(query, user_id=user_id)

    print("=" * 64)
    print(f"Workflow Config: {config_path.name}")
    print(f"Workflow: {result.workflow_name}")
    print()
    print(f"Workflow Trace ({len(result.trace)} Nodes)")
    for index, step in enumerate(result.trace, start=1):
        print(f"{index}. {step.name}: {step.detail}")
    print()
    print("Answer")
    print(result.answer)
    print()


def show_builder_template(template_path: Path) -> None:
    builder = TemplateWorkflowBuilder(template_path)
    generated = builder.build_workflow_config()

    print("=" * 64)
    print("Builder Template Preview")
    print()
    print(builder.render_builder_summary())
    print()
    print("Builder Mapping")
    for index, row in enumerate(builder.mapping_rows(), start=1):
        print(f"{index}. {row['node']} [{row['category']}]")
        print(f"   Builder equivalent: {row['builder_equivalent']}")
        print(f"   Role: {row['role']}")
    print()
    print("Generated Workflow Config")
    print(json.dumps(generated, ensure_ascii=False, indent=2))
    print()


def run_generated_workflow(
    template_path: Path,
    query: str | None,
    user_id: str,
    local_llm_config: dict | None = None,
) -> None:
    builder = TemplateWorkflowBuilder(template_path)
    generated = builder.build_workflow_config(absolute_base_config=True)

    with tempfile.TemporaryDirectory(prefix="workflow_builder_") as temp_dir:
        generated_path = Path(temp_dir) / "generated_outfit_workflow.json"
        generated_path.write_text(
            json.dumps(generated, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        run_workflow(generated_path, query, user_id, local_llm_config=local_llm_config)


def list_builder_templates() -> None:
    print("=" * 64)
    print("Available Builder Templates")
    print()
    for path in sorted(BUILDER_TEMPLATE_DIR.glob("*.json")):
        builder = TemplateWorkflowBuilder(path)
        print(f"- {path.name}")
        print(f"  name: {builder.template_name}")
        print(f"  domain: {builder.template.get('target_domain', '')}")
        print(f"  default_query: {builder.template.get('default_query', '')}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the same Agent Builder engine with different JSON configs."
    )
    parser.add_argument("query", nargs="?", default=None)
    parser.add_argument("--config", default=None, help="Path to one agent config JSON.")
    parser.add_argument("--workflow-config", default=None, help="Path to one workflow config JSON.")
    parser.add_argument("--builder-template", default=None, help="Path to one builder template JSON.")
    parser.add_argument("--local-llm-config", default=None, help="Optional Local LLM Node config JSON.")
    parser.add_argument("--user", default="user_a", help="user_a or user_b")
    parser.add_argument(
        "--show-builder",
        action="store_true",
        help="Show the builder template, node palette, mapping, and generated workflow config.",
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List available builder templates.",
    )
    parser.add_argument(
        "--run-generated",
        action="store_true",
        help="Generate a workflow from the builder template and run it.",
    )
    parser.add_argument(
        "--workflow",
        action="store_true",
        help="Run the multi-agent workflow MVP.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all current outfit demo configs.",
    )
    args = parser.parse_args()

    builder_template = Path(args.builder_template) if args.builder_template else DEFAULT_BUILDER_TEMPLATE
    if not builder_template.is_absolute():
        builder_template = ROOT / builder_template

    local_llm_config_path = Path(args.local_llm_config) if args.local_llm_config else None
    if local_llm_config_path and not local_llm_config_path.is_absolute():
        local_llm_config_path = ROOT / local_llm_config_path
    local_llm_config = load_local_llm_config(local_llm_config_path)

    if args.list_templates:
        list_builder_templates()
        return

    if args.show_builder:
        show_builder_template(builder_template)
        return

    if args.run_generated:
        run_generated_workflow(builder_template, args.query, args.user, local_llm_config=local_llm_config)
        return

    if args.workflow:
        workflow_config = Path(args.workflow_config) if args.workflow_config else DEFAULT_WORKFLOW_CONFIG
        if not workflow_config.is_absolute():
            workflow_config = ROOT / workflow_config
        run_workflow(workflow_config, args.query, args.user, local_llm_config=local_llm_config)
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

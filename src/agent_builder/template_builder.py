import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TemplateValidation:
    ok: bool
    errors: list[str]
    warnings: list[str]


class TemplateWorkflowBuilder:
    """Builds executable workflow configs from a domain workflow template."""

    def __init__(self, template_path: str | Path):
        self.template_path = Path(template_path)
        self.template = self._load_json(self.template_path)
        self._node_by_id = {node["id"]: node for node in self.template.get("node_palette", [])}

    @property
    def template_name(self) -> str:
        return self.template["template_name"]

    @property
    def recommended_sequence(self) -> list[str]:
        return list(self.template.get("recommended_sequence", []))

    @property
    def available_nodes(self) -> list[dict[str, Any]]:
        return list(self.template.get("node_palette", []))

    def validate_node_ids(self, node_ids: list[str] | None = None) -> TemplateValidation:
        selected = self.recommended_sequence if node_ids is None else node_ids
        errors: list[str] = []
        warnings: list[str] = []

        unknown = [node_id for node_id in selected if node_id not in self._node_by_id]
        if unknown:
            errors.append("unknown nodes: " + ", ".join(unknown))

        duplicates = sorted({node_id for node_id in selected if selected.count(node_id) > 1})
        if duplicates:
            errors.append("duplicate nodes: " + ", ".join(duplicates))

        required = [node["id"] for node in self.available_nodes if node.get("required", False)]
        missing_required = [node_id for node_id in required if node_id not in selected]
        if missing_required:
            errors.append("missing required nodes: " + ", ".join(missing_required))

        if selected != self.recommended_sequence:
            warnings.append(
                "this MVP runner supports the recommended sequence only: "
                + " -> ".join(self.recommended_sequence)
            )

        return TemplateValidation(ok=not errors, errors=errors, warnings=warnings)

    def build_workflow_config(
        self,
        node_ids: list[str] | None = None,
        *,
        absolute_base_config: bool = False,
    ) -> dict[str, Any]:
        selected = self.recommended_sequence if node_ids is None else node_ids
        validation = self.validate_node_ids(selected)
        if not validation.ok:
            raise ValueError("; ".join(validation.errors))

        base_agent_config = self.template["base_agent_config"]
        if absolute_base_config:
            base_agent_config = str((self.template_path.parent / base_agent_config).resolve())

        agents = [
            {
                "id": node["id"],
                "name": node["name"],
                "role": node["role"],
                "builder_equivalent": node.get("builder_equivalent", ""),
            }
            for node in (self._node_by_id[node_id] for node_id in selected)
        ]

        return {
            "workflow_id": self.template["template_id"].replace("_builder_template", "_workflow"),
            "workflow_name": self.template["template_name"].replace("Template", "Workflow"),
            "description": self.template["description"],
            "base_agent_config": base_agent_config,
            "default_query": self.template["default_query"],
            "default_user_id": self.template.get("default_user_id", "user_a"),
            "agents": agents,
            "execution": {
                "type": "sequential",
                "order": selected,
                "generated_by": "TemplateWorkflowBuilder",
            },
            "question_agent": self.template.get("question_agent", {}),
        }

    def render_builder_summary(self, node_ids: list[str] | None = None) -> str:
        selected = self.recommended_sequence if node_ids is None else node_ids
        validation = self.validate_node_ids(selected)
        lines = [
            f"Template: {self.template_name}",
            f"Domain: {self.template.get('target_domain', '')}",
            "Selected Workflow:",
        ]
        for index, node_id in enumerate(selected, start=1):
            node = self._node_by_id.get(node_id, {"name": node_id, "role": "(unknown)"})
            lines.append(f"  {index}. {node['name']} - {node.get('role', '')}")
        lines.append("")
        lines.append("Validation: OK" if validation.ok else "Validation: ERROR")
        if validation.errors:
            lines.append("Errors:")
            lines.extend(f"  - {error}" for error in validation.errors)
        if validation.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {warning}" for warning in validation.warnings)
        return "\n".join(lines)

    def mapping_rows(self) -> list[dict[str, str]]:
        rows = []
        for node in self.available_nodes:
            rows.append(
                {
                    "node": node["name"],
                    "category": node.get("category", ""),
                    "builder_equivalent": node.get("builder_equivalent", ""),
                    "role": node.get("role", ""),
                }
            )
        return rows

    def _load_json(self, path: Path) -> Any:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

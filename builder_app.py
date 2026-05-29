import json
import sys
import tempfile
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from agent_builder import MultiAgentWorkflowEngine, TemplateWorkflowBuilder  # noqa: E402


TEMPLATE_DIR = ROOT / "configs" / "builder_templates"
DEFAULT_TEMPLATE_PATH = TEMPLATE_DIR / "outfit_recommendation_template.json"
STATIC_PREVIEW = ROOT / "workflow_builder_preview.html"


class BuilderPrototypeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Workflow Builder Prototype - Outfit Recommendation")
        self.root.geometry("1220x780")
        self.root.minsize(1020, 680)

        self.template_paths = self._discover_templates()
        self.template_labels = {self._template_label(path): path for path in self.template_paths}
        self.template_var = tk.StringVar(value=self._template_label(DEFAULT_TEMPLATE_PATH))
        self.builder = TemplateWorkflowBuilder(self.template_labels[self.template_var.get()])
        self.selected_node_ids = self.builder.recommended_sequence.copy()
        self.node_by_id = {node["id"]: node for node in self.builder.available_nodes}
        self.query_var = tk.StringVar(value=self.builder.template["default_query"])
        self.user_var = tk.StringVar(value=self.builder.template.get("default_user_id", "user_a"))
        self.status_var = tk.StringVar(value="Ready")

        self._configure_style()
        self._build_layout()
        self._refresh_all()

    def _configure_style(self) -> None:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 17, "bold"))
        style.configure("Hint.TLabel", font=("Microsoft YaHei UI", 10), foreground="#667085")
        style.configure("Section.TLabel", font=("Microsoft YaHei UI", 10, "bold"), foreground="#2557a7")
        style.configure("Accent.TButton", font=("Microsoft YaHei UI", 10, "bold"))

    def _build_layout(self) -> None:
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(main)
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text="Multi-Agent Workflow Builder Prototype",
            style="Title.TLabel",
        ).pack(anchor=tk.W)
        ttk.Label(
            header,
            text=(
                "This is a local MVP builder: select reusable nodes, generate a JSON workflow, "
                "then run the generated recommendation workflow."
            ),
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(4, 0))

        controls = ttk.Frame(main)
        controls.pack(fill=tk.X, pady=(14, 8))
        ttk.Label(controls, text="Template").pack(side=tk.LEFT)
        template_box = ttk.Combobox(
            controls,
            textvariable=self.template_var,
            values=list(self.template_labels),
            width=36,
            state="readonly",
        )
        template_box.pack(side=tk.LEFT, padx=(8, 12))
        template_box.bind("<<ComboboxSelected>>", lambda _event: self.load_selected_template())
        ttk.Label(controls, text="Demo query").pack(side=tk.LEFT)
        ttk.Entry(controls, textvariable=self.query_var, width=58).pack(side=tk.LEFT, padx=(8, 12), fill=tk.X, expand=True)
        ttk.Label(controls, text="User").pack(side=tk.LEFT)
        ttk.Combobox(
            controls,
            textvariable=self.user_var,
            values=["user_a", "user_b"],
            width=10,
            state="readonly",
        ).pack(side=tk.LEFT, padx=(8, 12))
        ttk.Button(controls, text="Open Static Preview", command=self.open_static_preview).pack(side=tk.LEFT)

        panes = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(panes)
        center = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(center, weight=1)
        panes.add(right, weight=2)

        self._build_palette(left)
        self._build_workflow(center)
        self._build_output(right)

        footer = ttk.Frame(main)
        footer.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(footer, textvariable=self.status_var, style="Hint.TLabel").pack(side=tk.LEFT)

    def _discover_templates(self) -> list[Path]:
        paths = sorted(TEMPLATE_DIR.glob("*.json"))
        if DEFAULT_TEMPLATE_PATH not in paths:
            paths.insert(0, DEFAULT_TEMPLATE_PATH)
        return paths

    def _template_label(self, path: Path) -> str:
        try:
            builder = TemplateWorkflowBuilder(path)
            return f"{builder.template['template_name']} ({path.name})"
        except Exception:
            return path.name

    def load_selected_template(self) -> None:
        template_path = self.template_labels[self.template_var.get()]
        self.builder = TemplateWorkflowBuilder(template_path)
        self.selected_node_ids = self.builder.recommended_sequence.copy()
        self.node_by_id = {node["id"]: node for node in self.builder.available_nodes}
        self.query_var.set(self.builder.template["default_query"])
        self.user_var.set(self.builder.template.get("default_user_id", "user_a"))
        self._write_detail("")
        self._refresh_all()

    def _build_palette(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Node Palette", style="Section.TLabel").pack(anchor=tk.W)
        self.palette_list = tk.Listbox(parent, height=12, exportselection=False)
        self.palette_list.pack(fill=tk.BOTH, expand=True, pady=(6, 8))
        ttk.Button(parent, text="Add Node", command=self.add_selected_node).pack(fill=tk.X)

        ttk.Label(parent, text="Selected Node Detail", style="Section.TLabel").pack(anchor=tk.W, pady=(14, 0))
        self.detail_text = scrolledtext.ScrolledText(parent, height=13, wrap=tk.WORD, font=("Consolas", 9))
        self.detail_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.detail_text.configure(state=tk.DISABLED)
        self.palette_list.bind("<<ListboxSelect>>", lambda _event: self._show_palette_detail())

    def _build_workflow(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Generated Workflow Canvas", style="Section.TLabel").pack(anchor=tk.W)
        self.workflow_list = tk.Listbox(parent, height=12, exportselection=False)
        self.workflow_list.pack(fill=tk.BOTH, expand=True, pady=(6, 8))
        self.workflow_list.bind("<<ListboxSelect>>", lambda _event: self._show_workflow_detail())

        buttons = ttk.Frame(parent)
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Remove", command=self.remove_selected_node).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(buttons, text="Up", command=lambda: self.move_selected_node(-1)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(buttons, text="Down", command=lambda: self.move_selected_node(1)).pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(parent, text="Reset Recommended Template", command=self.reset_template).pack(fill=tk.X, pady=(8, 0))
        ttk.Button(parent, text="Generate Workflow JSON", style="Accent.TButton", command=self.generate_json).pack(fill=tk.X, pady=(8, 0))
        ttk.Button(parent, text="Run Generated Workflow", style="Accent.TButton", command=self.run_generated_workflow).pack(fill=tk.X, pady=(8, 0))

    def _build_output(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Generated JSON / Execution Result", style="Section.TLabel").pack(anchor=tk.W)
        self.output_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, font=("Consolas", 9))
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.output_text.configure(state=tk.DISABLED)

    def _refresh_all(self) -> None:
        self.palette_list.delete(0, tk.END)
        for node in self.builder.available_nodes:
            self.palette_list.insert(tk.END, f"{node['id']} | {node['name']}")

        self.workflow_list.delete(0, tk.END)
        for index, node_id in enumerate(self.selected_node_ids, start=1):
            node = self.node_by_id[node_id]
            self.workflow_list.insert(tk.END, f"{index}. {node['name']}")

        self.generate_json()

    def _selected_palette_node_id(self) -> str | None:
        selection = self.palette_list.curselection()
        if not selection:
            return None
        return self.builder.available_nodes[selection[0]]["id"]

    def _selected_workflow_index(self) -> int | None:
        selection = self.workflow_list.curselection()
        if not selection:
            return None
        return selection[0]

    def _show_palette_detail(self) -> None:
        node_id = self._selected_palette_node_id()
        if not node_id:
            return
        self._write_detail(self._format_node_detail(self.node_by_id[node_id]))

    def _show_workflow_detail(self) -> None:
        index = self._selected_workflow_index()
        if index is None:
            return
        self._write_detail(self._format_node_detail(self.node_by_id[self.selected_node_ids[index]]))

    def _format_node_detail(self, node: dict[str, object]) -> str:
        return json.dumps(node, ensure_ascii=False, indent=2)

    def add_selected_node(self) -> None:
        node_id = self._selected_palette_node_id()
        if not node_id:
            messagebox.showinfo("Select node", "Please select one node from the palette.")
            return
        self.selected_node_ids.append(node_id)
        self._refresh_all()

    def remove_selected_node(self) -> None:
        index = self._selected_workflow_index()
        if index is None:
            messagebox.showinfo("Select node", "Please select one node in the workflow canvas.")
            return
        del self.selected_node_ids[index]
        self._refresh_all()

    def move_selected_node(self, delta: int) -> None:
        index = self._selected_workflow_index()
        if index is None:
            return
        new_index = index + delta
        if new_index < 0 or new_index >= len(self.selected_node_ids):
            return
        self.selected_node_ids[index], self.selected_node_ids[new_index] = (
            self.selected_node_ids[new_index],
            self.selected_node_ids[index],
        )
        self._refresh_all()
        self.workflow_list.selection_set(new_index)

    def reset_template(self) -> None:
        self.selected_node_ids = self.builder.recommended_sequence.copy()
        self._refresh_all()

    def generate_json(self) -> None:
        validation = self.builder.validate_node_ids(self.selected_node_ids)
        try:
            generated = self.builder.build_workflow_config(self.selected_node_ids)
            payload = json.dumps(generated, ensure_ascii=False, indent=2)
        except ValueError as exc:
            payload = str(exc)

        summary = self.builder.render_builder_summary(self.selected_node_ids)
        self._write_output(summary + "\n\nGenerated JSON:\n" + payload)
        self.status_var.set("Valid template" if validation.ok else "Invalid template: fix required nodes")

    def run_generated_workflow(self) -> None:
        validation = self.builder.validate_node_ids(self.selected_node_ids)
        if not validation.ok:
            messagebox.showerror("Invalid workflow", "\n".join(validation.errors))
            return
        generated = self.builder.build_workflow_config(
            self.selected_node_ids,
            absolute_base_config=True,
        )
        query = self.query_var.get().strip() or self.builder.template["default_query"]
        user_id = self.user_var.get()

        with tempfile.TemporaryDirectory(prefix="workflow_builder_") as temp_dir:
            generated_path = Path(temp_dir) / "generated_outfit_workflow.json"
            generated_path.write_text(
                json.dumps(generated, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            engine = MultiAgentWorkflowEngine(generated_path)
            result = engine.run(query, user_id=user_id)

        trace = "\n".join(f"{index}. {step.name}: {step.detail}" for index, step in enumerate(result.trace, start=1))
        self._write_output(
            "Generated workflow executed successfully.\n\n"
            f"Answer:\n{result.answer}\n\nTrace:\n{trace}"
        )
        self.status_var.set("Generated workflow executed")

    def open_static_preview(self) -> None:
        webbrowser.open(STATIC_PREVIEW.resolve().as_uri())

    def _write_detail(self, value: str) -> None:
        self.detail_text.configure(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert("1.0", value)
        self.detail_text.configure(state=tk.DISABLED)

    def _write_output(self, value: str) -> None:
        self.output_text.configure(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", value)
        self.output_text.configure(state=tk.DISABLED)


def main() -> None:
    root = tk.Tk()
    BuilderPrototypeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

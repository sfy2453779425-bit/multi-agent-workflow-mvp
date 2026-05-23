import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from agent_builder import MultiAgentWorkflowEngine  # noqa: E402


WORKFLOW_CONFIG = ROOT / "configs" / "outfit_workflow.json"
DEFAULT_QUERY = "다음 주에 칭다오 여행 가는데 옷 추천해줘"
USERS = {
    "user_a": "用户 A - 休闲 / 黑色 / 连帽卫衣",
    "user_b": "用户 B - 极简 / 白色 / 衬衫",
}


def merge_followup_query(previous_query: str, new_query: str) -> str:
    previous_query = previous_query.strip()
    new_query = new_query.strip()
    if previous_query and new_query:
        return f"{previous_query} {new_query}"
    return new_query or previous_query


class DesktopWorkflowApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Personalized Outfit Recommendation Workflow MVP")
        self.root.geometry("1120x760")
        self.root.minsize(940, 640)

        self.result_queue: queue.Queue[tuple[str, object, str]] = queue.Queue()
        self.conversation_context = ""
        self.running = False

        self.user_var = tk.StringVar(value="user_a")
        self.status_var = tk.StringVar(value="就绪")
        self.context_var = tk.StringVar(value="当前没有追问上下文")

        self._configure_style()
        self._build_layout()
        self._set_input(DEFAULT_QUERY)

    def _configure_style(self) -> None:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 17, "bold"))
        style.configure("Subtitle.TLabel", font=("Microsoft YaHei UI", 10), foreground="#5f6673")
        style.configure("Section.TLabel", font=("Microsoft YaHei UI", 10, "bold"), foreground="#C25710")
        style.configure("TButton", font=("Microsoft YaHei UI", 10))
        style.configure("Accent.TButton", font=("Microsoft YaHei UI", 10, "bold"))

    def _build_layout(self) -> None:
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(main)
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text="个性化穿搭推荐 Workflow 桌面版",
            style="Title.TLabel",
        ).pack(anchor=tk.W)
        ttk.Label(
            header,
            text="不使用浏览器和本地端口。输入自然语言后，6 个 Workflow Node 会按顺序执行；信息不足时先追问。",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(4, 0))

        controls = ttk.Frame(main)
        controls.pack(fill=tk.X, pady=(16, 8))
        ttk.Label(controls, text="购物记录用户").pack(side=tk.LEFT)
        user_box = ttk.Combobox(
            controls,
            textvariable=self.user_var,
            values=list(USERS.keys()),
            state="readonly",
            width=12,
        )
        user_box.pack(side=tk.LEFT, padx=(8, 8))
        ttk.Label(controls, textvariable=self.context_var, foreground="#6b7280").pack(side=tk.LEFT)

        input_frame = ttk.LabelFrame(main, text="用户输入 / 补充回答", padding=10)
        input_frame.pack(fill=tk.X)
        self.input_text = scrolledtext.ScrolledText(
            input_frame,
            height=4,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 11),
        )
        self.input_text.pack(fill=tk.X)

        button_bar = ttk.Frame(input_frame)
        button_bar.pack(fill=tk.X, pady=(10, 0))
        self.run_button = ttk.Button(
            button_bar,
            text="运行 Workflow",
            style="Accent.TButton",
            command=self.run_workflow,
        )
        self.run_button.pack(side=tk.LEFT)
        ttk.Button(button_bar, text="示例输入", command=self.load_example).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(button_bar, text="重置追问", command=self.reset_conversation).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(button_bar, textvariable=self.status_var, foreground="#6b7280").pack(side=tk.RIGHT)

        panes = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=3)
        panes.add(right, weight=2)

        ttk.Label(left, text="Workflow 输出", style="Section.TLabel").pack(anchor=tk.W)
        self.answer_text = scrolledtext.ScrolledText(
            left,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            background="#FFF9F3",
        )
        self.answer_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.answer_text.configure(state=tk.DISABLED)

        ttk.Label(right, text="执行 Trace", style="Section.TLabel").pack(anchor=tk.W)
        self.trace_text = scrolledtext.ScrolledText(
            right,
            wrap=tk.WORD,
            font=("Consolas", 9),
        )
        self.trace_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.trace_text.configure(state=tk.DISABLED)

    def load_example(self) -> None:
        self.conversation_context = ""
        self._set_input(DEFAULT_QUERY)
        self._set_context_label()
        self.run_button.configure(text="运行 Workflow")

    def reset_conversation(self) -> None:
        self.conversation_context = ""
        self._set_input("")
        self._set_context_label()
        self.run_button.configure(text="运行 Workflow")
        self.status_var.set("追问上下文已重置")

    def run_workflow(self) -> None:
        if self.running:
            return

        current_input = self.input_text.get("1.0", tk.END).strip()
        full_query = merge_followup_query(self.conversation_context, current_input)
        if not full_query:
            messagebox.showinfo("需要输入", "请输入请求，例如：옷 추천해줘")
            return

        user_id = self.user_var.get()
        self.running = True
        self.run_button.configure(state=tk.DISABLED)
        self.status_var.set("正在执行 Workflow...")
        self._write_answer("正在执行，请稍候...")
        self._write_trace("")

        thread = threading.Thread(
            target=self._worker_run,
            args=(full_query, user_id),
            daemon=True,
        )
        thread.start()
        self.root.after(120, self._poll_result)

    def _worker_run(self, full_query: str, user_id: str) -> None:
        try:
            engine = MultiAgentWorkflowEngine(WORKFLOW_CONFIG)
            result = engine.run(full_query, user_id=user_id)
            self.result_queue.put(("ok", result, full_query))
        except Exception as exc:
            self.result_queue.put(("error", exc, full_query))

    def _poll_result(self) -> None:
        try:
            status, payload, full_query = self.result_queue.get_nowait()
        except queue.Empty:
            self.root.after(120, self._poll_result)
            return

        self.running = False
        self.run_button.configure(state=tk.NORMAL)

        if status == "error":
            self.status_var.set("执行失败")
            self._write_answer(f"执行失败：\n{payload}")
            return

        result = payload
        self._write_answer(result.answer)
        self._write_trace(self._format_trace(result))

        if result.context.get("needs_clarification"):
            self.conversation_context = full_query
            self._set_input("")
            self.run_button.configure(text="提交补充信息")
            self.status_var.set("需要补充信息")
        else:
            self.conversation_context = ""
            self.run_button.configure(text="运行 Workflow")
            self.status_var.set("完成")
        self._set_context_label()

    def _format_trace(self, result: object) -> str:
        lines = [f"Workflow: {result.workflow_name}", ""]
        for index, step in enumerate(result.trace, start=1):
            lines.append(f"NODE {index:02d} | {step.name}")
            lines.append(f"  {step.detail}")
            if step.data:
                lines.append(f"  data: {step.data}")
            lines.append("")
        return "\n".join(lines)

    def _set_context_label(self) -> None:
        if self.conversation_context:
            self.context_var.set(f"追问上下文：{self.conversation_context}")
        else:
            self.context_var.set("当前没有追问上下文")

    def _set_input(self, value: str) -> None:
        self.input_text.delete("1.0", tk.END)
        if value:
            self.input_text.insert("1.0", value)

    def _write_answer(self, value: str) -> None:
        self.answer_text.configure(state=tk.NORMAL)
        self.answer_text.delete("1.0", tk.END)
        self.answer_text.insert("1.0", value)
        self.answer_text.configure(state=tk.DISABLED)

    def _write_trace(self, value: str) -> None:
        self.trace_text.configure(state=tk.NORMAL)
        self.trace_text.delete("1.0", tk.END)
        self.trace_text.insert("1.0", value)
        self.trace_text.configure(state=tk.DISABLED)


def main() -> None:
    root = tk.Tk()
    app = DesktopWorkflowApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

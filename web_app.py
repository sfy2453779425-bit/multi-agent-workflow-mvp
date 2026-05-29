import dataclasses
import html
import json
import mimetypes
import socket
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agent_builder import MultiAgentWorkflowEngine, TemplateWorkflowBuilder  # noqa: E402


TEMPLATE_DIR = ROOT / "configs" / "builder_templates"
STATIC_DIR = ROOT / "static"
DEFAULT_TEMPLATE = "outfit_recommendation_template.json"
USERS = {
    "user_a": "User A - casual / dark color / hoodie-heavy history",
    "user_b": "User B - minimal / white-gray / shirt-heavy history",
}
WEB_DEFAULT_QUERIES = {
    "outfit_recommendation_template.json": "다음 주에 칭다오 여행 가는데 캐주얼 옷 추천해줘",
    "commute_outfit_template.json": "내일 서울 출근용 포멀 옷 추천해줘",
}


# ---------------------------------------------------------------------------
# Template / workflow helpers
# ---------------------------------------------------------------------------


def template_paths() -> list[Path]:
    return sorted(TEMPLATE_DIR.glob("*_template.json"))


def safe_template_name(name: str | None) -> str:
    names = {path.name for path in template_paths()}
    if name in names:
        return str(name)
    return DEFAULT_TEMPLATE if DEFAULT_TEMPLATE in names else sorted(names)[0]


def load_builder(template_name: str) -> TemplateWorkflowBuilder:
    return TemplateWorkflowBuilder(TEMPLATE_DIR / safe_template_name(template_name))


def default_query_for(template_name: str, builder: TemplateWorkflowBuilder) -> str:
    return WEB_DEFAULT_QUERIES.get(template_name) or builder.template.get("default_query", "")


def generated_config(builder: TemplateWorkflowBuilder) -> dict[str, object]:
    return builder.build_workflow_config(absolute_base_config=True)


def run_generated_workflow(builder: TemplateWorkflowBuilder, query: str, user_id: str):
    config = generated_config(builder)
    with tempfile.TemporaryDirectory(prefix="builder_web_") as temp_dir:
        config_path = Path(temp_dir) / "generated_workflow.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        engine = MultiAgentWorkflowEngine(config_path)
        return engine.run(query, user_id=user_id), config


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def _json_default(obj):
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


def _safe(obj):
    """Recursively convert dataclasses / Paths so json.dumps works on `context`."""
    if dataclasses.is_dataclass(obj):
        return _safe(dataclasses.asdict(obj))
    if isinstance(obj, dict):
        return {str(k): _safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return [_safe(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


# ---------------------------------------------------------------------------
# API payloads
# ---------------------------------------------------------------------------


def api_templates() -> dict:
    items = []
    for path in template_paths():
        builder = TemplateWorkflowBuilder(path)
        items.append(
            {
                "file": path.name,
                "template_id": builder.template.get("template_id", ""),
                "name": builder.template_name,
                "target_domain": builder.template.get("target_domain", ""),
                "description": builder.template.get("description", ""),
                "default_query": default_query_for(path.name, builder),
            }
        )
    return {"templates": items, "default": safe_template_name(None)}


def api_template_detail(name: str) -> dict:
    builder = load_builder(name)
    by_id = {node["id"]: node for node in builder.available_nodes}
    sequence = builder.recommended_sequence
    nodes = []
    for index, node_id in enumerate(sequence, start=1):
        node = by_id[node_id]
        nodes.append(
            {
                "index": index,
                "id": node["id"],
                "name": node["name"],
                "role": node.get("role", ""),
                "category": node.get("category", ""),
                "builder_equivalent": node.get("builder_equivalent", ""),
                "inputs": node.get("inputs", []),
                "outputs": node.get("outputs", []),
                "required": bool(node.get("required", False)),
            }
        )
    palette = [
        {
            "id": node["id"],
            "name": node["name"],
            "role": node.get("role", ""),
            "category": node.get("category", ""),
            "builder_equivalent": node.get("builder_equivalent", ""),
            "inputs": node.get("inputs", []),
            "outputs": node.get("outputs", []),
            "required": bool(node.get("required", False)),
        }
        for node in builder.available_nodes
    ]
    validation = builder.validate_node_ids()
    config = generated_config(builder)
    return {
        "file": safe_template_name(name),
        "template_id": builder.template.get("template_id", ""),
        "name": builder.template_name,
        "target_domain": builder.template.get("target_domain", ""),
        "description": builder.template.get("description", ""),
        "default_query": default_query_for(safe_template_name(name), builder),
        "default_user_id": builder.template.get("default_user_id", "user_a"),
        "recommended_sequence": sequence,
        "nodes": nodes,
        "palette": palette,
        "mapping": builder.mapping_rows(),
        "validation": {
            "ok": validation.ok,
            "errors": list(validation.errors),
            "warnings": list(validation.warnings),
        },
        "generated_config": config,
    }


def api_users() -> dict:
    return {"users": [{"id": uid, "label": label} for uid, label in USERS.items()]}


def api_run(payload: dict) -> dict:
    template_name = safe_template_name(payload.get("template"))
    user_id = payload.get("user") or "user_a"
    builder = load_builder(template_name)
    query = (payload.get("query") or "").strip()
    if not query:
        query = default_query_for(template_name, builder)
    result, config = run_generated_workflow(builder, query, user_id)
    trace = [
        {"name": step.name, "detail": step.detail, "data": _safe(step.data)}
        for step in result.trace
    ]
    context = _safe(result.context)
    return {
        "template": template_name,
        "user": user_id,
        "query": query,
        "workflow_name": result.workflow_name,
        "answer": result.answer,
        "needs_clarification": bool(context.get("needs_clarification")),
        "trace": trace,
        "summary": {
            "city_display": context.get("city_display", ""),
            "date_label": context.get("date_label", ""),
            "weather_summary": context.get("weather_summary") or {},
            "shopping_analysis_summary": context.get("shopping_analysis_summary") or {},
            "ranked_items": context.get("ranked_items") or [],
            "executed_agents": context.get("executed_agents") or [],
            "executed_tools": context.get("executed_tools") or [],
            "missing_fields": context.get("missing_fields") or [],
            "next_question_field": context.get("next_question_field", ""),
            "clarification_message": context.get("clarification_message", ""),
        },
        "context": context,
        "generated_config": config,
    }


# ---------------------------------------------------------------------------
# Legacy server-rendered page (kept at /legacy for the older demo flow)
# ---------------------------------------------------------------------------


LEGACY_STYLE = """
:root { --bg:#f6f7f9;--panel:#fff;--text:#17202a;--muted:#667085;--line:#d9dee7;--soft:#eef2f7;--accent:#2563eb;--ok:#15803d;--warn:#b45309;--bad:#b91c1c; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text); font-family:Inter,"Noto Sans SC","Noto Sans KR",Arial,sans-serif; }
.shell { max-width:1180px; margin:0 auto; padding:24px; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:18px; box-shadow:0 1px 2px rgba(16,24,40,.04); margin-bottom:14px; }
h1 { margin:0 0 12px; font-size:24px; }
h2 { margin:0 0 12px; font-size:16px; }
a { color:var(--accent); }
pre { background:#111827; color:#f9fafb; padding:12px; border-radius:8px; overflow:auto; font-size:12px; }
.status { border-left:5px solid var(--ok); background:#f0fdf4; }
.status.warn { border-left-color:var(--warn); background:#fffbeb; }
.status.bad { border-left-color:var(--bad); background:#fef2f2; }
form { display:grid; gap:10px; }
label { font-size:12px; font-weight:800; color:var(--muted); }
select, textarea { width:100%; border:1px solid var(--line); border-radius:8px; padding:10px; font:inherit; }
textarea { min-height:90px; }
button { border:0; border-radius:8px; padding:10px 16px; background:var(--accent); color:#fff; font-weight:800; cursor:pointer; }
button.secondary { background:#334155; }
.buttons { display:flex; gap:10px; }
"""


def render_legacy_page(
    template_name: str | None = None,
    user_id: str = "user_a",
    query: str | None = None,
    action: str = "generate",
) -> bytes:
    selected_template = safe_template_name(template_name)
    builder = load_builder(selected_template)
    query_text = query if query and query.strip() else default_query_for(selected_template, builder)
    body_parts: list[str] = []
    body_parts.append('<div class="card"><h1>Legacy renderer</h1>'
                      '<p>New visualized front-end is at <a href="/">/</a>. '
                      'This page is kept for the old server-rendered demo flow.</p></div>')
    if action == "run":
        try:
            payload = api_run({"template": selected_template, "user": user_id, "query": query_text})
            body_parts.append('<div class="card status"><h2>Run answer</h2>'
                              f'<pre>{html.escape(payload["answer"])}</pre></div>')
            body_parts.append('<div class="card"><h2>Trace</h2><pre>'
                              + html.escape(json.dumps(payload["trace"], ensure_ascii=False, indent=2))
                              + '</pre></div>')
        except Exception as exc:
            body_parts.append(f'<div class="card status bad"><h2>Error</h2><p>{html.escape(str(exc))}</p></div>')
    else:
        detail = api_template_detail(selected_template)
        body_parts.append('<div class="card"><h2>Generated workflow JSON</h2><pre>'
                          + html.escape(json.dumps(detail["generated_config"], ensure_ascii=False, indent=2))
                          + '</pre></div>')

    options = "\n".join(
        f'<option value="{html.escape(p.name)}"{" selected" if p.name == selected_template else ""}>'
        f'{html.escape(TemplateWorkflowBuilder(p).template_name)}</option>'
        for p in template_paths()
    )
    users = "\n".join(
        f'<option value="{html.escape(uid)}"{" selected" if uid == user_id else ""}>{html.escape(label)}</option>'
        for uid, label in USERS.items()
    )

    page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>Legacy</title><style>{LEGACY_STYLE}</style></head>
<body><main class="shell">
<div class="card"><form method="post" action="/legacy">
<label>Template</label><select name="template">{options}</select>
<label>User</label><select name="user">{users}</select>
<label>Query</label><textarea name="query">{html.escape(query_text)}</textarea>
<div class="buttons">
<button class="secondary" name="action" value="generate">Generate JSON</button>
<button name="action" value="run">Run Workflow</button>
</div></form></div>
{''.join(body_parts)}
</main></body></html>
"""
    return page.encode("utf-8")


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


_INDEX_BYTES = None


def index_bytes() -> bytes:
    global _INDEX_BYTES
    if _INDEX_BYTES is None or True:  # always re-read during dev
        _INDEX_BYTES = (STATIC_DIR / "index.html").read_bytes()
    return _INDEX_BYTES


class VisualBuilderHandler(BaseHTTPRequestHandler):
    # GET ------------------------------------------------------------------
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/health":
            self._send(b"OK", content_type="text/plain; charset=utf-8")
            return
        if path == "/" or path == "/index.html":
            try:
                self._send(index_bytes())
            except FileNotFoundError:
                self._send(b"static/index.html missing", status=500, content_type="text/plain; charset=utf-8")
            return
        if path.startswith("/static/"):
            self._send_static(path[len("/static/"):])
            return
        if path == "/api/templates":
            self._send_json(api_templates())
            return
        if path == "/api/template":
            name = params.get("name", [None])[0]
            try:
                self._send_json(api_template_detail(name or DEFAULT_TEMPLATE))
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
            return
        if path == "/api/users":
            self._send_json(api_users())
            return
        if path == "/legacy":
            self._send(
                render_legacy_page(
                    template_name=params.get("template", [None])[0],
                    user_id=params.get("user", ["user_a"])[0],
                    query=params.get("query", [None])[0],
                )
            )
            return
        self._send(b"Not found", status=404, content_type="text/plain; charset=utf-8")

    # POST -----------------------------------------------------------------
    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b""

        if parsed.path == "/api/run":
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, status=400)
                return
            try:
                self._send_json(api_run(payload))
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return

        if parsed.path == "/legacy":
            form = parse_qs(raw.decode("utf-8"))
            self._send(
                render_legacy_page(
                    template_name=form.get("template", [None])[0],
                    user_id=form.get("user", ["user_a"])[0],
                    query=form.get("query", [""])[0],
                    action=form.get("action", ["generate"])[0],
                )
            )
            return

        self._send(b"Not found", status=404, content_type="text/plain; charset=utf-8")

    # Helpers --------------------------------------------------------------
    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, payload: bytes, status: int = 200, content_type: str = "text/html; charset=utf-8") -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
            return

    def _send_json(self, data: object, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False, default=_json_default).encode("utf-8")
        self._send(payload, status=status, content_type="application/json; charset=utf-8")

    def _send_static(self, rel_path: str) -> None:
        # prevent path traversal
        target = (STATIC_DIR / rel_path).resolve()
        if STATIC_DIR not in target.parents and target != STATIC_DIR:
            self._send(b"forbidden", status=403, content_type="text/plain; charset=utf-8")
            return
        if not target.exists() or not target.is_file():
            self._send(b"not found", status=404, content_type="text/plain; charset=utf-8")
            return
        content_type, _ = mimetypes.guess_type(target.name)
        content_type = content_type or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type = f"{content_type}; charset=utf-8"
        self._send(target.read_bytes(), content_type=content_type)


def ensure_port_available(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise OSError(f"port {port} is already in use; stop the old server or run: python web_app.py {port + 1}")


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    ensure_port_available(port)
    server = ThreadingHTTPServer(("127.0.0.1", port), VisualBuilderHandler)
    print(f"Visual Builder frontend: http://127.0.0.1:{port}", flush=True)
    print("Keep this window open while using the page.", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

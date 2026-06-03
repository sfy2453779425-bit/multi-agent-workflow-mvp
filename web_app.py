import dataclasses
import html
import json
import mimetypes
import re
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
CONTEXT_OPTIONS = {
    "outfit_recommendation": {
        "label": {
            "ko": "3. 사용자 (쇼핑 이력)",
            "zh": "3. 用户 (购物历史)",
        },
        "query_label": {
            "ko": "4. 사용자 입력",
            "zh": "4. 用户输入",
        },
        "options": [
            {
                "id": "user_a",
                "label": {
                    "ko": "User A - casual / dark color / hoodie-heavy history",
                    "zh": "User A - 休闲 / 深色 / 连帽衫购买历史",
                },
            },
            {
                "id": "user_b",
                "label": {
                    "ko": "User B - minimal / white-gray / shirt-heavy history",
                    "zh": "User B - 极简 / 白灰色 / 衬衫购买历史",
                },
            },
        ],
    },
    "presentation_planning": {
        "label": {
            "ko": "3. 발표 조건",
            "zh": "3. 发表场景",
        },
        "query_label": {
            "ko": "4. 발표 요청",
            "zh": "4. 发表需求",
        },
        "options": [
            {
                "id": "user_a",
                "label": {
                    "ko": "15분 최종 발표 / 교수 질문 대비",
                    "zh": "15 分钟最终发表 / 准备教授提问",
                },
            },
            {
                "id": "user_b",
                "label": {
                    "ko": "전시회 심사 발표 / 차별점 강조",
                    "zh": "展会评审发表 / 强调项目差异点",
                },
            },
        ],
    },
    "customer_support": {
        "label": {
            "ko": "3. 고객/채널 조건",
            "zh": "3. 客户/渠道条件",
        },
        "query_label": {
            "ko": "4. 고객 문의 내용",
            "zh": "4. 客户问题内容",
        },
        "options": [
            {
                "id": "user_a",
                "label": {
                    "ko": "일반 고객 / 웹 채널 / 배송 문의",
                    "zh": "普通客户 / 网页渠道 / 配送问题",
                },
            },
            {
                "id": "user_b",
                "label": {
                    "ko": "VIP 고객 / 앱 채널 / 환불·계정 문의",
                    "zh": "VIP 客户 / App 渠道 / 退款或账号问题",
                },
            },
        ],
    },
}
WEB_DEFAULT_QUERIES = {
    "presentation_planning_template.json": "Prepare a 15-minute presentation outline about Harness Engineering and Multi-Agent Workflow Builder MVP.",
    "customer_support_ticket_template.json": "Customer says the delivery is late and asks whether the order can be refunded.",
    "outfit_recommendation_template.json": "다음 주에 칭다오 여행 가는데 캐주얼 옷 추천해줘",
    "commute_outfit_template.json": "내일 서울 출근용 포멀 옷 추천해줘",
}
BUILDER_PRESETS = [
    {
        "id": "travel_recommendation",
        "template": "outfit_recommendation_template.json",
        "label": {
            "ko": "여행/개인화 추천 Workflow",
            "zh": "旅行/个性化推荐 Workflow",
        },
        "default_workflow_name": "Custom Travel Recommendation Workflow",
    },
    {
        "id": "commute_recommendation",
        "template": "commute_outfit_template.json",
        "label": {
            "ko": "출근/통근 추천 Workflow",
            "zh": "通勤/上班推荐 Workflow",
        },
        "default_workflow_name": "Custom Commute Recommendation Workflow",
    },
    {
        "id": "presentation_planning",
        "template": "presentation_planning_template.json",
        "label": {
            "ko": "발표 기획 Workflow",
            "zh": "发表规划 Workflow",
        },
        "default_workflow_name": "Custom Presentation Planning Workflow",
    },
    {
        "id": "customer_support",
        "template": "customer_support_ticket_template.json",
        "label": {
            "ko": "고객 문의 분류 Workflow",
            "zh": "客服工单分流 Workflow",
        },
        "default_workflow_name": "Custom Customer Support Workflow",
    },
]


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


def context_options_for(builder: TemplateWorkflowBuilder) -> dict[str, object]:
    runtime_type = builder.template.get("runtime_type", "outfit_recommendation")
    return context_options_for_runtime(runtime_type)


def context_options_for_runtime(runtime_type: str) -> dict[str, object]:
    return CONTEXT_OPTIONS.get(runtime_type, CONTEXT_OPTIONS["outfit_recommendation"])


def run_generated_workflow(builder: TemplateWorkflowBuilder, query: str, user_id: str):
    config = generated_config(builder)
    with tempfile.TemporaryDirectory(prefix="builder_web_") as temp_dir:
        config_path = Path(temp_dir) / "generated_workflow.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        engine = MultiAgentWorkflowEngine(config_path)
        return engine.run(query, user_id=user_id), config


def run_workflow_config(config: dict[str, object], query: str, user_id: str):
    with tempfile.TemporaryDirectory(prefix="builder_workspace_") as temp_dir:
        config_path = Path(temp_dir) / "custom_workflow.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        engine = MultiAgentWorkflowEngine(config_path)
        return engine.run(query, user_id=user_id)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "custom"


def builder_preset_by_id(preset_id: str | None) -> dict[str, object]:
    for preset in BUILDER_PRESETS:
        if preset["id"] == preset_id:
            return preset
    return BUILDER_PRESETS[0]


def nodes_from_builder(
    builder: TemplateWorkflowBuilder,
    sequence: list[str] | None = None,
) -> list[dict[str, object]]:
    by_id = {node["id"]: node for node in builder.available_nodes}
    selected = builder.recommended_sequence if sequence is None else sequence
    nodes = []
    for index, node_id in enumerate(selected, start=1):
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
    return nodes


def palette_from_builder(builder: TemplateWorkflowBuilder) -> list[dict[str, object]]:
    return [
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
    sequence = builder.recommended_sequence
    nodes = nodes_from_builder(builder, sequence)
    palette = palette_from_builder(builder)
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
        "context_options": context_options_for(builder),
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
    options = CONTEXT_OPTIONS["outfit_recommendation"]["options"]
    return {
        "users": [
            {
                "id": option["id"],
                "label": option["label"]["ko"],
                "labels": option["label"],
            }
            for option in options
        ]
    }


def workflow_result_payload(
    *,
    template_name: str,
    user_id: str,
    query: str,
    result,
    config: dict[str, object],
    builder_mode: str = "template_library",
) -> dict:
    trace = [
        {"name": step.name, "detail": step.detail, "data": _safe(step.data)}
        for step in result.trace
    ]
    context = _safe(result.context)
    return {
        "template": template_name,
        "builder_mode": builder_mode,
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
            "summary_cards": context.get("summary_cards") or [],
            "runtime_type": context.get("runtime_type", ""),
        },
        "context": context,
        "generated_config": config,
    }


def api_builder_presets() -> dict:
    presets = []
    for preset in BUILDER_PRESETS:
        builder = load_builder(str(preset["template"]))
        runtime_type = builder.template.get("runtime_type", "outfit_recommendation")
        presets.append(
            {
                "id": preset["id"],
                "source_template": preset["template"],
                "label": preset["label"],
                "default_workflow_name": preset["default_workflow_name"],
                "runtime_type": runtime_type,
                "target_domain": builder.template.get("target_domain", ""),
                "description": builder.template.get("description", ""),
                "default_query": default_query_for(str(preset["template"]), builder),
                "default_user_id": builder.template.get("default_user_id", "user_a"),
                "context_options": context_options_for_runtime(runtime_type),
                "nodes": nodes_from_builder(builder),
            }
        )
    return {"presets": presets, "default": BUILDER_PRESETS[0]["id"]}


def api_builder_compose(payload: dict | None = None) -> dict:
    payload = payload or {}
    preset = builder_preset_by_id(payload.get("preset"))
    template_name = str(preset["template"])
    builder = load_builder(template_name)
    node_ids = payload.get("node_ids") or builder.recommended_sequence
    if not isinstance(node_ids, list):
        raise ValueError("node_ids must be a list")

    validation = builder.validate_node_ids(node_ids)
    if not validation.ok:
        raise ValueError("; ".join(validation.errors))

    workflow_name = (payload.get("workflow_name") or "").strip()
    if not workflow_name:
        workflow_name = str(preset["default_workflow_name"])

    description = (
        (payload.get("description") or "").strip()
        or f"Custom workflow composed in Builder Workspace from {template_name}."
    )
    config = builder.build_workflow_config(node_ids, absolute_base_config=True)
    config["workflow_id"] = f"custom_{preset['id']}_{slugify(workflow_name)}_workflow"
    config["workflow_name"] = workflow_name
    config["description"] = description
    config["execution"]["generated_by"] = "BuilderWorkspace"
    config["execution"]["builder_mode"] = "custom_workspace"
    config["execution"]["source_template"] = template_name
    config["builder_workspace"] = {
        "preset_id": preset["id"],
        "source_template": template_name,
        "selected_nodes": node_ids,
        "workflow_name": workflow_name,
    }

    runtime_type = config.get("runtime_type", "outfit_recommendation")
    return {
        "file": f"builder:{preset['id']}",
        "builder_mode": "custom_workspace",
        "source_template": template_name,
        "template_id": builder.template.get("template_id", ""),
        "name": workflow_name,
        "target_domain": builder.template.get("target_domain", ""),
        "description": description,
        "default_query": payload.get("query") or default_query_for(template_name, builder),
        "default_user_id": builder.template.get("default_user_id", "user_a"),
        "context_options": context_options_for_runtime(str(runtime_type)),
        "recommended_sequence": node_ids,
        "nodes": nodes_from_builder(builder, node_ids),
        "palette": palette_from_builder(builder),
        "mapping": builder.mapping_rows(),
        "validation": {
            "ok": validation.ok,
            "errors": list(validation.errors),
            "warnings": list(validation.warnings),
        },
        "generated_config": config,
    }


def api_builder_run(payload: dict) -> dict:
    detail = api_builder_compose(payload)
    config = detail["generated_config"]
    user_id = payload.get("user") or detail.get("default_user_id") or "user_a"
    query = (payload.get("query") or detail.get("default_query") or "").strip()
    result = run_workflow_config(config, query, user_id)
    return workflow_result_payload(
        template_name=str(detail["file"]),
        user_id=user_id,
        query=query,
        result=result,
        config=config,
        builder_mode="custom_workspace",
    )


def api_run(payload: dict) -> dict:
    template_name = safe_template_name(payload.get("template"))
    user_id = payload.get("user") or "user_a"
    builder = load_builder(template_name)
    query = (payload.get("query") or "").strip()
    if not query:
        query = default_query_for(template_name, builder)
    result, config = run_generated_workflow(builder, query, user_id)
    return workflow_result_payload(
        template_name=template_name,
        user_id=user_id,
        query=query,
        result=result,
        config=config,
    )


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
    context_options = context_options_for(builder)
    users = "\n".join(
        f'<option value="{html.escape(option["id"])}"{" selected" if option["id"] == user_id else ""}>'
        f'{html.escape(option["label"]["ko"])}</option>'
        for option in context_options["options"]
    )
    context_label = context_options["label"]["ko"]
    query_label = context_options["query_label"]["ko"]

    page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>Legacy</title><style>{LEGACY_STYLE}</style></head>
<body><main class="shell">
<div class="card"><form method="post" action="/legacy">
<label>Template</label><select name="template">{options}</select>
<label>{html.escape(context_label)}</label><select name="user">{users}</select>
<label>{html.escape(query_label)}</label><textarea name="query">{html.escape(query_text)}</textarea>
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
        if path == "/api/builder/presets":
            self._send_json(api_builder_presets())
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

        if parsed.path == "/api/builder/compose":
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, status=400)
                return
            try:
                self._send_json(api_builder_compose(payload))
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
            return

        if parsed.path == "/api/builder/run":
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, status=400)
                return
            try:
                self._send_json(api_builder_run(payload))
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


def console_notice(message: str) -> None:
    try:
        print(message, flush=True)
    except Exception:
        pass


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    ensure_port_available(port)
    server = ThreadingHTTPServer(("127.0.0.1", port), VisualBuilderHandler)
    console_notice(f"Visual Builder frontend: http://127.0.0.1:{port}")
    console_notice("Keep this window open while using the page.")
    server.serve_forever()


if __name__ == "__main__":
    main()

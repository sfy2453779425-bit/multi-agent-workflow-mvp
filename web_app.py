import html
import json
import socket
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from agent_builder import AgentBuilderEngine, MultiAgentWorkflowEngine  # noqa: E402


AGENT_CONFIGS = {
    "workflow_outfit": {
        "type": "workflow",
        "labels": {
            "ko": "의류 추천 Multi-Agent Workflow",
            "zh": "穿搭推荐 Multi-Agent Workflow",
        },
        "path": ROOT / "configs" / "outfit_workflow.json",
        "default_query": "서울 내일 날씨에 맞춰 내 스타일로 옷 추천해줘",
    },
    "outfit": {
        "type": "agent",
        "labels": {
            "ko": "개인화 의류 추천 Agent",
            "zh": "个性化穿搭推荐 Agent",
        },
        "path": ROOT / "configs" / "outfit_agent.json",
        "default_query": "서울 내일 날씨에 맞춰 내 스타일로 옷 추천해줘",
    },
    "travel": {
        "type": "agent",
        "labels": {
            "ko": "여행 준비물 추천 Agent",
            "zh": "旅行准备物推荐 Agent",
        },
        "path": ROOT / "configs" / "travel_pack_agent.json",
        "default_query": "서울 내일 여행 갈 때 챙길 물건 추천해줘",
    },
    "commute": {
        "type": "agent",
        "labels": {
            "ko": "통학/출근 준비 Agent",
            "zh": "通勤/上学准备 Agent",
        },
        "path": ROOT / "configs" / "commute_agent.json",
        "default_query": "서울 내일 학교 갈 때 뭐 챙겨야 해?",
    },
}

USERS = {
    "user_a": {
        "ko": "User A - 캐주얼 / 블랙 / 후드티",
        "zh": "用户 A - 休闲 / 黑色 / 连帽卫衣",
    },
    "user_b": {
        "ko": "User B - 미니멀 / 화이트 / 셔츠",
        "zh": "用户 B - 极简 / 白色 / 衬衫",
    },
}

DEFAULT_AGENT = "workflow_outfit"
DEFAULT_USER = "user_a"
DEFAULT_LANG = "ko"

LANGUAGES = {
    "ko": "한국어 UI",
    "zh": "中文 UI",
}

UI_TEXT = {
    "ko": {
        "html_lang": "ko",
        "eyebrow": "Configuration-driven AI Agent Builder MVP",
        "title": "설정 파일로 Agent와 Workflow를 실행하는 Builder Demo",
        "subtitle": "하나의 실행 엔진이 JSON 설정을 읽고, 여러 Agent를 순차 Workflow로 연결해 쇼핑 기록과 실시간 날씨 기반 추천을 생성합니다.",
        "language": "UI Language",
        "agent_config": "Demo Config",
        "shopping_user": "Shopping History User",
        "user_input": "User Input",
        "run": "Run Selected Agent",
        "metric_data": "Data",
        "metric_data_value": "weather + shopping",
        "metric_config": "Config",
        "metric_config_value": "JSON template",
        "metric_flow": "Flow",
        "metric_flow_value": "Parser -> Weather -> Shopping -> Recommend -> Compose",
        "agent_output": "Agent Output",
        "execution_trace": "Workflow Trace",
        "steps_badge": "5 agents",
        "loaded_config": "Loaded Config",
        "shopping_analysis": "Shopping History Analysis",
        "raw_trace": "Raw Trace",
    },
    "zh": {
        "html_lang": "zh-CN",
        "eyebrow": "配置驱动 AI Agent Builder MVP",
        "title": "通过配置文件运行 Agent 与 Workflow 的 Builder Demo",
        "subtitle": "同一套执行引擎读取 JSON 配置，把多个 Agent 按顺序连接成 Workflow，结合购物记录和实时天气生成推荐。",
        "language": "界面语言",
        "agent_config": "Demo 配置",
        "shopping_user": "购物记录用户",
        "user_input": "用户输入",
        "run": "运行所选 Agent",
        "metric_data": "数据",
        "metric_data_value": "天气 + 购物记录",
        "metric_config": "配置",
        "metric_config_value": "JSON 模板",
        "metric_flow": "流程",
        "metric_flow_value": "解析 -> 天气 -> 购物分析 -> 推荐 -> 输出",
        "agent_output": "Agent 输出",
        "execution_trace": "Workflow 执行流程",
        "steps_badge": "5 个 Agent",
        "loaded_config": "已加载配置",
        "shopping_analysis": "购物记录分析",
        "raw_trace": "原始执行记录",
    },
}


STYLE = """
:root {
  --bg: #f4f6f8;
  --panel: #ffffff;
  --text: #17202a;
  --muted: #65717d;
  --line: #d9e1e8;
  --soft: #f8fafc;
  --accent: #1f6f8b;
  --accent-dark: #18596f;
  --green: #2f7d68;
  --green-soft: #e8f5f1;
  --amber-soft: #fff7df;
  --shadow: 0 12px 30px rgba(24, 38, 53, 0.08);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Arial, "Malgun Gothic", sans-serif;
  color: var(--text);
  background: var(--bg);
}

.topbar {
  padding: 24px 32px 18px;
  background: var(--panel);
  border-bottom: 1px solid var(--line);
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--green);
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: 29px;
  line-height: 1.25;
}

.subtitle {
  max-width: 900px;
  margin: 10px 0 0;
  color: var(--muted);
  line-height: 1.55;
}

.shell {
  display: grid;
  grid-template-columns: minmax(330px, 430px) minmax(0, 1fr);
  gap: 20px;
  padding: 22px 32px 36px;
  align-items: start;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: var(--shadow);
}

.control,
.result {
  padding: 20px;
}

.control {
  position: sticky;
  top: 16px;
}

.field {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 8px;
  font-weight: 700;
  font-size: 14px;
}

select,
textarea {
  width: 100%;
  border: 1px solid #b7c2cc;
  border-radius: 6px;
  padding: 11px 12px;
  color: var(--text);
  background: var(--panel);
  font: inherit;
  line-height: 1.5;
}

select:focus,
textarea:focus {
  outline: 3px solid rgba(31, 111, 139, 0.16);
  border-color: var(--accent);
}

textarea {
  min-height: 116px;
  resize: vertical;
}

button {
  width: 100%;
  border: 0;
  border-radius: 6px;
  padding: 12px 14px;
  background: var(--accent);
  color: #fff;
  font-weight: 700;
  cursor: pointer;
}

button:hover {
  background: var(--accent-dark);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.metric {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
  background: var(--soft);
}

.metric strong {
  display: block;
  margin-bottom: 3px;
  font-size: 13px;
}

.metric span {
  color: var(--muted);
  font-size: 13px;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 10px;
}

.section-title h2 {
  margin: 0;
  font-size: 17px;
}

.badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 5px 9px;
  background: var(--green-soft);
  color: var(--green);
  font-size: 12px;
  font-weight: 700;
}

.answer {
  white-space: pre-wrap;
  line-height: 1.65;
  padding: 16px;
  background: var(--green-soft);
  border: 1px solid #bfe1d8;
  border-radius: 8px;
}

.trace {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.step {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  min-height: 126px;
  background: var(--soft);
}

.step h3 {
  margin: 0 0 8px;
  font-size: 15px;
}

.step p {
  margin: 0;
  color: var(--muted);
  line-height: 1.5;
  font-size: 13px;
}

.config {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  margin-top: 18px;
}

.config-box {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: var(--soft);
}

.config-box h3 {
  margin: 0 0 8px;
  font-size: 15px;
}

.config-box code {
  display: block;
  color: var(--muted);
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}

.raw {
  overflow: auto;
  margin-top: 12px;
  padding: 12px;
  border-radius: 6px;
  background: #17202a;
  color: #edf2f7;
  font-size: 12px;
  max-height: 260px;
}

.result-grid {
  display: grid;
  gap: 18px;
}

.error {
  padding: 14px;
  background: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 8px;
  color: #8a1f11;
}
@media (max-width: 980px) {
  .shell,
  .trace,
  .config {
    grid-template-columns: 1fr;
  }
  .topbar,
  .shell {
    padding-left: 18px;
    padding-right: 18px;
  }

  .control {
    position: static;
  }
}
"""


def selected(value: str, current: str) -> str:
    return " selected" if value == current else ""


def get_lang(lang: str) -> str:
    return lang if lang in UI_TEXT else DEFAULT_LANG


def escape_json(data: object) -> str:
    return html.escape(json.dumps(data, ensure_ascii=False, indent=2))


def get_agent_meta(agent_key: str) -> dict[str, object]:
    return AGENT_CONFIGS.get(agent_key, AGENT_CONFIGS[DEFAULT_AGENT])


def run_builder_agent(agent_key: str, user_id: str, query: str, lang: str) -> str:
    text = UI_TEXT[get_lang(lang)]
    meta = get_agent_meta(agent_key)
    if meta.get("type") == "workflow":
        engine = MultiAgentWorkflowEngine(meta["path"])
        result = engine.run(query, user_id=user_id)
        display_name = result.workflow_name
        base_config = engine.base_engine.config
        config_summary = {
            "workflow_config": str(Path(meta["path"]).relative_to(ROOT)),
            "workflow_name": result.workflow_name,
            "execution": engine.workflow_config.get("execution", {}),
            "agents": [agent.get("name") for agent in engine.workflow_config.get("agents", [])],
            "base_agent_config": str(engine.base_engine.config_path.relative_to(ROOT)),
            "tools": list(base_config.get("tools", {}).keys()),
        }
    else:
        engine = AgentBuilderEngine(meta["path"])
        result = engine.run(query, user_id=user_id)
        display_name = result.agent_name
        config_summary = {
            "config": str(Path(meta["path"]).relative_to(ROOT)),
            "agent_name": result.agent_name,
            "intent": engine.config.get("intent"),
            "tools": list(engine.config.get("tools", {}).keys()),
            "rules": [rule.get("name") for rule in engine.config.get("temperature_rules", [])],
        }

    trace_html = []
    for step in result.trace:
        trace_html.append(
            f"""
            <section class="step">
              <h3>{html.escape(step.name)}</h3>
              <p>{html.escape(step.detail)}</p>
            </section>
            """
        )

    shopping_summary = result.context.get("shopping_analysis_summary", {})
    raw = [
        {"name": step.name, "detail": step.detail, "data": step.data}
        for step in result.trace
    ]

    return f"""
      <div class="result-grid">
        <section>
          <div class="section-title">
            <h2>{html.escape(text["agent_output"])}</h2>
            <span class="badge">{html.escape(display_name)}</span>
          </div>
          <div class="answer">{html.escape(result.answer)}</div>
        </section>
        <section>
          <div class="section-title">
            <h2>{html.escape(text["execution_trace"])}</h2>
            <span class="badge">{html.escape(text["steps_badge"])}</span>
          </div>
          <div class="trace">{''.join(trace_html)}</div>
        </section>
        <section class="config">
          <div class="config-box">
            <h3>{html.escape(text["loaded_config"])}</h3>
            <code>{escape_json(config_summary)}</code>
          </div>
          <div class="config-box">
            <h3>{html.escape(text["shopping_analysis"])}</h3>
            <code>{escape_json(shopping_summary)}</code>
          </div>
        </section>
        <section>
          <div class="section-title">
            <h2>{html.escape(text["raw_trace"])}</h2>
          </div>
          <pre class="raw">{escape_json(raw)}</pre>
        </section>
      </div>
    """


def render_page(
    agent_key: str = DEFAULT_AGENT,
    user_id: str = DEFAULT_USER,
    lang: str = DEFAULT_LANG,
    query: str | None = None,
    result_html: str = "",
    error: str = "",
) -> bytes:
    lang = get_lang(lang)
    text = UI_TEXT[lang]
    meta = get_agent_meta(agent_key)
    if query is None:
        query = str(meta["default_query"])

    if error:
        result_html = f'<div class="error">{html.escape(error)}</div>'
    if not result_html:
        try:
            result_html = run_builder_agent(agent_key, user_id, query, lang)
        except Exception as exc:
            result_html = f'<div class="error">{html.escape(str(exc))}</div>'

    language_options = "\n".join(
        f'<option value="{html.escape(key)}"{selected(key, lang)}>{html.escape(label)}</option>'
        for key, label in LANGUAGES.items()
    )
    agent_options = "\n".join(
        (
            f'<option value="{html.escape(key)}"{selected(key, agent_key)}>'
            f'{html.escape(str(value["labels"][lang]))}</option>'
        )
        for key, value in AGENT_CONFIGS.items()
    )
    user_options = "\n".join(
        f'<option value="{html.escape(key)}"{selected(key, user_id)}>{html.escape(labels[lang])}</option>'
        for key, labels in USERS.items()
    )

    page = f"""
<!doctype html>
<html lang="{html.escape(text["html_lang"])}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agent Builder MVP</title>
  <style>{STYLE}</style>
</head>
<body>
  <header class="topbar">
    <p class="eyebrow">{html.escape(text["eyebrow"])}</p>
    <h1>{html.escape(text["title"])}</h1>
    <p class="subtitle">{html.escape(text["subtitle"])}</p>
  </header>
  <main class="shell">
    <section class="panel control">
      <form method="post">
        <div class="field">
          <label for="lang">{html.escape(text["language"])}</label>
          <select id="lang" name="lang">{language_options}</select>
        </div>
        <div class="field">
          <label for="agent">{html.escape(text["agent_config"])}</label>
          <select id="agent" name="agent">{agent_options}</select>
        </div>
        <div class="field">
          <label for="user">{html.escape(text["shopping_user"])}</label>
          <select id="user" name="user">{user_options}</select>
        </div>
        <div class="field">
          <label for="query">{html.escape(text["user_input"])}</label>
          <textarea id="query" name="query">{html.escape(query)}</textarea>
        </div>
        <button type="submit">{html.escape(text["run"])}</button>
      </form>
      <div class="metric-grid">
        <div class="metric"><strong>{html.escape(text["metric_data"])}</strong><span>{html.escape(text["metric_data_value"])}</span></div>
        <div class="metric"><strong>{html.escape(text["metric_config"])}</strong><span>{html.escape(text["metric_config_value"])}</span></div>
        <div class="metric"><strong>{html.escape(text["metric_flow"])}</strong><span>{html.escape(text["metric_flow_value"])}</span></div>
      </div>
    </section>
    <section class="panel result">
      {result_html}
    </section>
  </main>
</body>
</html>
    """
    return page.encode("utf-8")


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        params = parse_qs(urlparse(self.path).query)
        lang = get_lang(params.get("lang", [DEFAULT_LANG])[0])
        agent_key = params.get("agent", [DEFAULT_AGENT])[0]
        user_id = params.get("user", [DEFAULT_USER])[0]
        self._send(render_page(agent_key=agent_key, user_id=user_id, lang=lang))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        form = parse_qs(body)
        lang = get_lang(form.get("lang", [DEFAULT_LANG])[0])
        agent_key = form.get("agent", [DEFAULT_AGENT])[0]
        user_id = form.get("user", [DEFAULT_USER])[0]
        query = form.get("query", [""])[0].strip()
        if not query:
            query = str(get_agent_meta(agent_key)["default_query"])

        try:
            result_html = run_builder_agent(agent_key, user_id, query, lang)
            error = ""
        except Exception as exc:
            result_html, error = "", str(exc)
        self._send(
            render_page(
                agent_key=agent_key,
                user_id=user_id,
                lang=lang,
                query=query,
                result_html=result_html,
                error=error,
            )
        )

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, payload: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def find_port(start: int) -> int:
    port = start
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1


def main() -> None:
    requested = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    port = find_port(requested)
    server = HTTPServer(("127.0.0.1", port), DemoHandler)
    print(f"Agent Builder MVP demo running at http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

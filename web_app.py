import html
import json
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import urllib.parse
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from agent_builder import AgentBuilderEngine, MultiAgentWorkflowEngine  # noqa: E402


AGENT_CONFIGS = {
    "workflow_outfit": {
        "type": "workflow",
        "labels": {
            "ko": "의류 추천 Workflow (6 Node)",
            "zh": "穿搭推荐 Workflow (6 Node)",
        },
        "path": ROOT / "configs" / "outfit_workflow.json",
        "default_query": "다음 주에 칭다오 여행 가는데 옷 추천해줘",
    },
    "outfit": {
        "type": "agent",
        "labels": {
            "ko": "개인화 의류 추천 (단일 Config)",
            "zh": "个性化穿搭推荐 (单 Config)",
        },
        "path": ROOT / "configs" / "outfit_agent.json",
        "default_query": "서울 내일 날씨에 맞춰 내 스타일로 옷 추천해줘",
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
        "eyebrow": "Personalized Outfit Recommendation Workflow MVP",
        "title": "JSON Workflow로 6개 Node를 조립한 개인화 의류 추천 Demo",
        "subtitle": "하나의 실행 엔진이 JSON 설정을 읽고, 6개 Workflow Node를 순차로 연결해 쇼핑 기록과 실시간 날씨 기반의 개인화 의류 추천을 생성합니다.",
        "language": "UI Language",
        "agent_config": "Demo Config",
        "shopping_user": "Shopping History User",
        "user_input": "User Input",
        "run": "Run Selected Workflow",
        "metric_data": "Data",
        "metric_data_value": "weather + shopping",
        "metric_config": "Config",
        "metric_config_value": "JSON template",
        "metric_flow": "Flow",
        "metric_flow_value": "Parser -> Question -> Weather -> Shopping -> Recommend -> Compose",
        "agent_output": "Workflow Output",
        "execution_trace": "Workflow Trace",
        "steps_badge": "6 Nodes",
        "loaded_config": "Loaded Config",
        "shopping_analysis": "Shopping History Analysis",
        "raw_trace": "Raw Trace",
        "followup_placeholder": "추가 답변을 입력하세요. 예: 칭다오 / 다음 주 / 여행",
        "hint_label": "TIP",
        "hint_text": "정보가 부족한 입력을 보내면 시스템이 도시 → 시간 → 목적 순으로 추가 질문합니다. 아래 예시를 눌러 시도해 보세요.",
        "preset_minimal_label": "최소 입력 (추가 질문 시연)",
        "preset_minimal_query": "옷 추천해줘",
        "preset_partial_label": "부분 입력",
        "preset_partial_query": "칭다오 옷 추천해줘",
        "preset_full_label": "전체 한 문장",
        "preset_full_query": "다음 주에 칭다오 여행 가는데 옷 추천해줘",
        "context_label": "이미 입력된 정보",
        "reset_label": "처음부터 다시",
    },
    "zh": {
        "html_lang": "zh-CN",
        "eyebrow": "Personalized Outfit Recommendation Workflow MVP",
        "title": "通过 JSON Workflow 组装 6 个 Node 的个性化穿搭推荐 Demo",
        "subtitle": "同一套执行引擎读取 JSON 配置，把 6 个 Workflow Node 顺序连接，结合购物记录和实时天气生成个性化穿搭推荐。",
        "language": "界面语言",
        "agent_config": "Demo 配置",
        "shopping_user": "购物记录用户",
        "user_input": "用户输入",
        "run": "运行所选 Workflow",
        "metric_data": "数据",
        "metric_data_value": "天气 + 购物记录",
        "metric_config": "配置",
        "metric_config_value": "JSON 模板",
        "metric_flow": "流程",
        "metric_flow_value": "解析 -> 追问 -> 天气 -> 购物分析 -> 推荐 -> 输出",
        "agent_output": "Workflow 输出",
        "execution_trace": "Workflow 执行流程",
        "steps_badge": "6 个 Node",
        "loaded_config": "已加载配置",
        "shopping_analysis": "购物记录分析",
        "raw_trace": "原始执行记录",
        "followup_placeholder": "请输入补充回答，例如：青岛 / 下周 / 旅行",
        "hint_label": "提示",
        "hint_text": "如果信息不足，系统会按 城市 → 时间 → 目的 顺序追问。点击下方示例可一键试用。",
        "preset_minimal_label": "最少输入（演示追问）",
        "preset_minimal_query": "옷 추천해줘",
        "preset_partial_label": "部分输入",
        "preset_partial_query": "칭다오 옷 추천해줘",
        "preset_full_label": "完整一句话",
        "preset_full_query": "다음 주에 칭다오 여행 가는데 옷 추천해줘",
        "context_label": "已输入信息",
        "reset_label": "重新开始",
    },
}


STYLE = """
:root {
  --bg: #fafafa;
  --panel: #ffffff;
  --text: #1a1a1a;
  --muted: #6b7280;
  --line: #e5e7eb;
  --soft: #f9fafb;
  --accent: #ED6F1B;
  --accent-dark: #C25710;
  --accent-soft: #FFF1E6;
  --accent-border: #F8C8A2;
  --output-bg: #FFF9F3;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Pretendard", "Noto Sans KR", "Malgun Gothic", -apple-system, BlinkMacSystemFont, Arial, sans-serif;
  color: var(--text);
  background: var(--bg);
  -webkit-font-smoothing: antialiased;
}

.container {
  max-width: 1080px;
  margin: 0 auto;
  padding: 0 24px;
  position: relative;
}

.header {
  padding: 28px 0 22px;
  background: var(--panel);
  border-bottom: 3px solid var(--accent);
}

.eyebrow {
  margin: 0;
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
}

h1 {
  margin: 6px 0 0;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: -0.3px;
}

.subtitle {
  max-width: 760px;
  margin: 8px 0 0;
  color: var(--muted);
  line-height: 1.55;
  font-size: 13.5px;
}

.lang-toggle {
  position: absolute;
  top: 0;
  right: 24px;
  font-size: 12px;
}

.lang-toggle a {
  color: var(--muted);
  text-decoration: none;
  padding: 4px 8px;
  border-radius: 6px;
}

.lang-toggle a:hover {
  color: var(--text);
}

main {
  padding: 28px 0 48px;
}

.tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.tab {
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color 0.15s ease, border-color 0.15s ease;
}

.tab:hover {
  color: var(--text);
}

.tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.input-card {
  padding: 18px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
}

.hint-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 12px;
  background: var(--accent-soft);
  border: 1px solid var(--accent-border);
  border-radius: 8px;
  font-size: 12.5px;
  color: var(--text);
  line-height: 1.5;
}

.hint-banner .hint-tag {
  flex: 0 0 auto;
  background: var(--accent);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 2px 7px;
  border-radius: 4px;
  margin-top: 1px;
}

.presets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.preset-chip {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--muted);
  font-size: 11.5px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 999px;
  text-decoration: none;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}

.preset-chip:hover {
  border-color: var(--accent);
  color: var(--accent-dark);
  background: var(--accent-soft);
}

.context-pill {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 12px;
  margin-bottom: 10px;
  background: var(--soft);
  border: 1px dashed var(--accent);
  border-radius: 8px;
  font-size: 12px;
  color: var(--text);
}

.context-pill .ctx-label {
  color: var(--accent-dark);
  font-weight: 700;
  margin-right: 6px;
}

.context-pill .ctx-text {
  flex: 1;
  color: var(--muted);
  word-break: break-word;
}

.context-pill .ctx-reset {
  flex: 0 0 auto;
  color: var(--muted);
  text-decoration: none;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid var(--line);
}

.context-pill .ctx-reset:hover {
  color: var(--accent-dark);
  border-color: var(--accent);
}

textarea {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 13px;
  color: var(--text);
  background: var(--panel);
  font: inherit;
  font-size: 15px;
  line-height: 1.55;
  min-height: 72px;
  resize: vertical;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(237, 111, 27, 0.15);
}

.input-bottom {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 12px;
}

select {
  flex: 0 0 200px;
  padding: 11px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  color: var(--text);
  background: var(--panel);
  font: inherit;
  font-size: 13px;
}

select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(237, 111, 27, 0.15);
}

button {
  flex: 1;
  border: 0;
  border-radius: 8px;
  padding: 12px 18px;
  background: var(--accent);
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

button:hover {
  background: var(--accent-dark);
}

.output-card {
  margin-top: 22px;
  padding: 22px;
  background: var(--output-bg);
  border: 1px solid var(--accent-border);
  border-left: 5px solid var(--accent);
  border-radius: 10px;
}

.output-card .output-label {
  color: var(--accent-dark);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.output-card .answer-text {
  white-space: pre-wrap;
  font-size: 14.5px;
  line-height: 1.75;
  color: var(--text);
}

.section-heading {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 26px 0 12px;
}

.section-heading h2 {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.section-heading .pill {
  background: var(--accent-soft);
  color: var(--accent-dark);
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}

.pipeline {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
}

.node {
  background: var(--panel);
  border: 1px solid var(--line);
  border-top: 3px solid var(--accent);
  border-radius: 8px;
  padding: 12px 11px 13px;
  min-height: 108px;
  display: flex;
  flex-direction: column;
}

.node .num {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 0.5px;
}

.node .title {
  font-size: 12.5px;
  font-weight: 700;
  margin: 2px 0 6px;
  color: var(--text);
  line-height: 1.3;
}

.node .detail {
  font-size: 11.5px;
  color: var(--muted);
  line-height: 1.5;
  word-break: break-word;
  flex: 1;
}

.advanced {
  margin-top: 28px;
  border-top: 1px dashed var(--line);
  padding-top: 18px;
}

.advanced summary {
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  letter-spacing: 0.4px;
  padding: 6px 0;
  user-select: none;
  list-style: none;
}

.advanced summary::-webkit-details-marker { display: none; }

.advanced summary::before {
  content: "▸ ";
  color: var(--accent);
  display: inline-block;
  transition: transform 0.15s ease;
}

.advanced[open] summary::before { content: "▾ "; }

.advanced summary:hover { color: var(--text); }

.advanced-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  margin-top: 14px;
}

.adv-box {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  background: var(--soft);
}

.adv-box h3 {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.adv-box code {
  display: block;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 11.5px;
  font-family: "SF Mono", "Consolas", "Monaco", monospace;
  line-height: 1.55;
}

.raw-block {
  margin-top: 12px;
  overflow: auto;
  padding: 14px;
  border-radius: 8px;
  background: #1a1a1a;
  color: #f5f5f5;
  font-size: 11.5px;
  font-family: "SF Mono", "Consolas", "Monaco", monospace;
  max-height: 280px;
  border: 1px solid #2a2a2a;
}

.error {
  margin-top: 22px;
  padding: 14px 16px;
  background: #fff2f0;
  border: 1px solid #ffccc7;
  border-left: 4px solid #c0392b;
  border-radius: 8px;
  color: #8a1f11;
  font-size: 14px;
}

@media (max-width: 860px) {
  .pipeline { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .advanced-grid { grid-template-columns: 1fr; }
  .input-bottom { flex-direction: column; align-items: stretch; }
  select { flex: 1 1 auto; }
  button { width: 100%; }
  h1 { font-size: 22px; }
}

@media (max-width: 520px) {
  .pipeline { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .container { padding: 0 16px; }
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


def run_builder_agent(agent_key: str, user_id: str, query: str, lang: str) -> tuple[str, bool]:
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

    nodes_html = []
    for i, step in enumerate(result.trace, start=1):
        nodes_html.append(
            f"""
            <div class="node">
              <div class="num">NODE {i:02d}</div>
              <div class="title">{html.escape(step.name)}</div>
              <div class="detail">{html.escape(step.detail)}</div>
            </div>
            """
        )

    shopping_summary = result.context.get("shopping_analysis_summary", {})
    needs_clarification = bool(result.context.get("needs_clarification", False))
    raw = [
        {"name": step.name, "detail": step.detail, "data": step.data}
        for step in result.trace
    ]
    step_count_label = f"{len(result.trace)} Nodes" if get_lang(lang) == "ko" else f"{len(result.trace)} 个 Node"

    return f"""
      <section class="output-card">
        <div class="output-label">{html.escape(text["agent_output"])} · {html.escape(display_name)}</div>
        <div class="answer-text">{html.escape(result.answer)}</div>
      </section>

      <div class="section-heading">
        <h2>{html.escape(text["execution_trace"])}</h2>
        <span class="pill">{html.escape(step_count_label)}</span>
      </div>
      <div class="pipeline">{''.join(nodes_html)}</div>

      <details class="advanced">
        <summary>기술 상세 / Technical Details</summary>
        <div class="advanced-grid">
          <div class="adv-box">
            <h3>{html.escape(text["loaded_config"])}</h3>
            <code>{escape_json(config_summary)}</code>
          </div>
          <div class="adv-box">
            <h3>{html.escape(text["shopping_analysis"])}</h3>
            <code>{escape_json(shopping_summary)}</code>
          </div>
        </div>
        <pre class="raw-block">{escape_json(raw)}</pre>
      </details>
    """, needs_clarification


def merge_followup_query(previous_query: str, new_query: str) -> str:
    previous_query = previous_query.strip()
    new_query = new_query.strip()
    if previous_query and new_query:
        return f"{previous_query} {new_query}"
    return new_query or previous_query


def render_page(
    agent_key: str = DEFAULT_AGENT,
    user_id: str = DEFAULT_USER,
    lang: str = DEFAULT_LANG,
    query: str | None = None,
    conversation_context: str = "",
    result_html: str = "",
    error: str = "",
    auto_run: bool = False,
) -> bytes:
    lang = get_lang(lang)
    text = UI_TEXT[lang]
    meta = get_agent_meta(agent_key)
    if query is None:
        query = str(meta["default_query"])

    if error:
        result_html = f'<div class="error">{html.escape(error)}</div>'
    if auto_run and not result_html:
        try:
            result_html, needs_clarification = run_builder_agent(agent_key, user_id, query, lang)
            if needs_clarification:
                conversation_context = query
                query = ""
        except Exception as exc:
            result_html = f'<div class="error">{html.escape(str(exc))}</div>'

    user_options = "\n".join(
        f'<option value="{html.escape(key)}"{selected(key, user_id)}>{html.escape(labels[lang])}</option>'
        for key, labels in USERS.items()
    )
    tabs_html = "\n".join(
        (
            f'<a class="tab{" active" if key == agent_key else ""}" '
            f'href="?agent={html.escape(key)}&lang={lang}">'
            f'{html.escape(str(value["labels"][lang]))}</a>'
        )
        for key, value in AGENT_CONFIGS.items()
    )
    other_lang = "zh" if lang == "ko" else "ko"
    other_label = "中文" if lang == "ko" else "한국어"
    placeholder = "다음 주에 칭다오 여행 가는데 옷 추천해줘" if lang == "ko" else "下周去青岛旅行，帮我推荐穿搭"
    if conversation_context:
        placeholder = text["followup_placeholder"]

    presets_html = ""
    if not conversation_context:
        preset_items = [
            (text["preset_minimal_label"], text["preset_minimal_query"]),
            (text["preset_partial_label"], text["preset_partial_query"]),
            (text["preset_full_label"], text["preset_full_query"]),
        ]
        chips = "".join(
            f'<a class="preset-chip" href="?agent={html.escape(agent_key)}&lang={lang}'
            f'&preset={urllib.parse.quote(p_query)}">{html.escape(p_label)}</a>'
            for p_label, p_query in preset_items
        )
        presets_html = f'<div class="presets">{chips}</div>'

    hint_html = ""
    if not conversation_context:
        hint_html = (
            f'<div class="hint-banner">'
            f'<span class="hint-tag">{html.escape(text["hint_label"])}</span>'
            f'<span>{html.escape(text["hint_text"])}</span>'
            f'</div>'
        )

    context_pill_html = ""
    if conversation_context:
        reset_href = f'?agent={html.escape(agent_key)}&lang={lang}'
        context_pill_html = (
            f'<div class="context-pill">'
            f'<span><span class="ctx-label">{html.escape(text["context_label"])}:</span>'
            f'<span class="ctx-text">{html.escape(conversation_context)}</span></span>'
            f'<a class="ctx-reset" href="{reset_href}">↺ {html.escape(text["reset_label"])}</a>'
            f'</div>'
        )

    page = f"""
<!doctype html>
<html lang="{html.escape(text["html_lang"])}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Personalized Outfit Recommendation Workflow MVP</title>
  <style>{STYLE}</style>
</head>
<body>
  <header class="header">
    <div class="container">
      <div class="lang-toggle">
        <a href="?agent={html.escape(agent_key)}&lang={other_lang}">{other_label}</a>
      </div>
      <p class="eyebrow">{html.escape(text["eyebrow"])}</p>
      <h1>{html.escape(text["title"])}</h1>
      <p class="subtitle">{html.escape(text["subtitle"])}</p>
    </div>
  </header>
  <main class="container">
    <nav class="tabs">{tabs_html}</nav>
    <form method="post" class="input-card">
      <input type="hidden" name="lang" value="{lang}">
      <input type="hidden" name="agent" value="{html.escape(agent_key)}">
      <input type="hidden" name="conversation_context" value="{html.escape(conversation_context)}">
      {hint_html}
      {presets_html}
      {context_pill_html}
      <textarea name="query" placeholder="{html.escape(placeholder)}">{html.escape(query)}</textarea>
      <div class="input-bottom">
        <select name="user">{user_options}</select>
        <button type="submit">▶ {html.escape(text["run"])}</button>
      </div>
    </form>
    {result_html}
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
        preset = params.get("preset", [""])[0].strip()
        if preset:
            self._send(render_page(
                agent_key=agent_key, user_id=user_id, lang=lang, query=preset,
            ))
        else:
            self._send(render_page(agent_key=agent_key, user_id=user_id, lang=lang))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        form = parse_qs(body)
        lang = get_lang(form.get("lang", [DEFAULT_LANG])[0])
        agent_key = form.get("agent", [DEFAULT_AGENT])[0]
        user_id = form.get("user", [DEFAULT_USER])[0]
        previous_query = form.get("conversation_context", [""])[0].strip()
        query = merge_followup_query(previous_query, form.get("query", [""])[0])
        if not query:
            query = str(get_agent_meta(agent_key)["default_query"])

        try:
            result_html, needs_clarification = run_builder_agent(agent_key, user_id, query, lang)
            conversation_context = query if needs_clarification else ""
            display_query = "" if needs_clarification else query
            error = ""
        except Exception as exc:
            result_html, error = "", str(exc)
            conversation_context = previous_query
            display_query = form.get("query", [""])[0].strip()
        self._send(
            render_page(
                agent_key=agent_key,
                user_id=user_id,
                lang=lang,
                query=display_query,
                conversation_context=conversation_context,
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
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return


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
    server = ThreadingHTTPServer(("127.0.0.1", port), DemoHandler)
    print(f"Personalized Outfit Recommendation Workflow MVP demo running at http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

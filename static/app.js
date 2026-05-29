// ============================================================
// Multi-Agent Workflow Builder — front-end logic
// ============================================================
(() => {
  "use strict";

  const I18N = window.I18N;
  const STORAGE_LANG = "mawb_lang";
  const CATEGORIES = ["input", "control", "tool", "data", "decision", "output"];

  let lang = localStorage.getItem(STORAGE_LANG) || "ko";
  let templates = [];
  let users = [];
  let currentDetail = null;
  let lastRunResult = null;
  let selectedNodeId = null;

  // ---------- helpers --------------------------------------------------
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  function t(key) {
    return (I18N[lang] && I18N[lang][key]) || (I18N.ko && I18N.ko[key]) || key;
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[c]));
  }

  async function fetchJSON(url, opts) {
    const r = await fetch(url, opts);
    const data = await r.json().catch(() => ({}));
    if (!r.ok || data.error) {
      throw new Error(data.error || `${url} → HTTP ${r.status}`);
    }
    return data;
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // ---------- i18n -----------------------------------------------------
  function applyI18n() {
    document.documentElement.lang = lang === "ko" ? "ko" : "zh-CN";
    $$("[data-i18n]").forEach((el) => {
      el.textContent = t(el.dataset.i18n);
    });
    $$(".lang-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === lang);
    });
    renderLegend();
    if (currentDetail) {
      renderTemplateMeta(currentDetail);
      refreshNodeLabels();
    }
    if (selectedNodeId && currentDetail) showNodeDetail(selectedNodeId);
    if (lastRunResult) renderResult(lastRunResult);
    refreshStatusPills();
  }

  function refreshStatusPills() {
    [["run-status", "run"], ["result-status", "result"]].forEach(([id, kind]) => {
      const pill = document.getElementById(id);
      if (!pill) return;
      const state = pill.dataset.state || "idle";
      const key = "status_" + state;
      const label = pill.querySelector(kind === "result" ? "#result-status-text" : "span:last-child");
      if (label) label.textContent = t(key);
    });
  }

  function refreshNodeLabels() {
    $$(".node").forEach((el) => {
      const cat = el.dataset.category;
      const badge = el.querySelector(".badge");
      if (badge && cat) badge.textContent = t("category_" + cat);
      const state = el.dataset.state || "idle";
      const lbl = el.querySelector(".state");
      if (lbl) lbl.textContent = t("node_state_" + state);
    });
  }

  function renderLegend() {
    const el = $("#canvas-legend");
    if (!el) return;
    el.innerHTML = CATEGORIES.map(
      (c) =>
        `<span class="legend-item"><span class="legend-dot" style="background:var(--cat-${c})"></span>${escapeHtml(
          t("category_" + c)
        )}</span>`
    ).join("");
  }

  // ---------- bootstrap ------------------------------------------------
  async function init() {
    bindLangButtons();
    applyI18n();

    try {
      const [tplResp, usersResp] = await Promise.all([
        fetchJSON("/api/templates"),
        fetchJSON("/api/users"),
      ]);
      templates = tplResp.templates;
      users = usersResp.users;
      fillTemplateSelect(tplResp.default);
      fillUserSelect();
      await loadTemplateDetail(tplResp.default);
    } catch (err) {
      console.error(err);
      document.body.insertAdjacentHTML(
        "afterbegin",
        `<div style="padding:14px;background:#fef2f2;color:#7f1d1d;border-bottom:1px solid #fecaca">
           Failed to load API: ${escapeHtml(err.message)}
         </div>`
      );
      return;
    }

    $("#template-select").addEventListener("change", (e) => loadTemplateDetail(e.target.value));
    $("#btn-generate").addEventListener("click", onGenerate);
    $("#btn-run").addEventListener("click", onRun);
    $("#copy-json").addEventListener("click", onCopyJson);

    const ro = new ResizeObserver(() => drawEdges());
    ro.observe($("#canvas"));
    window.addEventListener("resize", () => drawEdges());
  }

  function bindLangButtons() {
    $$(".lang-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        lang = btn.dataset.lang;
        localStorage.setItem(STORAGE_LANG, lang);
        applyI18n();
      });
    });
  }

  function fillTemplateSelect(selected) {
    const sel = $("#template-select");
    sel.innerHTML = templates
      .map(
        (tpl) =>
          `<option value="${escapeHtml(tpl.file)}"${tpl.file === selected ? " selected" : ""}>${escapeHtml(
            tpl.name
          )}</option>`
      )
      .join("");
  }

  function fillUserSelect() {
    const sel = $("#user-select");
    sel.innerHTML = users
      .map(
        (u) => `<option value="${escapeHtml(u.id)}">${escapeHtml(u.label)}</option>`
      )
      .join("");
  }

  // ---------- template detail load ------------------------------------
  async function loadTemplateDetail(name) {
    currentDetail = await fetchJSON("/api/template?name=" + encodeURIComponent(name));
    $("#query-input").value = currentDetail.default_query || "";
    selectedNodeId = null;
    lastRunResult = null;
    $("#result-area").hidden = true;
    setRunStatus("idle");
    renderTemplateMeta(currentDetail);
    renderNodes(currentDetail.nodes);
    showNodeDetail(null);
    requestAnimationFrame(() => drawEdges());
  }

  function renderTemplateMeta(detail) {
    $("#template-description").textContent = detail.description || "";
    $("#template-domain").textContent = detail.target_domain || "";
    $("#template-nodes-count").textContent = detail.nodes.length;
    const execType = (detail.generated_config && detail.generated_config.execution && detail.generated_config.execution.type) || "sequential";
    $("#template-execution").textContent = execType;
  }

  function renderNodes(nodes) {
    const container = $("#nodes-container");
    container.innerHTML = nodes
      .map(
        (n, i) => `
        <div class="node" data-id="${escapeHtml(n.id)}" data-category="${escapeHtml(n.category)}" data-state="idle" tabindex="0">
          <div class="num">NODE ${String(i + 1).padStart(2, "0")}</div>
          <div class="name">${escapeHtml(n.name)}</div>
          <div class="role">${escapeHtml(n.role)}</div>
          <div class="footer-row">
            <span class="badge">${escapeHtml(t("category_" + n.category) || n.category)}</span>
            <span class="state">${escapeHtml(t("node_state_idle"))}</span>
          </div>
        </div>`
      )
      .join("");
    container.querySelectorAll(".node").forEach((el) => {
      el.addEventListener("click", () => selectNode(el.dataset.id));
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          selectNode(el.dataset.id);
        }
      });
    });
  }

  function selectNode(id) {
    selectedNodeId = id;
    $$(".node").forEach((x) => x.classList.toggle("is-selected", x.dataset.id === id));
    showNodeDetail(id);
  }

  function showNodeDetail(nodeId) {
    const el = $("#detail-content");
    if (!nodeId || !currentDetail) {
      el.innerHTML = `<p class="muted small">${escapeHtml(t("detail_empty"))}</p>`;
      return;
    }
    const node = currentDetail.nodes.find((n) => n.id === nodeId);
    if (!node) return;
    const traceForNode =
      lastRunResult && lastRunResult.trace
        ? lastRunResult.trace.find((s) => s.name === node.name)
        : null;
    const inputsHtml =
      node.inputs.length === 0
        ? `<span class="muted">—</span>`
        : node.inputs.map((x) => `<span class="chip">${escapeHtml(x)}</span>`).join("");
    const outputsHtml =
      node.outputs.length === 0
        ? `<span class="muted">—</span>`
        : node.outputs.map((x) => `<span class="chip">${escapeHtml(x)}</span>`).join("");
    const traceHtml = traceForNode
      ? `<div class="detail-trace">
           <b>${escapeHtml(traceForNode.name)}</b><br>${escapeHtml(traceForNode.detail)}
           <pre>${escapeHtml(JSON.stringify(traceForNode.data, null, 2))}</pre>
         </div>`
      : `<p class="muted small">${escapeHtml(t("detail_pending"))}</p>`;

    el.innerHTML = `
      <dl class="detail-block">
        <dt>${escapeHtml(t("detail_category"))}</dt>
        <dd><span class="chip" style="background:color-mix(in srgb, var(--cat-${escapeHtml(node.category)}) 20%, white); color:var(--cat-${escapeHtml(node.category)})">${escapeHtml(t("category_" + node.category))}</span></dd>
        <dt>${escapeHtml(t("detail_role"))}</dt>
        <dd>${escapeHtml(node.role)}</dd>
        <dt>${escapeHtml(t("detail_inputs"))}</dt>
        <dd>${inputsHtml}</dd>
        <dt>${escapeHtml(t("detail_outputs"))}</dt>
        <dd>${outputsHtml}</dd>
        <dt>${escapeHtml(t("detail_builder"))}</dt>
        <dd>${escapeHtml(node.builder_equivalent || "—")}</dd>
      </dl>
      <h2 style="margin-top:8px">${escapeHtml(t("detail_trace"))}</h2>
      ${traceHtml}
    `;
  }

  function setNodeState(nodeId, state) {
    const el = document.querySelector(`.node[data-id="${cssEscape(nodeId)}"]`);
    if (!el) return;
    el.dataset.state = state;
    const lbl = el.querySelector(".state");
    if (lbl) lbl.textContent = t("node_state_" + state);
  }

  function setAllNodesState(state) {
    $$(".node").forEach((el) => {
      el.dataset.state = state;
      const lbl = el.querySelector(".state");
      if (lbl) lbl.textContent = t("node_state_" + state);
    });
  }

  function cssEscape(value) {
    if (window.CSS && CSS.escape) return CSS.escape(value);
    return String(value).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
  }

  // ---------- SVG edges ------------------------------------------------
  function drawEdges() {
    if (!currentDetail) return;
    const canvas = $("#canvas");
    const svg = $("#canvas-edges");
    const container = $("#nodes-container");
    if (!canvas || !svg || !container) return;

    const width = Math.max(canvas.clientWidth, container.scrollWidth + 32);
    const height = Math.max(canvas.clientHeight, container.scrollHeight + 16);
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("width", width);
    svg.setAttribute("height", height);

    const cRect = canvas.getBoundingClientRect();
    const nodes = Array.from(container.querySelectorAll(".node"));
    const rects = nodes.map((el) => {
      const r = el.getBoundingClientRect();
      return {
        id: el.dataset.id,
        left: r.left - cRect.left + canvas.scrollLeft,
        right: r.right - cRect.left + canvas.scrollLeft,
        top: r.top - cRect.top,
        bottom: r.bottom - cRect.top,
        cy: r.top - cRect.top + r.height / 2,
      };
    });

    let svgContent = `
      <defs>
        <marker id="arrow-idle" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
          <path class="arrow-head" d="M0,0 L10,5 L0,10 z"/>
        </marker>
        <marker id="arrow-active" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
          <path class="arrow-head is-active" d="M0,0 L10,5 L0,10 z"/>
        </marker>
        <marker id="arrow-done" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
          <path class="arrow-head is-done" d="M0,0 L10,5 L0,10 z"/>
        </marker>
      </defs>`;
    for (let i = 0; i < rects.length - 1; i++) {
      const a = rects[i];
      const b = rects[i + 1];
      const d = edgePath(a, b);
      const cls = "edge";
      svgContent += `<path class="${cls}" data-edge-index="${i}" d="${d}" marker-end="url(#arrow-idle)" />`;
    }
    svg.innerHTML = svgContent;
  }

  function edgePath(a, b) {
    const ax = a.right;
    const ay = a.cy;
    const bx = b.left;
    const by = b.cy;
    const sameRow = Math.abs(by - ay) < 4;
    if (sameRow) {
      // smooth horizontal Bezier
      const midX = (ax + bx) / 2;
      return `M ${ax},${ay} C ${midX},${ay} ${midX},${by} ${bx},${by}`;
    }
    // wrap-around: rounded orthogonal path with corners
    const exit = 22;
    const midY = (a.bottom + b.top) / 2;
    const r = 10;
    const dirRightToCorner = ax + exit;
    const cornerTopY = ay;
    return [
      `M ${ax},${ay}`,
      `L ${dirRightToCorner - r},${cornerTopY}`,
      `Q ${dirRightToCorner},${cornerTopY} ${dirRightToCorner},${cornerTopY + r}`,
      `L ${dirRightToCorner},${midY - r}`,
      `Q ${dirRightToCorner},${midY} ${dirRightToCorner - r},${midY}`,
      `L ${bx - exit + r},${midY}`,
      `Q ${bx - exit},${midY} ${bx - exit},${midY + r}`,
      `L ${bx - exit},${by - r}`,
      `Q ${bx - exit},${by} ${bx - exit + r},${by}`,
      `L ${bx},${by}`,
    ].join(" ");
  }

  function setEdgeState(index, state) {
    const path = document.querySelector(`.edge[data-edge-index="${index}"]`);
    if (!path) return;
    path.classList.remove("is-active", "is-done");
    if (state === "active") path.classList.add("is-active");
    if (state === "done") path.classList.add("is-done");
    const markerId =
      state === "active" ? "arrow-active" : state === "done" ? "arrow-done" : "arrow-idle";
    path.setAttribute("marker-end", `url(#${markerId})`);
  }

  function resetEdges() {
    $$(".edge").forEach((p) => {
      p.classList.remove("is-active", "is-done");
      p.setAttribute("marker-end", "url(#arrow-idle)");
    });
  }

  // ---------- status pill ---------------------------------------------
  function setRunStatus(state) {
    const pill = $("#run-status");
    pill.dataset.state = state;
    pill.className = "status-pill";
    if (state === "running") pill.classList.add("is-running");
    if (state === "done") pill.classList.add("is-done");
    if (state === "needs") pill.classList.add("is-needs");
    if (state === "error") pill.classList.add("is-error");
    const label = pill.querySelector("span:last-child");
    if (label) label.textContent = t("status_" + state);
  }

  function setResultStatus(state) {
    const pill = $("#result-status");
    pill.dataset.state = state;
    pill.className = "status-pill";
    if (state === "running") pill.classList.add("is-running");
    if (state === "done") pill.classList.add("is-done");
    if (state === "needs") pill.classList.add("is-needs");
    if (state === "error") pill.classList.add("is-error");
    $("#result-status-text").textContent = t("status_" + state);
  }

  // ---------- actions: generate ---------------------------------------
  async function onGenerate() {
    if (!currentDetail) return;
    const name = $("#template-select").value;
    try {
      currentDetail = await fetchJSON("/api/template?name=" + encodeURIComponent(name));
    } catch (err) {
      alert(err.message);
      return;
    }
    lastRunResult = null;
    setAllNodesState("idle");
    resetEdges();
    showGeneratedOnly(currentDetail);
  }

  function showGeneratedOnly(detail) {
    $("#result-area").hidden = false;
    setResultStatus("done");
    const placeholder = `<span class="muted small">—</span>`;
    $("#result-weather").innerHTML = placeholder;
    $("#result-shopping").innerHTML = placeholder;
    $("#result-ranking").innerHTML = placeholder;
    $("#result-trace").innerHTML = "";
    $("#result-answer").textContent = "";
    $("#result-json").textContent = JSON.stringify(detail.generated_config, null, 2);
  }

  // ---------- actions: run --------------------------------------------
  async function onRun() {
    if (!currentDetail) return;
    const btn = $("#btn-run");
    btn.classList.add("is-loading");
    btn.disabled = true;
    setRunStatus("running");
    setAllNodesState("idle");
    resetEdges();
    $("#result-area").hidden = true;

    try {
      const payload = {
        template: $("#template-select").value,
        user: $("#user-select").value,
        query: $("#query-input").value,
      };
      const result = await fetchJSON("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await animateRun(result);
      lastRunResult = result;
      renderResult(result);
      setRunStatus(result.needs_clarification ? "needs" : "done");
    } catch (err) {
      console.error(err);
      setRunStatus("error");
      alert(t("error_run") + ": " + err.message);
    } finally {
      btn.classList.remove("is-loading");
      btn.disabled = false;
    }
  }

  async function animateRun(result) {
    // map trace.name → node id by matching against currentDetail.nodes[].name
    const byName = {};
    currentDetail.nodes.forEach((n) => {
      byName[n.name] = n.id;
    });
    const sequence = result.trace.map((s) => byName[s.name]).filter(Boolean);
    const visited = new Set(sequence);

    currentDetail.nodes.forEach((n) => {
      if (!visited.has(n.id)) setNodeState(n.id, "skipped");
    });

    for (let i = 0; i < sequence.length; i++) {
      const id = sequence[i];
      setNodeState(id, "active");
      if (i > 0) setNodeState(sequence[i - 1], "done");
      if (i > 0) setEdgeState(i - 1, "active");
      if (i > 1) setEdgeState(i - 2, "done");
      await sleep(360);
    }
    if (sequence.length > 0) setNodeState(sequence[sequence.length - 1], "done");
    if (sequence.length > 1) setEdgeState(sequence.length - 2, "done");
  }

  function renderResult(result) {
    $("#result-area").hidden = false;
    const w = result.summary.weather_summary || {};
    const s = result.summary.shopping_analysis_summary || {};
    const ranked = result.summary.ranked_items || [];

    $("#result-weather").innerHTML = `
      <div class="row"><span>${escapeHtml(t("field_city"))}</span><span>${escapeHtml(result.summary.city_display || "-")}</span></div>
      <div class="row"><span>${escapeHtml(t("field_date"))}</span><span>${escapeHtml(result.summary.date_label || "-")}</span></div>
      <div class="row"><span>${escapeHtml(t("field_temp"))}</span><span>${escapeHtml(`${w.temp_min ?? "-"} ~ ${w.temp_max ?? "-"} °C`)}</span></div>
      <div class="row"><span>${escapeHtml(t("field_condition"))}</span><span>${escapeHtml(w.condition || "-")}</span></div>
    `;
    $("#result-shopping").innerHTML = `
      <div class="row"><span>${escapeHtml(t("field_items"))}</span><span>${escapeHtml(String(s.total_items ?? "-"))}</span></div>
      <div class="row"><span>${escapeHtml(t("field_styles"))}</span><span>${(s.top_styles || []).map(escapeHtml).join(", ") || "-"}</span></div>
      <div class="row"><span>${escapeHtml(t("field_colors"))}</span><span>${(s.top_colors || []).map(escapeHtml).join(", ") || "-"}</span></div>
    `;
    $("#result-ranking").innerHTML = ranked.length
      ? ranked.map((item) => `<div>${escapeHtml(item)}</div>`).join("")
      : `<div class="muted small">${escapeHtml((result.answer || "").slice(0, 240))}</div>`;

    $("#result-trace").innerHTML = result.trace
      .map(
        (st) => `<li><strong>${escapeHtml(st.name)}</strong><span class="trace-detail">${escapeHtml(st.detail)}</span></li>`
      )
      .join("");

    $("#result-answer").textContent = result.answer || "";
    $("#result-json").textContent = JSON.stringify(result.generated_config, null, 2);

    if (selectedNodeId) showNodeDetail(selectedNodeId);
    setResultStatus(result.needs_clarification ? "needs" : "done");
  }

  function onCopyJson() {
    const text = $("#result-json").textContent;
    if (!text) return;
    const btn = $("#copy-json");
    navigator.clipboard
      .writeText(text)
      .then(() => {
        btn.textContent = t("action_copied");
        setTimeout(() => {
          btn.textContent = t("action_copy");
        }, 1200);
      })
      .catch(() => {
        // fallback: select text
        const range = document.createRange();
        range.selectNodeContents($("#result-json"));
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
      });
  }

  // ---------- go --------------------------------------------------------
  init();
})();

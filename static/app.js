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
  let builderPresets = [];
  let currentBuilderPreset = null;
  let currentDetail = null;
  let lastRunResult = null;
  let selectedNodeId = null;

  // ---------- helpers --------------------------------------------------
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  function t(key) {
    return (I18N[lang] && I18N[lang][key]) || (I18N.ko && I18N.ko[key]) || key;
  }

  function localized(value) {
    if (value && typeof value === "object") {
      return value[lang] || value.ko || value.zh || Object.values(value)[0] || "";
    }
    return value || "";
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
      renderControlContext(currentDetail);
      refreshNodeLabels();
    }
    if (selectedNodeId && currentDetail) showNodeDetail(selectedNodeId);
    if (lastRunResult) renderResult(lastRunResult);
    refreshStatusPills();
    renderBuilderWorkspace();
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
      const [tplResp, usersResp, builderResp] = await Promise.all([
        fetchJSON("/api/templates"),
        fetchJSON("/api/users"),
        fetchJSON("/api/builder/presets"),
      ]);
      templates = tplResp.templates;
      users = usersResp.users;
      builderPresets = builderResp.presets || [];
      fillTemplateSelect(tplResp.default);
      fillBuilderPresetSelect(builderResp.default);
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
    $("#builder-preset-select").addEventListener("change", (e) => selectBuilderPreset(e.target.value, true));
    $("#btn-compose-builder").addEventListener("click", onComposeBuilder);
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

  function fillBuilderPresetSelect(selected) {
    const sel = $("#builder-preset-select");
    if (!sel) return;
    sel.innerHTML = builderPresets
      .map(
        (preset) =>
          `<option value="${escapeHtml(preset.id)}"${preset.id === selected ? " selected" : ""}>${escapeHtml(
            localized(preset.label) || preset.id
          )}</option>`
      )
      .join("");
    selectBuilderPreset(selected || (builderPresets[0] && builderPresets[0].id), false);
  }

  function selectBuilderPreset(id, updateQuery) {
    currentBuilderPreset = builderPresets.find((preset) => preset.id === id) || builderPresets[0] || null;
    if (!currentBuilderPreset) return;
    const nameInput = $("#builder-workflow-name");
    if (nameInput) nameInput.value = currentBuilderPreset.default_workflow_name || "";
    if (updateQuery && currentBuilderPreset.default_query) {
      $("#query-input").value = currentBuilderPreset.default_query;
    }
    renderBuilderWorkspace();
  }

  function renderBuilderWorkspace() {
    const list = $("#builder-node-list");
    if (!list || !currentBuilderPreset) return;
    list.innerHTML = (currentBuilderPreset.nodes || [])
      .map(
        (node, index) => `
        <div class="builder-node-item">
          <span class="builder-node-index">${String(index + 1).padStart(2, "0")}</span>
          <span class="builder-node-name" title="${escapeHtml(node.name)}">${escapeHtml(node.name)}</span>
          <span class="builder-node-required">${escapeHtml(node.required ? t("builder_required") : "")}</span>
        </div>`
      )
      .join("");
    const status = $("#builder-status");
    if (status) {
      status.textContent = t("builder_status_ready");
    }
  }

  function builderPayloadFromUI() {
    const preset = currentBuilderPreset || builderPresets[0] || {};
    return {
      preset: preset.id,
      workflow_name: ($("#builder-workflow-name") && $("#builder-workflow-name").value) || preset.default_workflow_name,
      node_ids: (preset.nodes || []).map((node) => node.id),
      query: $("#query-input") ? $("#query-input").value : preset.default_query,
    };
  }

  function fillUserSelect() {
    const sel = $("#user-select");
    const optionRows =
      (currentDetail && currentDetail.context_options && currentDetail.context_options.options) || users;
    sel.innerHTML = optionRows
      .map(
        (u) => {
          const label = localized(u.label || u.labels) || u.id;
          return `<option value="${escapeHtml(u.id)}">${escapeHtml(label)}</option>`;
        }
      )
      .join("");
    const selected = currentDetail && currentDetail.default_user_id;
    if (selected && optionRows.some((u) => u.id === selected)) {
      sel.value = selected;
    }
  }

  // ---------- template detail load ------------------------------------
  async function loadTemplateDetail(name) {
    currentDetail = await fetchJSON("/api/template?name=" + encodeURIComponent(name));
    $("#query-input").value = currentDetail.default_query || "";
    renderControlContext(currentDetail);
    selectedNodeId = null;
    lastRunResult = null;
    $("#result-area").hidden = true;
    setRunStatus("idle");
    renderTemplateMeta(currentDetail);
    renderNodes(currentDetail.nodes);
    showNodeDetail(null);
    requestAnimationFrame(() => drawEdges());
  }

  function renderControlContext(detail) {
    const cfg = detail && detail.context_options;
    const contextTitle = document.querySelector('[data-i18n="controls_user"]');
    const queryTitle = document.querySelector('[data-i18n="controls_query"]');
    if (contextTitle) contextTitle.textContent = localized(cfg && cfg.label) || t("controls_user");
    if (queryTitle) queryTitle.textContent = localized(cfg && cfg.query_label) || t("controls_query");
    fillUserSelect();
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
    if (currentDetail.builder_mode === "custom_workspace") {
      try {
        currentDetail = await fetchJSON("/api/builder/compose", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(builderPayloadFromUI()),
        });
      } catch (err) {
        alert(err.message);
        return;
      }
    } else {
      const name = $("#template-select").value;
      try {
        currentDetail = await fetchJSON("/api/template?name=" + encodeURIComponent(name));
      } catch (err) {
        alert(err.message);
        return;
      }
    }
    lastRunResult = null;
    setAllNodesState("idle");
    resetEdges();
    renderTemplateMeta(currentDetail);
    renderControlContext(currentDetail);
    renderNodes(currentDetail.nodes);
    requestAnimationFrame(() => drawEdges());
    showGeneratedOnly(currentDetail);
  }

  function showGeneratedOnly(detail) {
    $("#result-area").hidden = false;
    setResultStatus("done");
    renderResultCards([]);
    $("#result-trace").innerHTML = "";
    $("#result-answer").textContent = "";
    $("#result-json").textContent = JSON.stringify(detail.generated_config, null, 2);
  }

  function rowsHtml(rows) {
    return (rows || [])
      .map((row) => {
        const value = row.value == null || row.value === "" ? "-" : row.value;
        return `<div class="row"><span>${escapeHtml(row.label || "")}</span><span>${escapeHtml(value)}</span></div>`;
      })
      .join("");
  }

  function cardHtml(card) {
    let body;
    if (card.items && card.items.length) {
      body = card.items.map((item) => `<div>${escapeHtml(item)}</div>`).join("");
    } else if (card.rows && card.rows.length) {
      body = rowsHtml(card.rows);
    } else {
      body = `<span class="muted small">—</span>`;
    }
    return `<div class="result-card">
        <div class="result-card-title">${escapeHtml(card.title || "")}</div>
        <div class="result-card-body">${body}</div>
      </div>`;
  }

  function renderResultCards(cards) {
    const grid = $("#result-grid");
    if (!grid) return;
    if (!cards || !cards.length) {
      grid.innerHTML = `<div class="result-card result-card-empty"><span class="muted small">${escapeHtml(
        t("result_placeholder")
      )}</span></div>`;
      return;
    }
    grid.innerHTML = cards.map(cardHtml).join("");
  }

  // Outfit runtime returns typed summary fields instead of generic summary_cards;
  // normalize both shapes into one card model so the result grid has a single render path.
  function buildResultCards(result) {
    const summary = result.summary || {};
    if (summary.summary_cards && summary.summary_cards.length) {
      return summary.summary_cards;
    }
    const w = summary.weather_summary || {};
    const s = summary.shopping_analysis_summary || {};
    const ranked = summary.ranked_items || [];
    return [
      {
        title: t("result_weather"),
        rows: [
          { label: t("field_city"), value: summary.city_display || "-" },
          { label: t("field_date"), value: summary.date_label || "-" },
          { label: t("field_temp"), value: `${w.temp_min ?? "-"} ~ ${w.temp_max ?? "-"} °C` },
          { label: t("field_condition"), value: w.condition || "-" },
        ],
      },
      {
        title: t("result_shopping"),
        rows: [
          { label: t("field_items"), value: String(s.total_items ?? "-") },
          { label: t("field_styles"), value: (s.top_styles || []).join(", ") || "-" },
          { label: t("field_colors"), value: (s.top_colors || []).join(", ") || "-" },
        ],
      },
      {
        title: t("result_ranking"),
        items: ranked.length ? ranked : [(result.answer || "").slice(0, 240)],
      },
    ];
  }

  // ---------- actions: builder compose --------------------------------
  async function onComposeBuilder() {
    if (!currentBuilderPreset) return;
    try {
      currentDetail = await fetchJSON("/api/builder/compose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(builderPayloadFromUI()),
      });
    } catch (err) {
      alert(err.message);
      return;
    }

    selectedNodeId = null;
    lastRunResult = null;
    $("#result-area").hidden = true;
    setRunStatus("idle");
    renderTemplateMeta(currentDetail);
    renderControlContext(currentDetail);
    renderNodes(currentDetail.nodes);
    showNodeDetail(null);
    showGeneratedOnly(currentDetail);
    const status = $("#builder-status");
    if (status) status.textContent = t("builder_status_composed");
    requestAnimationFrame(() => drawEdges());
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
      const isCustom = currentDetail.builder_mode === "custom_workspace";
      const payload = isCustom
        ? { ...builderPayloadFromUI(), user: $("#user-select").value, query: $("#query-input").value }
        : {
            template: $("#template-select").value,
            user: $("#user-select").value,
            query: $("#query-input").value,
          };
      const result = await fetchJSON(isCustom ? "/api/builder/run" : "/api/run", {
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
    renderResultCards(buildResultCards(result));

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

const path = require("path");

const pptxgen = require("C:/Users/lain/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pptxgenjs");
const pptx = new pptxgen();

const ROOT = path.resolve(__dirname, "..");
const OUT_KO = path.join(ROOT, "docs", "AI_Agent_Builder_MVP_KR.pptx");
const OUT_ZH = path.join(ROOT, "docs", "AI_Agent_Builder_MVP_ZH.pptx");

const COLORS = {
  bg: "F5F7FA",
  text: "17202A",
  muted: "607080",
  line: "D8E1EA",
  accent: "1F6F8B",
  green: "2F7D68",
  greenSoft: "E8F5F1",
  dark: "12202B",
  white: "FFFFFF",
};

function addTitle(slide, title, subtitle, lang) {
  slide.addText(title, {
    x: 0.55,
    y: 0.38,
    w: 12.2,
    h: 0.42,
    fontFace: lang === "ko" ? "Malgun Gothic" : "Microsoft YaHei",
    fontSize: 21,
    bold: true,
    color: COLORS.text,
    margin: 0,
    breakLine: false,
    fit: "shrink",
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.58,
      y: 0.86,
      w: 11.9,
      h: 0.28,
      fontFace: lang === "ko" ? "Malgun Gothic" : "Microsoft YaHei",
      fontSize: 8.5,
      color: COLORS.muted,
      margin: 0,
      breakLine: false,
      fit: "shrink",
    });
  }
  slide.addShape(pptx.ShapeType.line, {
    x: 0.55,
    y: 1.22,
    w: 12.2,
    h: 0,
    line: { color: COLORS.line, width: 1 },
  });
}

function addFooter(slide, pageNo, lang) {
  slide.addText(lang === "ko" ? "설정 기반 AI Agent Builder MVP" : "配置驱动 AI Agent Builder MVP", {
    x: 0.55,
    y: 7.1,
    w: 4.5,
    h: 0.2,
    fontSize: 7.5,
    color: COLORS.muted,
    fontFace: lang === "ko" ? "Malgun Gothic" : "Microsoft YaHei",
    margin: 0,
  });
  slide.addText(String(pageNo), {
    x: 12.05,
    y: 7.1,
    w: 0.7,
    h: 0.2,
    fontSize: 7.5,
    color: COLORS.muted,
    align: "right",
    margin: 0,
  });
}

function addBullets(slide, items, x, y, w, h, lang, fontSize = 15) {
  slide.addText(
    items.map((t) => ({ text: t, options: { bullet: { type: "bullet" }, breakLine: true } })),
    {
      x,
      y,
      w,
      h,
      fontFace: lang === "ko" ? "Malgun Gothic" : "Microsoft YaHei",
      fontSize,
      color: COLORS.text,
      margin: 0.08,
      paraSpaceAfterPt: 8,
      breakLine: false,
      fit: "shrink",
    }
  );
}

function addCard(slide, title, body, x, y, w, h, lang, accent = COLORS.accent) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.06,
    fill: { color: COLORS.white },
    line: { color: COLORS.line, width: 1 },
    shadow: { type: "outer", color: "D7DEE8", opacity: 0.16, blur: 1, angle: 45, distance: 1 },
  });
  slide.addShape(pptx.ShapeType.rect, { x, y, w: 0.08, h, fill: { color: accent }, line: { color: accent } });
  slide.addText(title, {
    x: x + 0.22,
    y: y + 0.16,
    w: w - 0.35,
    h: 0.25,
    fontFace: lang === "ko" ? "Malgun Gothic" : "Microsoft YaHei",
    fontSize: 12.5,
    bold: true,
    color: COLORS.text,
    margin: 0,
    fit: "shrink",
  });
  slide.addText(body, {
    x: x + 0.22,
    y: y + 0.52,
    w: w - 0.35,
    h: h - 0.65,
    fontFace: lang === "ko" ? "Malgun Gothic" : "Microsoft YaHei",
    fontSize: 9.5,
    color: COLORS.muted,
    margin: 0,
    breakLine: false,
    fit: "shrink",
  });
}

function addSimpleTable(slide, rows, x, y, w, h, lang, opts = {}) {
  const colW = opts.colW || Array(rows[0].length).fill(w / rows[0].length);
  const rowH = h / rows.length;
  const fontFace = lang === "ko" ? "Malgun Gothic" : "Microsoft YaHei";
  rows.forEach((row, r) => {
    let cx = x;
    row.forEach((cell, c) => {
      const fill = r === 0 ? COLORS.dark : r % 2 === 0 ? "F8FAFC" : COLORS.white;
      const color = r === 0 ? COLORS.white : COLORS.text;
      slide.addShape(pptx.ShapeType.rect, {
        x: cx,
        y: y + rowH * r,
        w: colW[c],
        h: rowH,
        fill: { color: fill },
        line: { color: COLORS.line, width: 0.6 },
      });
      slide.addText(String(cell), {
        x: cx + 0.05,
        y: y + rowH * r + 0.05,
        w: colW[c] - 0.1,
        h: rowH - 0.08,
        fontFace,
        fontSize: opts.fontSize || 8.5,
        color,
        bold: r === 0,
        valign: "mid",
        margin: 0,
        fit: "shrink",
      });
      cx += colW[c];
    });
  });
}

function addFlow(slide, steps, lang) {
  const y = 2.38;
  const startX = 0.75;
  const boxW = 2.15;
  const gap = 0.26;
  steps.forEach((step, idx) => {
    const x = startX + idx * (boxW + gap);
    slide.addShape(pptx.ShapeType.roundRect, {
      x,
      y,
      w: boxW,
      h: 1.1,
      rectRadius: 0.06,
      fill: { color: idx === 2 ? COLORS.greenSoft : COLORS.white },
      line: { color: idx === 2 ? COLORS.green : COLORS.line, width: 1 },
    });
    slide.addText(step.title, {
      x: x + 0.12,
      y: y + 0.17,
      w: boxW - 0.24,
      h: 0.22,
      fontFace: lang === "ko" ? "Malgun Gothic" : "Microsoft YaHei",
      fontSize: 11,
      bold: true,
      color: COLORS.text,
      margin: 0,
      align: "center",
      fit: "shrink",
    });
    slide.addText(step.body, {
      x: x + 0.12,
      y: y + 0.48,
      w: boxW - 0.24,
      h: 0.45,
      fontFace: lang === "ko" ? "Malgun Gothic" : "Microsoft YaHei",
      fontSize: 8,
      color: COLORS.muted,
      margin: 0,
      align: "center",
      fit: "shrink",
    });
    if (idx < steps.length - 1) {
      slide.addShape(pptx.ShapeType.rightArrow, {
        x: x + boxW + 0.03,
        y: y + 0.42,
        w: 0.2,
        h: 0.26,
        fill: { color: COLORS.accent },
        line: { color: COLORS.accent },
      });
    }
  });
}

function buildDeck(lang) {
  const ko = lang === "ko";
  const deck = new pptxgen();
  deck.layout = "LAYOUT_WIDE";
  deck.author = "Codex";
  deck.subject = ko ? "설정 기반 AI Agent Builder MVP" : "配置驱动 AI Agent Builder MVP";
  deck.title = deck.subject;
  deck.company = "";
  deck.lang = ko ? "ko-KR" : "zh-CN";
  deck.theme = {
    headFontFace: ko ? "Malgun Gothic" : "Microsoft YaHei",
    bodyFontFace: ko ? "Malgun Gothic" : "Microsoft YaHei",
    lang: ko ? "ko-KR" : "zh-CN",
  };

  const t = ko ? TEXT_KO : TEXT_ZH;

  let s = deck.addSlide();
  s.background = { color: COLORS.bg };
  s.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: COLORS.bg }, line: { color: COLORS.bg } });
  s.addText(t.title, {
    x: 0.75,
    y: 1.15,
    w: 11.8,
    h: 0.85,
    fontFace: ko ? "Malgun Gothic" : "Microsoft YaHei",
    fontSize: 30,
    bold: true,
    color: COLORS.text,
    margin: 0,
    fit: "shrink",
  });
  s.addText(t.subtitle, {
    x: 0.78,
    y: 2.12,
    w: 11.2,
    h: 0.55,
    fontFace: ko ? "Malgun Gothic" : "Microsoft YaHei",
    fontSize: 14,
    color: COLORS.muted,
    margin: 0,
    fit: "shrink",
  });
  addCard(s, t.coverCards[0].title, t.coverCards[0].body, 0.8, 3.15, 3.75, 1.35, lang, COLORS.accent);
  addCard(s, t.coverCards[1].title, t.coverCards[1].body, 4.8, 3.15, 3.75, 1.35, lang, COLORS.green);
  addCard(s, t.coverCards[2].title, t.coverCards[2].body, 8.8, 3.15, 3.75, 1.35, lang, "8A6F1F");
  s.addText(t.date, { x: 0.78, y: 6.78, w: 5, h: 0.22, fontSize: 9, color: COLORS.muted, margin: 0 });

  s = deck.addSlide();
  addTitle(s, t.problem.title, t.problem.subtitle, lang);
  addBullets(s, t.problem.bullets, 0.8, 1.65, 5.6, 3.2, lang, 15);
  addSimpleTable(s, t.problem.table, 6.75, 1.55, 5.6, 3.25, lang, { colW: [1.65, 3.95], fontSize: 8.5 });
  addFooter(s, 2, lang);

  s = deck.addSlide();
  addTitle(s, t.goal.title, t.goal.subtitle, lang);
  addCard(s, t.goal.cards[0].title, t.goal.cards[0].body, 0.8, 1.55, 3.85, 1.6, lang, COLORS.accent);
  addCard(s, t.goal.cards[1].title, t.goal.cards[1].body, 4.9, 1.55, 3.85, 1.6, lang, COLORS.green);
  addCard(s, t.goal.cards[2].title, t.goal.cards[2].body, 9.0, 1.55, 3.25, 1.6, lang, "8A6F1F");
  s.addText(t.goal.formula, {
    x: 1.15,
    y: 4.05,
    w: 11.0,
    h: 1.1,
    fontFace: "Consolas",
    fontSize: 20,
    bold: true,
    align: "center",
    color: COLORS.text,
    margin: 0.05,
    fit: "shrink",
  });
  addFooter(s, 3, lang);

  s = deck.addSlide();
  addTitle(s, t.method.title, t.method.subtitle, lang);
  addFlow(s, t.method.steps, lang);
  addSimpleTable(s, t.method.table, 1.25, 4.35, 10.8, 1.55, lang, { colW: [2.4, 8.4], fontSize: 8.5 });
  addFooter(s, 4, lang);

  s = deck.addSlide();
  addTitle(s, t.arch.title, t.arch.subtitle, lang);
  addSimpleTable(s, t.arch.table, 0.9, 1.5, 11.6, 4.7, lang, { colW: [3.35, 8.25], fontSize: 9 });
  addFooter(s, 5, lang);

  s = deck.addSlide();
  addTitle(s, t.demo.title, t.demo.subtitle, lang);
  addSimpleTable(s, t.demo.table, 0.8, 1.55, 11.8, 3.4, lang, { colW: [2.25, 3.25, 3.25, 3.05], fontSize: 8.2 });
  addTextBlock(s, t.demo.note, 0.9, 5.35, 11.6, 0.65, lang, COLORS.greenSoft);
  addFooter(s, 6, lang);

  s = deck.addSlide();
  addTitle(s, t.evaluation.title, t.evaluation.subtitle, lang);
  addSimpleTable(s, t.evaluation.table, 0.75, 1.5, 11.9, 4.55, lang, { colW: [2.75, 4.55, 4.6], fontSize: 8.2 });
  addFooter(s, 7, lang);

  s = deck.addSlide();
  addTitle(s, t.metrics.title, t.metrics.subtitle, lang);
  addSimpleTable(s, t.metrics.table, 0.8, 1.45, 5.65, 3.95, lang, { colW: [3.7, 1.95], fontSize: 8.4 });
  addSimpleTable(s, t.metrics.table2, 6.85, 1.45, 5.65, 3.95, lang, { colW: [2.8, 2.85], fontSize: 8.4 });
  addFooter(s, 8, lang);

  s = deck.addSlide();
  addTitle(s, t.time.title, t.time.subtitle, lang);
  addSimpleTable(s, t.time.table, 0.65, 1.45, 12.0, 4.85, lang, { colW: [2.3, 1.7, 1.7, 1.7, 4.6], fontSize: 7.5 });
  addFooter(s, 9, lang);

  s = deck.addSlide();
  addTitle(s, t.demoFlow.title, t.demoFlow.subtitle, lang);
  addBullets(s, t.demoFlow.bullets, 0.85, 1.55, 6.0, 4.7, lang, 13.5);
  addTextBlock(s, t.demoFlow.script, 7.0, 1.7, 5.2, 2.25, lang, COLORS.greenSoft);
  addSimpleTable(s, t.demoFlow.table, 7.0, 4.45, 5.2, 1.35, lang, { colW: [2.0, 3.2], fontSize: 8 });
  addFooter(s, 10, lang);

  s = deck.addSlide();
  addTitle(s, t.limit.title, t.limit.subtitle, lang);
  addSimpleTable(s, t.limit.table, 0.85, 1.55, 11.7, 3.4, lang, { colW: [3.1, 8.6], fontSize: 9 });
  addTextBlock(s, t.limit.statement, 0.9, 5.25, 11.55, 0.9, lang, "FFF7DF");
  addFooter(s, 11, lang);

  s = deck.addSlide();
  addTitle(s, t.conclusion.title, "", lang);
  addBullets(s, t.conclusion.bullets, 0.85, 1.55, 6.0, 3.65, lang, 15);
  addTextBlock(s, t.conclusion.final, 7.0, 1.75, 5.3, 2.8, lang, COLORS.greenSoft);
  addSimpleTable(s, t.conclusion.table, 7.0, 5.1, 5.3, 0.95, lang, { colW: [2.35, 2.95], fontSize: 8 });
  addFooter(s, 12, lang);

  return deck;
}

function addTextBlock(slide, text, x, y, w, h, lang, fill) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.06,
    fill: { color: fill },
    line: { color: fill === COLORS.greenSoft ? "BFE1D8" : "F1D68A", width: 1 },
  });
  slide.addText(text, {
    x: x + 0.18,
    y: y + 0.16,
    w: w - 0.36,
    h: h - 0.28,
    fontFace: lang === "ko" ? "Malgun Gothic" : "Microsoft YaHei",
    fontSize: 11,
    color: COLORS.text,
    margin: 0,
    fit: "shrink",
  });
}

const TEXT_KO = {
  title: "설정 기반 AI Agent Builder MVP",
  subtitle: "쇼핑 기록과 날씨 데이터를 활용하는 개인화 Agent를 더 빠르게 생성하기 위한 Builder 검증",
  date: "2026.04 | 종합설계 발표",
  coverCards: [
    { title: "핵심 가설", body: "같은 실행 엔진에서 JSON 설정 파일만 바꾸면 서로 다른 Agent를 실행할 수 있다." },
    { title: "Demo 범위", body: "의류 추천, 여행 준비물, 통학/출근 준비 3개 Agent를 구현했다." },
    { title: "평가 관점", body: "완성된 기능보다 Agent 생성 과정의 작업량과 재사용성을 평가한다." },
  ],
  problem: {
    title: "Problem",
    subtitle: "Agent 하나를 만들 때마다 반복되는 구현 작업이 많다.",
    bullets: [
      "입력 분석, API 호출, 데이터 분석, 추천 규칙, 출력 형식을 매번 구현해야 한다.",
      "유사한 Agent를 추가할 때도 같은 구조의 작업이 반복된다.",
      "따라서 Agent 기능 자체보다 생성 과정을 줄이는 방법이 필요하다.",
    ],
    table: [
      ["직접 구현 단계", "반복되는 작업"],
      ["입력 처리", "도시, 날짜, 사용자 의도 파싱"],
      ["도구 호출", "Weather API, 쇼핑 기록 데이터 연결"],
      ["분석/추천", "스타일 분석, 온도별 추천 규칙 작성"],
      ["출력/UI", "응답 템플릿과 화면 연결"],
    ],
  },
  goal: {
    title: "Goal",
    subtitle: "완성형 플랫폼이 아니라 Builder의 핵심 가능성을 MVP로 검증한다.",
    cards: [
      { title: "공통 엔진", body: "Plan -> Act -> Analyze -> Decide -> Compose 실행 흐름을 고정한다." },
      { title: "설정 파일", body: "Agent별 차이는 JSON config에 작성한다." },
      { title: "재사용성", body: "유사 난이도 Agent 3개를 같은 엔진으로 실행한다." },
    ],
    formula: "same engine.py\n+ different JSON config\n= different Agent behavior",
  },
  method: {
    title: "Proposed Method",
    subtitle: "Agent 실행 흐름을 고정하고, 도구와 규칙은 설정으로 변경한다.",
    steps: [
      { title: "Plan", body: "도시/날짜/사용자/Agent 설정 확정" },
      { title: "Act", body: "Weather API + shopping_history 호출" },
      { title: "Analyze", body: "구매 기록에서 스타일/색상 추출" },
      { title: "Decide", body: "날씨와 구매 기록 기반 규칙 적용" },
      { title: "Compose", body: "output_template로 응답 생성" },
    ],
    table: [
      ["Config 항목", "역할"],
      ["tools", "Weather API, shopping_history 사용 여부"],
      ["temperature_rules", "온도별 추천 규칙"],
      ["conditional_extras", "비, 일교차 등 추가 조건"],
      ["output_template", "최종 응답 문장 형식"],
    ],
  },
  arch: {
    title: "System Architecture",
    subtitle: "공통 엔진과 Agent별 설정 파일을 분리한다.",
    table: [
      ["구성 요소", "역할"],
      ["web_app.py", "Agent 선택, 사용자 선택, 결과와 trace 표시"],
      ["src/agent_builder/engine.py", "공통 실행 엔진"],
      ["src/agent_builder/shopping.py", "쇼핑 기록 분석 및 보유 단품 선택"],
      ["configs/*.json", "Agent별 추천 규칙과 출력 템플릿"],
      ["data/shopping_history.json", "모의 구매 기록 데이터"],
      ["WeatherTool", "Open-Meteo 기반 실시간 날씨 조회"],
    ],
  },
  demo: {
    title: "Demo: 3 Similar Agents",
    subtitle: "세 Agent는 같은 엔진과 같은 데이터 분석 모듈을 사용한다.",
    table: [
      ["Agent", "목적", "Config", "재사용 요소"],
      ["Outfit", "날씨+쇼핑 기록 기반 의류 추천", "outfit_agent.json", "engine, shopping, weather"],
      ["Travel Packing", "날씨+쇼핑 기록 기반 여행 준비물 추천", "travel_pack_agent.json", "engine, shopping, weather"],
      ["Commute", "날씨+쇼핑 기록 기반 통학/출근 준비 추천", "commute_agent.json", "engine, shopping, weather"],
    ],
    note: "중요한 점은 Agent 기능 자체보다, 같은 실행 엔진에서 설정 파일만 바꿔 서로 다른 Agent가 실행된다는 점이다.",
  },
  evaluation: {
    title: "Evaluation: 기존 방식 vs Builder 방식",
    subtitle: "교수님 피드백에 따라 Agent 생성 과정 자체를 비교한다.",
    table: [
      ["작업 단계", "직접 구현 방식", "Builder 방식"],
      ["실행 흐름 설계", "Agent마다 직접 설계", "고정 흐름 재사용"],
      ["Weather API", "호출 코드 직접 작성", "기존 Tool 재사용"],
      ["쇼핑 기록 분석", "분석 로직 직접 작성", "shopping.py 재사용"],
      ["추천 규칙", "Python 코드 수정", "JSON rule 수정"],
      ["출력 형식", "코드에서 문자열 수정", "output_template 수정"],
      ["테스트", "단계별 직접 확인", "trace로 확인"],
    ],
  },
  metrics: {
    title: "Implementation Metrics",
    subtitle: "현재 코드 기준으로 확인 가능한 객관적 지표",
    table: [
      ["항목", "값"],
      ["지원 Agent 수", "3"],
      ["Agent 설정 파일 수", "3"],
      ["Outfit config", "58 lines"],
      ["Travel config", "58 lines"],
      ["Commute config", "58 lines"],
      ["공통 실행 엔진", "248 lines"],
      ["쇼핑 분석 모듈", "85 lines"],
      ["전체 테스트", "6"],
    ],
    table2: [
      ["구성 요소", "재사용 여부"],
      ["engine.py", "3개 Agent에서 재사용"],
      ["shopping.py", "3개 Agent에서 재사용"],
      ["shopping_history.json", "3개 Agent에서 재사용"],
      ["Weather API", "3개 Agent에서 재사용"],
      ["output_template", "Agent별 config에서 변경"],
    ],
  },
  time: {
    title: "Process Time Log",
    subtitle: "실제 시간은 팀 작업 기록으로 채워야 한다.",
    table: [
      ["작업 단계", "Outfit", "Travel", "Commute", "해석"],
      ["문제 정의", "기록 필요", "기록 필요", "기록 필요", "세 Agent 모두 필요"],
      ["데이터 구조", "기록 필요", "기록 필요", "기록 필요", "B/C는 기존 데이터 재사용"],
      ["API 연결", "기록 필요", "기록 필요", "기록 필요", "B/C는 Weather Tool 재사용"],
      ["쇼핑 분석", "기록 필요", "기록 필요", "기록 필요", "B/C는 shopping.py 재사용"],
      ["추천 규칙", "기록 필요", "기록 필요", "기록 필요", "B/C는 config rule 작성"],
      ["출력 템플릿", "기록 필요", "기록 필요", "기록 필요", "B/C는 output_template 수정"],
      ["총 소요 시간", "기록 필요", "기록 필요", "기록 필요", "Builder 효과 정량화"],
    ],
  },
  demoFlow: {
    title: "Live Demo Plan",
    subtitle: "시연은 기능보다 재사용 구조를 보여주는 순서로 진행한다.",
    bullets: [
      "한국어 UI로 실행한다.",
      "Outfit Agent + User A를 실행하고 쇼핑 기록 분석을 설명한다.",
      "User B로 변경해 개인화 결과가 바뀌는 것을 보여준다.",
      "Travel Packing Agent로 바꿔 Loaded Config 변화를 보여준다.",
      "Commute Agent로 바꿔 세 번째 Agent도 같은 trace로 실행됨을 보여준다.",
    ],
    script: "핵심 설명:\nAgent 자체가 아니라, 같은 engine.py에서 설정 파일만 교체해 다른 Agent가 실행된다는 점이 중요합니다.",
    table: [
      ["확인 위치", "의미"],
      ["Loaded Config", "어떤 JSON 설정이 로드됐는지 확인"],
      ["Execution Trace", "동일한 5단계 실행 흐름 확인"],
    ],
  },
  limit: {
    title: "Limitations",
    subtitle: "MVP 범위를 명확히 말해야 한다.",
    table: [
      ["한계", "설명"],
      ["실제 쇼핑몰 API 미연동", "현재는 모의 쇼핑 기록 JSON 사용"],
      ["완전한 No-code 아님", "현재는 설정 파일을 직접 수정"],
      ["지원 Agent 제한", "현재 3개 예시 Agent"],
      ["추천 품질 평가 미완성", "현재는 생성 과정 효율성 검증 중심"],
    ],
    statement: "향후 Cafe24, Shopify, WooCommerce API 또는 사용자 업로드 파일로 shopping_history 데이터 소스를 교체할 수 있다.",
  },
  conclusion: {
    title: "Conclusion",
    bullets: [
      "본 프로젝트는 특정 Agent 하나가 아니라 Builder MVP를 검증한다.",
      "세 Agent는 같은 실행 엔진과 같은 쇼핑 기록 분석 모듈을 재사용한다.",
      "Agent별 차이는 각각 58줄 규모의 JSON 설정 파일에 정의된다.",
      "다음 단계는 실제 작업 시간을 기록해 Builder 방식의 효율성을 정량화하는 것이다.",
    ],
    final: "결론:\n완전한 플랫폼은 아니지만, 설정 파일 교체만으로 유사 Agent를 실행할 수 있음을 확인했다.",
    table: [
      ["현재 성과", "3개 Agent 정상 실행"],
      ["평가 방향", "제작 시간/수정량 비교"],
    ],
  },
};

const TEXT_ZH = {
  title: "配置驱动 AI Agent Builder MVP",
  subtitle: "用于更快生成结合购物记录与天气数据的个性化 Agent",
  date: "2026.04 | 综合设计发表",
  coverCards: [
    { title: "核心假设", body: "同一套执行引擎，只更换 JSON 配置文件，就能运行不同 Agent。" },
    { title: "Demo 范围", body: "实现穿搭推荐、旅行准备物、通勤/上学准备 3 个 Agent。" },
    { title: "评价重点", body: "不只评价功能，而是评价 Agent 制作过程的工作量与复用性。" },
  ],
  problem: {
    title: "问题定义",
    subtitle: "每做一个特定目的 Agent，都会重复大量相似开发工作。",
    bullets: [
      "输入分析、API 调用、数据分析、推荐规则、输出格式都要重复实现。",
      "添加相似 Agent 时，同样结构的工作仍会重复出现。",
      "因此需要降低 Agent 制作过程本身的成本。",
    ],
    table: [
      ["直接实现步骤", "重复工作"],
      ["输入处理", "解析城市、日期、用户意图"],
      ["工具调用", "连接天气 API 与购物记录数据"],
      ["分析/推荐", "风格分析、温度规则、条件判断"],
      ["输出/UI", "回复模板与页面连接"],
    ],
  },
  goal: {
    title: "目标",
    subtitle: "不是做完整商业平台，而是用 MVP 验证 Builder 的核心可能性。",
    cards: [
      { title: "共通引擎", body: "固定 Plan -> Act -> Analyze -> Decide -> Compose 执行流程。" },
      { title: "配置文件", body: "Agent 之间的差异写在 JSON config 里。" },
      { title: "复用性", body: "用同一引擎运行 3 个相似难度 Agent。" },
    ],
    formula: "same engine.py\n+ different JSON config\n= different Agent behavior",
  },
  method: {
    title: "提出方法",
    subtitle: "固定 Agent 执行流程，把工具、规则和输出交给配置控制。",
    steps: [
      { title: "Plan", body: "确定城市/日期/用户/Agent 配置" },
      { title: "Act", body: "调用 Weather API + shopping_history" },
      { title: "Analyze", body: "从购买记录提取风格和颜色" },
      { title: "Decide", body: "按天气与购买记录应用推荐规则" },
      { title: "Compose", body: "用 output_template 生成回答" },
    ],
    table: [
      ["配置项", "作用"],
      ["tools", "是否使用天气 API 与购物记录"],
      ["temperature_rules", "温度区间推荐规则"],
      ["conditional_extras", "下雨、温差等附加条件"],
      ["output_template", "最终回复格式"],
    ],
  },
  arch: {
    title: "系统架构",
    subtitle: "把共通执行引擎和 Agent 配置文件分离。",
    table: [
      ["组件", "作用"],
      ["web_app.py", "选择 Agent / 用户，展示结果与 trace"],
      ["src/agent_builder/engine.py", "共通执行引擎"],
      ["src/agent_builder/shopping.py", "购物记录分析与已有单品选择"],
      ["configs/*.json", "各 Agent 的推荐规则与输出模板"],
      ["data/shopping_history.json", "模拟购买记录数据"],
      ["WeatherTool", "基于 Open-Meteo 的实时天气查询"],
    ],
  },
  demo: {
    title: "Demo: 3 个相似难度 Agent",
    subtitle: "三个 Agent 使用同一引擎和同一数据分析模块。",
    table: [
      ["Agent", "目的", "Config", "复用部分"],
      ["Outfit", "天气+购物记录的穿搭推荐", "outfit_agent.json", "engine, shopping, weather"],
      ["Travel Packing", "天气+购物记录的旅行准备物推荐", "travel_pack_agent.json", "engine, shopping, weather"],
      ["Commute", "天气+购物记录的通勤/上学准备推荐", "commute_agent.json", "engine, shopping, weather"],
    ],
    note: "重点不是单个 Agent 的功能，而是同一执行引擎通过换配置文件运行不同 Agent。",
  },
  evaluation: {
    title: "评价: 直接实现 vs Builder 方式",
    subtitle: "根据教授反馈，评价 Agent 的制作过程本身。",
    table: [
      ["工作步骤", "直接实现方式", "Builder 方式"],
      ["执行流程设计", "每个 Agent 单独设计", "复用固定流程"],
      ["Weather API", "手写调用代码", "复用已有 Tool"],
      ["购物记录分析", "手写分析逻辑", "复用 shopping.py"],
      ["推荐规则", "修改 Python 代码", "修改 JSON rule"],
      ["输出格式", "在代码里改字符串", "修改 output_template"],
      ["测试", "手动确认每一步", "通过 trace 确认"],
    ],
  },
  metrics: {
    title: "实现指标",
    subtitle: "当前代码中可确认的客观指标",
    table: [
      ["项目", "数值"],
      ["支持 Agent 数", "3"],
      ["Agent 配置文件数", "3"],
      ["Outfit config", "58 行"],
      ["Travel config", "58 行"],
      ["Commute config", "58 行"],
      ["共通执行引擎", "248 行"],
      ["购物分析模块", "85 行"],
      ["全部测试", "6"],
    ],
    table2: [
      ["组件", "复用情况"],
      ["engine.py", "3 个 Agent 复用"],
      ["shopping.py", "3 个 Agent 复用"],
      ["shopping_history.json", "3 个 Agent 复用"],
      ["Weather API", "3 个 Agent 复用"],
      ["output_template", "各 Agent 在 config 中修改"],
    ],
  },
  time: {
    title: "制作时间记录",
    subtitle: "实际耗时需要用团队工作记录补充。",
    table: [
      ["工作阶段", "Outfit", "Travel", "Commute", "解释"],
      ["问题定义", "待记录", "待记录", "待记录", "三个 Agent 都需要"],
      ["数据结构", "待记录", "待记录", "待记录", "B/C 复用已有数据"],
      ["API 连接", "待记录", "待记录", "待记录", "B/C 复用 Weather Tool"],
      ["购物分析", "待记录", "待记录", "待记录", "B/C 复用 shopping.py"],
      ["推荐规则", "待记录", "待记录", "待记录", "B/C 只写 config rule"],
      ["输出模板", "待记录", "待记录", "待记录", "B/C 只改 output_template"],
      ["总耗时", "待记录", "待记录", "待记录", "量化 Builder 效果"],
    ],
  },
  demoFlow: {
    title: "现场演示流程",
    subtitle: "演示顺序要突出复用结构，而不是只展示功能。",
    bullets: [
      "切换到韩语 UI。",
      "运行 Outfit Agent + User A，说明购物记录分析。",
      "切换 User B，展示个性化结果变化。",
      "切换 Travel Packing Agent，展示 Loaded Config 变化。",
      "切换 Commute Agent，说明第三个 Agent 也使用同样 trace。",
    ],
    script: "核心说明:\n重点不是 Agent 本身，而是同一个 engine.py 通过更换配置文件运行不同 Agent。",
    table: [
      ["确认位置", "意义"],
      ["Loaded Config", "确认加载了哪个 JSON 配置"],
      ["Execution Trace", "确认相同 5 步执行流程"],
    ],
  },
  limit: {
    title: "限制",
    subtitle: "需要明确 MVP 的边界。",
    table: [
      ["限制", "说明"],
      ["未接真实购物平台 API", "当前使用模拟购物记录 JSON"],
      ["不是完整 No-code", "当前仍需直接编辑配置文件"],
      ["Agent 数量有限", "当前 3 个示例 Agent"],
      ["推荐质量评估未完成", "当前重点是制作过程效率验证"],
    ],
    statement: "后续可把 shopping_history 数据源替换成 Cafe24、Shopify、WooCommerce API 或用户上传文件。",
  },
  conclusion: {
    title: "结论",
    bullets: [
      "本项目不是只做一个 Agent，而是验证 Builder MVP。",
      "三个 Agent 复用同一执行引擎和购物记录分析模块。",
      "每个 Agent 的差异由 58 行左右的 JSON 配置文件定义。",
      "下一步需要记录真实制作时间，量化 Builder 方式的效率。",
    ],
    final: "结论:\n虽然还不是完整平台，但已经证明更换配置文件即可运行相似 Agent。",
    table: [
      ["当前成果", "3 个 Agent 正常运行"],
      ["评价方向", "制作时间 / 修改量对比"],
    ],
  },
};

async function main() {
  const koDeck = buildDeck("ko");
  await koDeck.writeFile({ fileName: OUT_KO });
  const zhDeck = buildDeck("zh");
  await zhDeck.writeFile({ fileName: OUT_ZH });
  console.log(OUT_KO);
  console.log(OUT_ZH);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

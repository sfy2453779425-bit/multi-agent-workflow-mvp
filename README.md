# Personalized Outfit Recommendation Builder MVP

This project is no longer just an outfit recommendation demo. It is now a
**Sample Workflow + Template-based Builder Prototype** for personalized
recommendation workflows.

The current semester scope is intentionally limited:

- Build a working recommendation Sample Workflow.
- Define reusable Workflow Templates.
- Generate executable Workflow JSON from templates.
- Show how the same idea maps to Flowise / Dify / Langflow style builders.

## Project Position

Existing tools such as Flowise, Dify, and Langflow already provide general
workflow builders. This project does not try to replace them.

Our contribution is the recommendation-domain workflow structure:

```text
User Input
-> Question Node
-> Weather Tool Node
-> Shopping History Analysis Node
-> Recommendation Node
-> Compose Node
```

In Korean:

```text
기존 Builder를 대체하는 것이 아니라,
개인화 추천 도메인에 필요한 Workflow Template을 정의하고
실행 가능한 MVP로 검증한다.
```

## Main Demo

Run the stable desktop Sample Workflow:

```bat
run_desktop.cmd
```

Example query:

```text
다음 주에 칭다오 여행 가는데 캐주얼 옷 추천해줘
```

The app runs the 6-node workflow and returns:

- weather-based context
- shopping-history style analysis
- ranked outfit recommendations
- execution trace

## Builder Prototype

Run the local Builder Prototype:

```bat
run_builder_app.cmd
```

The Builder Prototype supports:

- reusable node palette
- template selection
- required-node validation
- Workflow JSON generation
- generated Workflow execution
- multiple recommendation templates

Current templates:

```text
configs/builder_templates/outfit_recommendation_template.json
configs/builder_templates/commute_outfit_template.json
```

## Visual Web Verification

If you do not want to inspect backend code, run the visual web page:

```bat
run_web.cmd
```

Then open:

```text
http://127.0.0.1:8000
```

The page shows:

- selected Workflow Template
- Node Palette and sequential Workflow structure
- Builder mapping table
- generated Workflow JSON
- visual run result and execution trace

## Static Builder Preview

Open this directly in a browser:

```text
workflow_builder_preview.html
```

This is a static visual explanation page for presentation. The runnable builder
is `run_builder_app.cmd`.

## Command Line Verification

List available templates:

```powershell
python builder_demo.py --list-templates
```

Show the default builder template:

```powershell
python builder_demo.py --show-builder
```

Generate and run the travel/outfit template:

```powershell
python builder_demo.py --run-generated "칭다오 다음 주 여행 캐주얼 옷 추천해줘" --user user_a
```

Generate and run the commute/work template:

```powershell
python builder_demo.py --run-generated --builder-template configs\builder_templates\commute_outfit_template.json "서울 내일 출근 포멀 옷 추천해줘" --user user_b
```

Run project verification:

```bat
run_verify.cmd
```

## External Builder Tool PoC

These folders document external builder validation paths:

```text
external_tools/flowise_poc/
external_tools/dify_poc/
external_tools/langflow_poc/
```

Start Flowise PoC entry point:

```bat
external_tools\flowise_poc\run_flowise_poc.cmd
```

Start Langflow PoC entry point:

```bat
external_tools\langflow_poc\run_langflow_poc.cmd
```

Check Dify requirement:

```bat
external_tools\dify_poc\run_dify_poc.cmd
```

Current verified external-tool facts:

- Flowise npm package exists at version `3.1.2`.
- Langflow package index shows latest version `1.9.4`.
- Dify needs Docker / Docker Compose; Docker is not installed on this machine.
- Flowise local install/start was attempted but timed out because of its large dependency tree, so the stable demo remains the local Python Builder Prototype.

## Tests

Run:

```bat
run_tests.cmd
```

Expected result:

```text
16 tests OK
```

## Project Structure

```text
.
|-- configs/
|   |-- outfit_workflow.json
|   |-- outfit_agent.json
|   |-- flowise_poc_mapping.json
|   `-- builder_templates/
|       |-- outfit_recommendation_template.json
|       `-- commute_outfit_template.json
|-- data/
|   |-- shopping_history.json
|   `-- user_profiles.json
|-- deliverables/
|   |-- builder_tool_comparison_kr.md
|   |-- competitor_positioning_kr.md
|   |-- dataset_research_kr.md
|   |-- external_builder_tool_verification_zh.md
|   |-- final_acceptance_checklist_zh.md
|   |-- mentor_requirement_alignment_zh.md
|   |-- next_presentation_outline_kr.md
|   |-- ppt_4_slides_builder_addon_kr.md
|   `-- professor_answer_drill_kr.md
|-- external_tools/
|   |-- flowise_poc/
|   |-- dify_poc/
|   `-- langflow_poc/
|-- src/
|   |-- agent_builder/
|   |   |-- engine.py
|   |   |-- workflow.py
|   |   |-- template_builder.py
|   |   `-- shopping.py
|   `-- weather_agent/
|-- tests/
|-- desktop_app.py
|-- builder_app.py
|-- web_app.py
|-- builder_demo.py
|-- verify_project.py
|-- workflow_builder_preview.html
|-- run_desktop.cmd
|-- run_builder_app.cmd
|-- run_verify.cmd
`-- run_tests.cmd
```

## Current Features

- Sequential 6-node recommendation workflow
- Question Node for missing city/date/purpose/style
- Weather API integration
- simulated shopping history analysis
- ranked recommendation output
- local desktop Sample Workflow demo
- local template-based Builder Prototype
- two recommendation templates using the same Builder mechanism
- generated Workflow JSON execution
- Flowise / Dify / Langflow comparison and PoC entry points
- presentation and Q&A deliverables

## Out of Scope

The current MVP does not claim to be:

- a full production drag-and-drop Builder
- a complete commercial recommendation engine
- a real shopping-platform OAuth integration
- a local LLM training system
- an enterprise monitoring/admin system

## Presentation Answer

Use this if asked why this project matters when Flowise / Dify / Langflow
already exist:

```text
저희는 기존 Builder 자체를 대체하려는 것이 아닙니다.
기존 Builder는 범용 도구이기 때문에 추천 도메인에 필요한
사용자 정보 보완, 쇼핑 기록 분석, 날씨 반영, 추천 우선순위화 같은
도메인 특화 Workflow Template은 직접 정의해야 합니다.

그래서 저희는 기존 Builder를 참고하면서,
개인화 추천 Agent Workflow의 구조를 설계하고
로컬 Builder Prototype으로 검증했습니다.
```

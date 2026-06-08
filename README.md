# Multi-Agent Workflow Builder MVP

This project is a **template-based Multi-Agent Workflow Builder MVP**. The
outfit recommendation workflow is now one executable domain example, alongside
presentation planning and customer support ticket routing examples.

The current semester scope is intentionally limited:

- Build working workflows across multiple domains.
- Define reusable Workflow Templates.
- Compose custom workflows in the Builder Workspace.
- Generate executable Workflow JSON from templates or workspace inputs.
- Show how the same idea maps to Flowise / Dify / Langflow style builders.

## Project Position

Existing tools such as Flowise, Dify, and Langflow already provide general
workflow builders. This project does not try to replace them.

Our contribution is the domain-template workflow structure:

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
- Builder Workspace composition
- required-node validation
- Workflow JSON generation
- generated Workflow execution
- multiple domain workflow templates

Current templates:

```text
configs/builder_templates/outfit_recommendation_template.json
configs/builder_templates/commute_outfit_template.json
configs/builder_templates/presentation_planning_template.json
configs/builder_templates/customer_support_ticket_template.json
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
- Builder Workspace for composing a custom workflow name and business domain
- Node Palette and sequential Workflow structure
- Builder mapping table
- generated Workflow JSON
- visual run result and execution trace

## Harness Engineering Comparison

Run the comparison experiment:

```bat
tools\dev\run_harness_comparison.cmd
```

The experiment compares two construction paths for the same tasks:

- Generic Harness Engineering: manually define Agent roles, tools, context,
  constraints, verification, and execution order.
- Builder Workspace: select a business preset, name the Workflow, generate
  executable Workflow JSON, and run the same 6-step trace.

Outputs:

```text
outputs/harness_comparison/harness_comparison_results.json
outputs/harness_comparison/harness_comparison_report_zh.md
outputs/harness_comparison/harness_comparison_report_kr.md
```

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

Generate and run the presentation planning template:

```powershell
python builder_demo.py --run-generated --builder-template configs\builder_templates\presentation_planning_template.json
```

Generate and run the customer support ticket template:

```powershell
python builder_demo.py --run-generated --builder-template configs\builder_templates\customer_support_ticket_template.json
```

Run project verification:

```bat
run_verify.cmd
```

## GPU Baseline Evidence

If the allocated GPU server is still available, run one final stable baseline
benchmark for the Local LLM Node evidence:

```bat
tools\gpu\run_final_base_benchmark.cmd
tools\gpu\download_final_base_benchmark.cmd
```

The downloaded files are stored locally under:

```text
_local_artifacts\gpu_results\final_base_benchmark
```

This benchmark is evidence collection only. It is not required for normal demo
execution; the stable demo remains `tools\gpu\run_gpu_replay_demo.cmd`.

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
tools\dev\run_tests.cmd
```

Expected result:

```text
28 tests OK
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
|       |-- commute_outfit_template.json
|       |-- presentation_planning_template.json
|       `-- customer_support_ticket_template.json
|-- data/
|   |-- shopping_history.json
|   |-- user_profiles.json
|   |-- presentation_knowledge.json
|   `-- support_policy.json
|-- deliverables/
|   |-- builder_tool_comparison_kr.md
|   |-- competitor_positioning_kr.md
|   |-- dataset_research_kr.md
|   |-- external_builder_tool_verification_zh.md
|   |-- final_acceptance_checklist_zh.md
|   |-- mentor_requirement_alignment_zh.md
|   |-- next_presentation_outline_kr.md
|   |-- ppt_4_slides_builder_addon_kr.md
|   |-- professor_answer_drill_kr.md
|   `-- forms/
|       `-- *.txt
|-- experiments/
|   |-- harness_comparison.py
|   `-- gpu_llm/
|       |-- local_llm_api_server.py
|       |-- run_local_llm_api_server.sh
|       `-- smoke_local_llm_api.py
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
|-- tools/
|   |-- dev/
|   |   |-- run_tests.cmd
|   |   `-- run_harness_comparison.cmd
|   `-- gpu/
|       |-- upload_gpu_api_update.cmd
|       |-- start_gpu_local_llm_api.cmd
|       |-- open_gpu_local_llm_tunnel.cmd
|       |-- verify_gpu_remote_node.cmd
|       |-- run_local_llm_remote_demo.cmd
|       `-- run_gpu_replay_demo.cmd
|-- _local_artifacts/       # ignored local packages, GPU outputs, temporary PPTs
|-- desktop_app.py
|-- builder_app.py
|-- web_app.py
|-- builder_demo.py
|-- verify_project.py
|-- workflow_builder_preview.html
|-- run_desktop.cmd
|-- run_builder_app.cmd
|-- run_verify.cmd
`-- run_web.cmd
```

## Current Features

- Sequential 6-node recommendation workflow
- Question Node for missing city/date/purpose/style
- Weather API integration
- simulated shopping history analysis
- ranked recommendation output
- optional Local LLM Node with mock, replay, and remote providers
- local desktop workflow run
- local template-based Builder Prototype
- four templates across recommendation, presentation planning, and support
- generated Workflow JSON execution
- Flowise / Dify / Langflow comparison and PoC entry points
- presentation and Q&A deliverables

## Stable GPU Evidence Mode

Use replay mode for the stable GPU-related demo:

```bat
tools\gpu\run_gpu_replay_demo.cmd
```

Replay mode reads a previously downloaded Qwen result JSON and appends it as a
`Local LLM Node` in the workflow trace. It does not require SSH, an open tunnel,
or a live GPU API process. The live remote API scripts remain available under
`tools/gpu/`, but they are experimental because they depend on remote process,
CUDA, tunnel, and port state.

## Out of Scope

The current MVP does not claim to be:

- a full production drag-and-drop Builder
- a complete commercial recommendation engine
- a real shopping-platform OAuth integration
- a local LLM training system
- an enterprise monitoring/admin system

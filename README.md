# Personalized Outfit Recommendation Workflow MVP

This repository contains a clean technical MVP for a **personalized outfit
recommendation system** that integrates weather, user preferences, and
shopping history.

- **Product goal**: personalized outfit recommendation for travel and daily
  scenarios.
- **Implementation strategy**: JSON-based Workflow composed of 6 reusable
  Workflow Nodes (Request Parser → Question → Weather Tool → Shopping History
  Analysis → Recommendation → Compose).
- **Future extension**: visual Builder UI, real shopping platform API, larger
  recommendation rule sets.

This MVP proves one idea:

> A user request like "다음 주에 칭다오 여행 가는데 옷 추천해줘" can be handled
> by composing 6 small Workflow Nodes defined in JSON, so adding new
> scenarios only requires filling a config template — not rewriting code.

## Do Not Open Python Files To Run The Frontend

If you click `builder_demo.py` or `web_app.py` in VS Code, you will see source
code. That is expected.

To see the frontend UI, you must start the local web server first.

On Windows:

```bat
run_web.cmd
```

Then open this URL in a browser:

```text
http://127.0.0.1:8000
```

If the terminal prints another port, open the printed URL instead.

## Main Web Demo

Run:

```bat
run_web.cmd
```

The web page shows:

- user input
- user selection
- workflow output
- 6-Node Workflow execution trace
- shopping history analysis
- loaded config summary

Default workflow (6 Nodes):

```text
Request Parser Node
-> Question Node                       (clarifies missing purpose / style)
-> Weather Tool Node
-> Shopping History Analysis Node
-> Recommendation Node
-> Compose Node
```

## Command Line Demo

Run the 6-Node Workflow:

```powershell
python builder_demo.py --workflow
```

Run all single-Config demos:

```bat
run_builder_demo.cmd
```

## Tests

Run:

```bat
run_tests.cmd
```

Expected result:

```text
9 tests OK
```

## Project Structure

```text
.
├── configs/
│   ├── outfit_workflow.json
│   ├── outfit_agent.json
│   ├── travel_pack_agent.json
│   └── commute_agent.json
├── data/
│   ├── shopping_history.json
│   └── user_profiles.json
├── src/
│   ├── agent_builder/
│   │   ├── engine.py
│   │   ├── workflow.py
│   │   └── shopping.py
│   └── weather_agent/
│       ├── tools.py
│       └── models.py
├── tests/
├── web_app.py
├── builder_demo.py
└── run_web.cmd
```

## Current Features

- Sequential 6-Node Workflow execution
- Config-driven Node behavior (JSON Workflow definition)
- Open-Meteo weather API integration (supports Seoul, Tokyo, Qingdao, Beijing, etc.)
- Question Node that detects missing context (purpose / style) and asks the user
- Local simulated shopping history analysis
- Personalized recommendation based on weather and purchase history
- Web UI for demo and Workflow Trace inspection
- Unit tests for single-Config and Workflow behavior (including clarification short-circuit)

## Current MVP Scope

In scope:

- JSON workflow definition
- sequential 6-Node Workflow execution
- weather tool call
- shopping history analysis
- recommendation rule matching
- web UI trace display
- tests

Out of scope:

- full drag-and-drop Builder
- admin dashboard
- real shopping-platform OAuth integration
- local LLM training
- complex orchestration such as retry, branching, or monitoring

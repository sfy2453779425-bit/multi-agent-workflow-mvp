# Multi-Agent Workflow Builder MVP

This repository contains a clean technical MVP for a template-based
Multi-Agent Workflow Builder.

The project is not a finished Agent Builder platform. It is a minimal demo
that proves one idea:

> A JSON workflow config can define multiple small Agents and run them in a
> fixed order to handle one user request.

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
- multi-Agent execution trace
- shopping history analysis
- loaded config summary

Default workflow:

```text
Request Parser Agent
-> Weather Agent
-> Shopping Analysis Agent
-> Recommendation Agent
-> Compose Agent
```

## Command Line Demo

Run the multi-Agent workflow:

```powershell
python builder_demo.py --workflow
```

Run all single-Agent config demos:

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
7 tests OK
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

- Sequential multi-Agent workflow execution
- Config-driven Agent behavior
- Open-Meteo weather API integration
- Local simulated shopping history analysis
- Personalized recommendation based on weather and purchase history
- Web UI for demo and trace inspection
- Unit tests for single-Agent and workflow behavior

## Current MVP Scope

In scope:

- JSON workflow definition
- sequential Agent execution
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

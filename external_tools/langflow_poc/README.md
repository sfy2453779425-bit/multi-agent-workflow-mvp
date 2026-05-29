# Langflow PoC Environment

This folder documents a reproducible Langflow verification path for the workflow
builder MVP.

## Verification

On 2026-05-28, the local Python package index check succeeded:

```powershell
python -m pip index versions langflow
```

Observed latest version:

```text
langflow (1.9.4)
```

## Start Langflow

Langflow is Python-based. To run it locally:

```powershell
python -m pip install "langflow==1.9.4"
python -m langflow run --host 127.0.0.1 --port 7860
```

Then open:

```text
http://127.0.0.1:7860
```

## How it maps to this project

The custom component candidate is:

```text
src/agent_builder/template_builder.py
```

The intended Langflow component would:

1. Load a template from `configs/builder_templates/`.
2. Generate Workflow JSON through `TemplateWorkflowBuilder`.
3. Execute it with `MultiAgentWorkflowEngine`.

This has not been installed into Langflow yet because the stable current demo is
the local Python Builder Prototype.

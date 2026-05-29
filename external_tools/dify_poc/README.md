# Dify PoC Environment

This folder documents the Dify verification path for the workflow builder MVP.

## Current local environment check

On 2026-05-28, Docker was checked locally:

```powershell
docker --version
docker compose version
```

Result:

```text
docker: command not found
```

Therefore Dify cannot be run on this machine right now because the standard Dify
self-hosted setup depends on Docker / Docker Compose.

## How to run when Docker is available

Use Dify's official self-hosted setup:

```powershell
git clone https://github.com/langgenius/dify.git
cd dify/docker
copy .env.example .env
docker compose up -d
```

Then open the Dify web console and build a Workflow with the same node structure
as:

```text
configs/builder_templates/outfit_recommendation_template.json
```

## How it maps to this project

Dify would be evaluated as a production-oriented workflow platform:

- Workflow / Chatflow
- Tool calls
- Knowledge / Dataset
- API publishing
- monitoring

The current Python Builder Prototype remains the stable MVP for this semester.

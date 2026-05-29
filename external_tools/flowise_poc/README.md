# Flowise PoC Environment

This folder is a reproducible external-tool verification workspace. It is kept
separate from the Python MVP because Flowise is a Node.js application with its
own dependencies.

## Why this exists

The enterprise mentor asked the team to research existing Agent Builder tools
such as Flowise, Dify, and Langflow. This folder proves that we did not only
write a comparison table: we prepared a runnable Flowise PoC environment that
can be used to recreate the current outfit workflow as a visual AgentFlow.

## Start Flowise

From this folder:

```powershell
npm run start
```

The script uses `npx flowise@3.1.2` so the exact Flowise version is pinned
without committing Node dependencies into this repository.

Then open:

```text
http://127.0.0.1:3100
```

Default local login:

```text
username: admin
password: admin
```

## What to build in Flowise

Create an AgentFlow or workflow with these nodes:

```text
Start / User Input
-> Parser Prompt
-> Condition / Question Node
-> Weather API Tool
-> Shopping History Data Node
-> Recommendation Decision Node
-> Output Template
```

This maps to:

```text
configs/builder_templates/outfit_recommendation_template.json
configs/flowise_poc_mapping.json
```

## Scope

This is not the main demo path. The stable project demo remains:

```text
run_desktop.cmd
run_builder_app.cmd
```

Use Flowise for external-tool validation and screenshots in the presentation.

## Current verification note

On 2026-05-28:

- `npm view flowise version` returned `3.1.2`, confirming that the package is available.
- A full local `npm install` was attempted twice but did not finish within the local timeout because Flowise has a large dependency tree.
- `npm exec --yes flowise@3.1.2 -- --version` was also attempted and timed out after 5 minutes.

For this reason, the repository keeps a pinned Flowise runner and documents the
intended visual PoC mapping, but the stable runnable demo remains the local
Python Builder Prototype.

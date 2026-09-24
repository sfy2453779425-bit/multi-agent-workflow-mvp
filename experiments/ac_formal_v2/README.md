# AC Formal v2 collection and replay

This directory freezes the prompt inputs and provides collection/replay tooling for the three-model, six-case experiment. `SMOKE01` is used only for the pre-collection smoke test; formal collection uses the six frozen cases only after the collection-tooling freeze and tag are in place.

## Frozen inputs and prompt source

The six frozen prompts are rendered by the existing `build_condition_prompt` in `experiments/authoritative_contract/pilot/pilot.py`, which uses the shared prompt builder in `src/agent_builder/generative_provider.py`. No new prompt wording is defined here. Each exported prompt file contains one canonical user message and its input/hash evidence. The exporter checks the frozen pilot-v4 prompt hashes for all six cases and Equality Pilot prompt hashes for cases that Equality Pilot recorded.

`config/schedule.json` freezes 54 cells: six cases × three models × three runs. The schedule uses seed `20260924`, with rows shuffled inside each run. Collection starts three provider workers concurrently; each worker processes only its own rows in schedule order and writes only its provider-specific append-only file. The merged `calls.jsonl` is written in `schedule_index` order after the workers finish.

## API mapping

- DeepSeek: existing frozen `DeepSeekResponsesProvider` and Runtime path; it builds the request itself. The adapter uses the Responses API, `reasoning.effort=none`, and `max_output_tokens=1024`; no JSON mode, schema, tools, temperature, or top-p are added.
- GPT (`gpt-5.6`): direct OpenAI Responses API. Canonical message roles and text are placed in `input`; minimum configured reasoning effort is `none`, with `max_output_tokens=1024`.
- Claude (`claude-opus-5-5`): direct Anthropic Messages API. A canonical `system` message, if present, maps to top-level `system`; remaining messages map to `messages`. The frozen prompt currently has one `user` message. `max_tokens=1024`; extended thinking is omitted.

Only credentials from process environment variables are read: `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, and `ANTHROPIC_API_KEY`. Keys are never serialized into request artifacts or logs. Temperature, top-p, and seed are not sent; `sampling_parameters` is recorded as `not_set_provider_default`.

## Retry and artifact rules

Each provider worker is sequential. Only network errors, HTTP 429, and HTTP 5xx are retried, up to three attempts with exponential backoff. HTTP 4xx stops collection. Empty output, truncation, refusal, malformed JSON, or parser failure is recorded as received and never retried. Raw provider response bodies are stored per call without request headers. Raw files are append-only; replay creates separate derived records and never edits raw data. No conflict/correctness analysis is performed by these tools.

## Commands (PowerShell)

Set credentials in the invoking process only; do not put key values in this repository:

```powershell
$env:DEEPSEEK_API_KEY = '<DeepSeek key>'
$env:OPENAI_API_KEY = '<OpenAI key>'
$env:ANTHROPIC_API_KEY = '<Anthropic key>'
python -B -m experiments.ac_formal_v2.collect --prepare
python -B -m experiments.ac_formal_v2.collect --smoke
python -B -m experiments.ac_formal_v2.replay --smoke
```

The smoke command uses only the synthetic `SMOKE01` case and runs the three provider workers concurrently. After smoke validation, the collection-tooling commit/tag, and the required remote merge/push:

```powershell
python -B -m experiments.ac_formal_v2.collect --formal
python -B -m experiments.ac_formal_v2.replay
```

Formal raw records are written to `raw/ac_formal_3model_6case_20260924_v2/`; replay records go to `derived/ac_formal_3model_6case_20260924_v2/`. Do not edit frozen prompts, schedule, or code after the first formal API call.

## Tests

```powershell
python -B -m unittest experiments.ac_formal_v2.tests.test_tools -q
python -B -m unittest discover -s tests -q
```

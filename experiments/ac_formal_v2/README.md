# AC Formal v2 collection and replay

This folder freezes six canonical customer-support prompts for 54 independent calls: six cases × three providers × three runs. The canonical prompt is rendered by the existing `build_condition_prompt` in `experiments/authoritative_contract/pilot/pilot.py`; this collection layer adds no prompt wording. The stored prompt text and its hash remain unchanged.

## Provider paths

- DeepSeek: frozen `DeepSeekResponsesProvider` and online Runtime path; `deepseek-v4-pro`, Responses API, `reasoning.effort=none`, `max_output_tokens=1024`.
- GPT: official Codex CLI, model `gpt-6-astra`, reasoning effort `low`, configured output ceiling 1024. Each call uses a fresh process/session, an empty temporary working directory, a temporary `CODEX_HOME` containing only the copied Codex login file and minimal config, read-only sandbox, no shell/web/MCP tools, and the exact canonical prompt on stdin. A neutral `model_instructions_file` was accepted, but its probe input was 7,405 tokens versus 11,533 with default instructions (35.8% lower, below the predeclared 50% threshold); the frozen collection therefore retains default Codex instructions. The ~11.5k figure is total probe input, not an isolated instruction-only count. No API key is used.
- Claude: official Claude Code CLI through `cli_claude/run_claude_cli.py` v1.2, one fresh `claude -p --output-format json` process per call. The corrected runner retries only timeouts and HTTP 429/5xx/529; CLI/content errors are recorded once. Claude Code CLI has no effective output-token cap: `max_tokens` is recorded as `not_enforceable_cli`, and output above the 1024-token reference is flagged without truncation. The runner is supplied for the Claude-side operator; Codex does not run it.

The schedule uses seed `20260924`, with rows shuffled within each run. Provider-specific CLI outputs live under `cli_raw/<EXPERIMENT_ID>/`; standard imported records and the merged `calls.jsonl` live under `raw/<EXPERIMENT_ID>/`. CLI imports preserve raw output and do not make correctness judgments. `replay.py` runs the saved text through the frozen Runtime and writes derived records separately.

## Isolation, credentials, and retries

DeepSeek reads `DEEPSEEK_API_KEY` from the current process environment. GPT uses the current Codex account login; Claude uses the current Claude Code login. Do not use or copy API keys from chat. Keys and authorization headers are never written to this repository or artifacts.

GPT and Claude receive the same canonical user text with no extra case-specific instructions. GPT uses `codex exec` with `--sandbox read-only`, no shell tool, disabled web search, and no MCP config. The GPT runner stores the exact JSONL stdout and extracted final assistant text without printing the response. For GPT, empty, malformed, refused, or truncated CLI output is preserved and not retried; only recognized network errors, HTTP 429, or HTTP 5xx are retried, at most three attempts with exponential backoff. Claude has the corresponding v1.2 transport-only retry behavior described above.

The prior official-API 401 smoke artifacts remain unchanged. Legacy `--smoke` and mixed-provider `--formal` commands are disabled for this CLI collection path.

## Commands (PowerShell)

One neutral GPT connectivity probe (not a frozen case, not formal data):

```powershell
python -B -m experiments.ac_formal_v2.cli_gpt.run_gpt_cli --probe
```

After the collection freeze tag is published, run the frozen DeepSeek and GPT arms:

```powershell
$env:DEEPSEEK_API_KEY = '<DeepSeek key>'
python -B -m experiments.ac_formal_v2.collect --deepseek-only-formal
python -B -m experiments.ac_formal_v2.cli_gpt.run_gpt_cli --formal
```

The Claude operator runs the frozen `cli_claude/run_claude_cli.py --formal` command and notifies the experiment owner when the 18 calls are complete. Only then import and merge the three provider logs, and replay:

```powershell
python -B -m experiments.ac_formal_v2.import_cli
python -B -m experiments.ac_formal_v2.replay
```

Do not run any formal command before the freeze tag. Do not rerun or overwrite existing outputs; interrupted/failed attempts remain recorded for review.

## Tests

```powershell
python -B -m unittest experiments.ac_formal_v2.tests.test_tools -q
python -B -m unittest experiments.ac_formal_v2.tests.test_cli_tools -q
python -B -m unittest discover -s tests -q
```

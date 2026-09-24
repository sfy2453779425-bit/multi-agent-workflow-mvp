# Deviations and input-file read log

## Prior read event

- Read time: 2026-09-24 (Asia/Seoul), during the immediately preceding task turn. The tool transcript did not retain the exact time of that read; this is recorded as unavailable rather than guessed.
- Path: `experiments/authoritative_contract/pilot_v4/fixture_hashes_v1.json`
- Note: **输入侧 hash 清单，未读取任何模型输出，无影响**。

## Previously read files under old experiment directories

Only frozen inputs, source code, or explicitly permitted prompt-hash metadata were read. No raw model response, candidate, runtime decision, final output, evaluation result, or statistical summary was read or used.

| Path | Use |
|---|---|
| `experiments/authoritative_contract/pilot/pilot.py` | Inspect the existing canonical prompt helper, frozen case/hash routines, and runtime entry point for reuse. |
| `experiments/authoritative_contract/pilot_v4.py` | Inspect source-only freeze, prompt, and fixture hashing logic. |
| `experiments/authoritative_contract/pilot_v3.py` | Search source for the existing case-hash convention only. |
| `experiments/authoritative_contract/main/e2_runner.py` | Search source for case identifiers and JSON-hash conventions only; no main-experiment artifacts were opened. |
| `experiments/authoritative_contract/provider_diagnostics/responses/stability_probe.py` | Search source for the existing JSON-hash helper only; no probe output was opened. |
| `experiments/authoritative_contract/pilot_v4/cases_v1.json` | Frozen case fixtures used to render the six prompts. |
| `experiments/authoritative_contract/pilot_v4/fixture_hashes_v1.json` | Input-side fixture hash list only. |
| `experiments/authoritative_contract/pilot_v4/prompt_hashes_v1.json` | Input-side prompt hashes only, to cross-check regenerated prompt text. |
| `experiments/authoritative_contract/pilot_v4/workflow_v1.json` | Frozen workflow configuration needed to invoke the existing Runtime. |
| `experiments/authoritative_contract/prompt_equality_pilot.py` | Inspect the Equality Pilot's prompt construction and hash-comparison logic. |
| `experiments/authoritative_contract/prompt_equality_pilot_v1/equality_results.csv` | Extract prompt-equality/hash columns only; no model output fields were used. |
| `experiments/authoritative_contract/prompt_equality_pilot_v1/manifest.json` | Inspect hash/metadata lines only; no model output or evaluation fields were used. |

## Other frozen input read

| Path | Use |
|---|---|
| `data/support_policy.json` | Frozen policy input for prompt rendering and offline Runtime replay. |

## Protected artifacts

No files under `experiments/authoritative_contract/main/` or the invalidated `authoritative_contract_main_6case_20260920_v1` were read, modified, moved, or used. All previously listed files remain read-only.

## Provider CLI migration and limits

- Reason: **外部模型 API 返回 401，改为官方 CLI 的独立会话**. DeepSeek remains on its frozen official Responses API path; GPT and Claude use their official CLIs.
- Claude Code CLI v1.2 has no effective output-token limit. `CLAUDE_CODE_MAX_OUTPUT_TOKENS=1024` did not enforce a cap in the reported test (1,670 output tokens, normal end-turn). The frozen config therefore records `max_tokens = not_enforceable_cli`; each formal result records output token usage and flags values above the 1,024-token reference.

## Codex neutral-instruction probe

- Probe: one isolated `gpt-6-astra` call on `Reply with the single word OK.` with reasoning effort `low`; no formal case was used.
- A one-line `model_instructions_file` containing `Follow the user's instructions.` was accepted. The probe reported 7,405 input tokens, compared with 11,533 in the preceding default-instruction probe, a 35.8% reduction. Because this did not meet the predeclared 50% reduction threshold, the collection keeps the default Codex instructions.
- The approximately 11.5k value is total input tokens for the default-instruction probe; an instruction-only token count was unavailable. The probe artifact is retained under the ignored `cli_raw/_probe/` directory and is not part of the freeze commit.

## Claude formal collection interruption and resume

Claude 正式采集中断与续跑：run_claude_cli.py --formal 于 2026-09-24T16:44:30Z 开始，完成 13/18 次（schedule #02–#39）后被操作者中断，属于工具调用中断，与内容无关。中断时没有产生不完整文件，已完成的 13 次都有输出文件和日志，sha256 一致。2026-09-24T17:01:01Z 用 cli_claude/resume_claude_cli.py 续跑剩余 5 次（#42、#48、#50、#52、#53）。该脚本直接调用冻结版 runner 的函数，冻结检查照常执行，没有重跑或覆盖任何已完成的调用。18 次全部成功，没有超过 1024 输出 token 的调用。

## GPT CLI output-limit observation

- All 18 formal Codex CLI records reported that `model_max_output_tokens` was ignored. The configured 1,024-token ceiling therefore was not enforceable through this CLI setting. The largest observed GPT output was 77 tokens; no formal GPT output exceeded 1,024 tokens, and all calls completed. No calls were repeated or altered because of this observation.

# Formal comparison tables

## Table 1 — Problem incidence

| model | case_id | parse_success | unauthorized_fields | field_conflict | text_conflict |
| --- | --- | --- | --- | --- | --- |
| DeepSeek | CS01 | 3/3 | 0/3 | 0/3 | 0/3 |
| DeepSeek | CS04 | 3/3 | 0/3 | 0/3 | 3/3 |
| DeepSeek | CS06 | 3/3 | 0/3 | 0/3 | 0/3 |
| DeepSeek | CS08 | 3/3 | 0/3 | 0/3 | 3/3 |
| DeepSeek | CS10 | 3/3 | 0/3 | 0/3 | 3/3 |
| DeepSeek | CS12 | 3/3 | 0/3 | 0/3 | 0/3 |
| GPT | CS01 | 3/3 | 0/3 | 0/3 | 0/3 |
| GPT | CS04 | 3/3 | 0/3 | 0/3 | 0/3 |
| GPT | CS06 | 3/3 | 0/3 | 0/3 | 0/3 |
| GPT | CS08 | 3/3 | 0/3 | 0/3 | 0/3 |
| GPT | CS10 | 3/3 | 0/3 | 0/3 | 0/3 |
| GPT | CS12 | 3/3 | 0/3 | 0/3 | 0/3 |
| Claude | CS01 | 3/3 | 0/3 | 0/3 | 0/3 |
| Claude | CS04 | 3/3 | 0/3 | 0/3 | 2/3 |
| Claude | CS06 | 3/3 | 0/3 | 0/3 | 0/3 |
| Claude | CS08 | 3/3 | 0/3 | 0/3 | 0/3 |
| Claude | CS10 | 3/3 | 0/3 | 0/3 | 1/3 |
| Claude | CS12 | 3/3 | 0/3 | 0/3 | 0/3 |

## Table 2 — Runtime effect and cost

| model | view | final_field_conflict | final_text_conflict | no_usable_output | fallback_rate | intercept | leak | false_reject | normal_pass | parse_failure_fallback | false_reject_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DeepSeek | C | 0/18 | 9/18 | 0/18 | N/A |  |  |  |  |  |  |
| DeepSeek | O | 0/18 | 9/18 | 0/18 | N/A |  |  |  |  |  |  |
| DeepSeek | D | 0/18 | 0/18 | 18/18 | 50.0% | 9 | 0 | 0 | 9 | 0 | 0.0% (0/9) |
| DeepSeek | F | 0 | 0 | 0 | 100% |  |  |  |  |  |  |
| GPT | C | 0/18 | 0/18 | 0/18 | N/A |  |  |  |  |  |  |
| GPT | O | 0/18 | 0/18 | 0/18 | N/A |  |  |  |  |  |  |
| GPT | D | 0/18 | 0/18 | 18/18 | 0.0% | 0 | 0 | 0 | 18 | 0 | 0.0% (0/18) |
| GPT | F | 0 | 0 | 0 | 100% |  |  |  |  |  |  |
| Claude | C | 0/18 | 3/18 | 0/18 | N/A |  |  |  |  |  |  |
| Claude | O | 0/18 | 3/18 | 0/18 | N/A |  |  |  |  |  |  |
| Claude | D | 0/18 | 0/18 | 18/18 | 50.0% | 3 | 0 | 6 | 9 | 0 | 40.0% (6/15) |
| Claude | F | 0 | 0 | 0 | 100% |  |  |  |  |  |  |
| ALL | D | 0/54 | 0/54 | 54/54 | 33.3% | 12 | 0 | 6 | 36 | 0 | 14.3% (6/42) |

## Table 3 — Experiment notes

| record_type | model_or_case | metric | value |
| --- | --- | --- | --- |
| model | DeepSeek | model_requested | deepseek-v4-pro |
| model | DeepSeek | model_returned | deepseek-v4-pro |
| model | DeepSeek | params_sent | {"max_output_tokens": 1024, "reasoning": {"effort": "none"}} |
| model | DeepSeek | params_unsupported | [] |
| model | DeepSeek | call_time_range | 2026-09-24T17:10:12.999Z → 2026-09-24T17:10:42.618Z |
| model | DeepSeek | successful_calls | 18 |
| model | DeepSeek | transport_failures | 0 |
| model | DeepSeek | finish_reason_distribution | completed: 18 |
| model | GPT | model_requested | gpt-6-astra |
| model | GPT | model_returned | not_available_cli |
| model | GPT | params_sent | {"max_output_tokens": 1024, "model": "gpt-6-astra", "model_instructions": "codex_cli_default_unmodified", "reasoning_effort": "low", "sandbox": "read-only", "shell_tool": false, "web_search": false} |
| model | GPT | params_unsupported | [] |
| model | GPT | call_time_range | 2026-09-24T17:10:49.727Z → 2026-09-24T17:13:05.843Z |
| model | GPT | successful_calls | 18 |
| model | GPT | transport_failures | 0 |
| model | GPT | finish_reason_distribution | completed: 18 |
| model | Claude | model_requested | claude-opus-5-5 |
| model | Claude | model_returned | claude-opus-5-5 |
| model | Claude | params_sent | {"cli_flags": ["-p", "--model", "claude-opus-5-5", "--output-format", "json", "--system-prompt", "", "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence"], "model": "claude-opus-5-5", "system_prompt": "empty", "tools": "disabled"} |
| model | Claude | params_unsupported | [] |
| model | Claude | call_time_range | 2026-09-24T16:44:30.176803+00:00 → 2026-09-24T17:01:26.275366+00:00 |
| model | Claude | successful_calls | 18 |
| model | Claude | transport_failures | 0 |
| model | Claude | finish_reason_distribution | end_turn: 18 |
| prompt_hash_consistency | CS01 | three_model_prompt_text_hash | PASS |
| prompt_hash_consistency | CS04 | three_model_prompt_text_hash | PASS |
| prompt_hash_consistency | CS06 | three_model_prompt_text_hash | PASS |
| prompt_hash_consistency | CS08 | three_model_prompt_text_hash | PASS |
| prompt_hash_consistency | CS10 | three_model_prompt_text_hash | PASS |
| prompt_hash_consistency | CS12 | three_model_prompt_text_hash | PASS |
| DeepSeek | all cases | live_matches_replay | 18/18 |
| all | all | runtime_version | authoritative-contract-v1.1 |
| all | all | validator_version | consistency-validator-v1.1 |
| all | all | evaluator_version | ac-eval-v1.0 |

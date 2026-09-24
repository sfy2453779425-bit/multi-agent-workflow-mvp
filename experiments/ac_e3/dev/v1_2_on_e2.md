# 开发集检查，不作为实验结果

本文件记录 Runtime v1.2 对既有 E2 的离线开发集检查，以及独立合成测试结果。它不是 E3 实验结果，不调用模型/API，也不支持对未见输入作泛化结论。

## E2 范围与完整性

- 输入：E2 的 54 条原始回答（6 个冻结 Case × 3 个模型 × 3 次运行）。逐条检查了原文；没有修改原始回答、Prompt、Fixture、Policy 或 Case。
- 重放：使用现有 `parse_candidate` 和 `experiments/ac_e3/replay_candidates.py`，分别选择 v1.1 / v1.2。
- v1.1：54/54 行的决定与最终输出均通过脚本校验；默认输出文件重新生成后 SHA-256 仍为 `7837CA8F87D679850B0B2187220D978A48E4C75BC3F204FAB14CBE4066470A84`，`git diff` 为空，逐字节一致。
- v1.2：54/54 行解析成功，按默认路径覆盖 `e2_v1_2_replay.jsonl`。没有创建 `_rework` 副本；66a0e90 中的旧文件仍保留在 Git 历史。最终 JSONL 与 `f556899` 的上一版 v1.2 逐字节一致，决定、fallback 和字段状态均无变化。开发中曾发现配送语境把明确标注的 `4-hour SLA` 误归为其他过程时长；通过新增显式 SLA 标签回归测试并修复后，E2 行为恢复为与上一版一致。相对 66a0e90 的旧版 v1.2，12 条 DeepSeek fallback 文本仍体现已过滤的 next actions 和新标题。
- 未读取 `experiments/ac_formal_v2_eval/`。

## 按模型的决定数

| 模型 | v1.1 ACCEPT | v1.1 REJECT | v1.2 ACCEPT | v1.2 REJECT |
|---|---:|---:|---:|---:|
| DeepSeek | 9 | 9 | 6 | 12 |
| GPT | 18 | 0 | 18 | 0 |
| Claude | 9 | 9 | 18 | 0 |
| 合计 | 36 | 18 | 42 | 12 |

v1.2 的 12 条拒绝全部是 `non_reply_echo`：

- DeepSeek：CS01 run 1–2；CS04 run 1–3；CS08 run 1–3；CS10 run 1–3；CS12 run 1。
- GPT 和 Claude：全部接受。

相对 v1.1，共 12 条决定改变：

- Claude 的 9 条拒绝式/对比式回答改为 ACCEPT：CS04 run 1–2、CS06 run 1–2、CS08 run 1–3、CS10 run 1–2。
- DeepSeek 的 CS01 run 1–2 和 CS12 run 1 从 ACCEPT 改为 REJECT，因为回答规范化后与客户输入相同或为其至少 20 个字符的子串。
- 其余 42 条决定不变。相对 `f556899` 上一版 v1.2，本轮没有 E2 决定变化。与本轮预期相比：无不符条目。

逐条核对中，E2 没有提供真正把错误优先级、时限或团队作为事实承诺的回答；其他 42 条通过，不能作为“未见错值冲突也能拦截”的证据。E2 因而无法验证冲突检测的漏检率，也不能替代独立合成测试。

## 合成测试计数

测试口径：`MUST_REJECT` 中目标字段状态为 `CONFLICT` 计为拦截；`MUST_ACCEPT` 中运行时发生 fallback 计为误拒。

| 版本 | 必须拒绝样例 | 拦截 | 漏检 | 必须放行样例 | 误拒 | 放行 |
|---|---:|---:|---:|---:|---:|---:|
| v1.1 | 72 | 45 | 27 | 60 | 30 | 30 |
| v1.2 | 72 | 72 | 0 | 60 | 0 | 60 |

72 条必须拒绝样例覆盖 priority、SLA、owner team，包含 14 条“先复述、后同意/照办”和 5 条金融相关回复时限。原有 53 条样例仍有超过一半不含 `marked`、`reply` 或 `assigned` 等旧提示词。60 条必须放行样例覆盖原有否定、并列否定、对比、复述/引用、团队别称和一般过程时长，并新增：5 条否定的后续动作、5 条同分句权威值重申、5 条不同对象动作、5 条退款/银行入账时长、恢复的 “A one-day reply is not the promised interval.”，以及 5 条在配送/运输语境中明确标注 SLA 的时长。合成样例不复用 E2 回答，除两条为恢复的既有回归句外，其余第三轮措辞均为新写。

第三轮恢复并验证了 “The customer's message asked for P2, and that level was approved.”（必须拒绝）及 “A one-day reply is not the promised interval.”（必须放行）。两条均通过，没有标记为 `expectedFailure` 的样例。

## 66a0e90 中原有 15 项 v1.2 测试的调整

| 原测试 | 本轮调整 | 原因 |
|---|---|---|
| `test_new_runtime_defaults_to_v11_and_v12_is_explicit` | 换成新的合成回复；增加 v1.1 runtime version 与“不注入 v1.2 context/trace 字段”的断言 | 锁定 v1.1 默认行为不变 |
| `test_unknown_validator_version_is_rejected` | 增加 `v1.3` 未知版本输入 | 确认显式版本选择边界 |
| `test_three_assertion_types_are_rejected` | 重写三字段的句子，加入不依赖触发词的断言 | 防止测试继续奖励 cue-word 检测 |
| `test_negation_contrast_and_request_attribution_are_mentions` | 全部改写，并补充值后否定与新客户归因措辞 | 覆盖窄豁免而不复用旧例句 |
| `test_later_assertion_after_attributed_request_is_still_detected` | 改成客户留言提及后、`then` 分句另作断言 | 确认请求复述不豁免后续独立断言 |
| `test_quoted_value_is_not_an_assertion` | 现在显式提供 `user_input`，且引文内容确实来自输入 | 引文只有匹配客户原文才豁免 |
| `test_other_authoritative_values_and_team_aliases_are_supported` | 重写优先级、SLA、团队别称的正确值句子 | 覆盖不同权威值并避免复用原句 |
| `test_multiple_distinct_assertions_for_one_field_are_rejected` | 重写同字段双断言例句 | 保持检测目标，换掉旧措辞 |
| `test_empty_reply_is_rejected_with_structured_reason` | 改用 em-space、空格、换行和 tab 混合输入 | 覆盖 Unicode 空白 |
| `test_missing_message_has_structured_contract_rejection` | 仅替换用户输入句子 | 避免沿用旧例句，契约检查不变 |
| `test_exact_and_punctuation_only_echoes_are_rejected` | 更新请求及其大小写/标点变体 | 让复制检测样例不沿用旧文本 |
| `test_quoted_request_with_a_real_reply_is_not_echo` | 重写客户请求和带实质答复的回复 | 保持“引用不等于照抄”检查，避免旧措辞 |
| `test_high_overlap_with_small_edits_is_rejected` | 重写高重合请求和回复 | 保持阈值测试，换成独立样例 |
| `test_assertion_rejection_has_field_value_sentence_and_trace_code` | 更换冲突句子 | 保留字段、值、权威值、触发句和 trace 检查 |
| `test_fallback_includes_policy_actions_and_passes_v12` | 改为要求至少一条安全 action、新标题、自检通过及 fallback 可再次通过；冲突 action 的过滤另测 | 不再假设所有类别 action 都能安全拼入 fallback |

另新增 10 项测试方法，覆盖上一轮的 53/34 条合成语料、部分照抄、引文来源验证、未知团队局部分派、fallback action 过滤/回退自检，以及 v1.2 trace/context 版本字段。`tests/test_authoritative_contract.py` 已随测试专用提交一并纳入，因为 v1.2 测试导入其中的 runtime/policy helpers。

第三轮测试专用提交 `989a115` 增加 124 行、7 个测试方法；后续测试专用提交 `6e7a3a7` 再追加 19 行、1 个测试方法。两个测试提交之后都没有修改或删除任何测试。新增方法覆盖两条恢复的原样例、请求后照办、否定动作、重申权威值、不同对象动作、退款/银行过程时长、仍然属于回复时限的金融相关句子，以及配送/运输语境中的明确 SLA 标签。当前没有 `expectedFailure` 样例；本轮没有修改或删除的测试，因此无原句/新句替换项。

## 测试与工作树记录

- 本机完整发现：221 项通过，0 failures / 0 errors / 0 skipped（188 项既有测试 + 当前 33 项 v1.2 测试）。
- 干净 checkout（detached Git worktree）：117 项通过，0 failures / 0 errors / 0 skipped。其余 104 项来自本机存在、但未纳入分支的 9 个测试文件，因此干净 checkout 不会发现它们。
- 仍未提交的测试文件：
  - `tests/test_authoritative_contract_experiment.py`
  - `tests/test_authoritative_contract_pilot.py`
  - `tests/test_baseline_experiment.py`
  - `tests/test_builder_v2.py`
  - `tests/test_evaluation_parser_v2.py`
  - `tests/test_generative_provider.py`
  - `tests/test_provider_adapter_diagnostics.py`
  - `tests/test_responses_provider_adapter.py`
  - `tests/test_workflow_runtime.py`
- 本轮新增测试依赖 `tests/test_authoritative_contract.py` 已包含在 tests-only 提交；上述 9 个未跟踪文件未被本轮暂存或修改。

## 解释边界

这是 54 条既有 E2 输出上的开发集检查和有限合成测试，不是新的正式实验。只能描述冻结样例和合成语料上的规则行为；不能据此声称普遍安全、消除幻觉、优于其他模型，或对自然语言所有表达都能正确处理。

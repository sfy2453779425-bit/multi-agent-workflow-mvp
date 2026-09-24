# 开发集检查，不作为实验结果

本文件记录 v1.2 对冻结 E2 的离线开发集检查。它不是 E3 实验结果，不用于证明系统普遍有效，也没有调用模型/API。

## 范围与方法

- 输入：E2 的 54 条只读 `raw_model_text`，覆盖 6 个冻结 Case、3 个模型、每格 3 次。
- 候选解析：使用项目现有 `parse_candidate`；没有修改原始文件、Prompt、Fixture、Runtime v1.1 或旧 replay。
- 重放：由 `experiments/ac_e3/replay_candidates.py` 分别选择 v1.1 / v1.2，走同一冻结 Workflow、候选解析和回放路径。
- v1.1 回归：54/54 条的决定和最终消息均与 E2 已记录 replay 一致。
- 逐条检查：54 条原始回答均已查看；未读取 `experiments/ac_formal_v2_eval/`。

## 按模型的决定数

| 模型 | v1.1 ACCEPT | v1.1 REJECT | v1.2 ACCEPT | v1.2 REJECT |
|---|---:|---:|---:|---:|
| DeepSeek | 9 | 9 | 6 | 12 |
| GPT | 18 | 0 | 18 | 0 |
| Claude | 9 | 9 | 18 | 0 |
| 合计 | 36 | 18 | 42 | 12 |

## 与预期的核对

预期为 42 ACCEPT / 12 REJECT，实际为 **42 ACCEPT / 12 REJECT**，无不符条目。

- Claude 先前被 v1.1 拒绝的 9 条全部改为 ACCEPT：CS04 run 1–2、CS06 run 1–2、CS08 run 1–3、CS10 run 1–2。
- DeepSeek 的 12 条照抄全部为 REJECT，理由均为 `non_reply_echo`：CS01 run 1–2、CS04 run 1–3、CS08 run 1–3、CS10 run 1–3、CS12 run 1。
- 其余 33 条全部 ACCEPT。

## 决定变化

共 12 条决定发生变化：上述 9 条 Claude 从 REJECT 变为 ACCEPT；CS01 run 1–2 和 CS12 run 1 的 DeepSeek 从 v1.1 的 ACCEPT 变为 REJECT。其余 42 条决定不变。12 条 DeepSeek 照抄输出的规范化文本均与对应 `user_input` 相同，故 echo 相似度为 1.0。

## 产物

- v1.1 回放：`experiments/ac_e3/dev/e2_v1_1_replay.jsonl`
- v1.2 回放：`experiments/ac_e3/dev/e2_v1_2_replay.jsonl`
- 原始 E2 输入和既有记录均保持只读；本检查没有覆盖 E2 数据。

## 解释边界

这只是用于检查规则实现的 54 条开发数据。案例数量少且来自既有 Customer Support 冻结集；不能据此声称普遍安全、消除幻觉、优于其他模型或对未见语句具有相同表现。正式 E3 应使用独立定义的实验方案和结果分析。

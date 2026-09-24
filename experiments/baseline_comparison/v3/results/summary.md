# 三方比较实验 v3（Pilot）结果摘要

Experiment ID: `builder_v3_threeway_20260925`。10 个冻结 case，每个系统每个 case 3 次。
Builder 由本地规则程序执行，本轮 Builder 没有调用模型。历史 ChatGPT 数据单独标记为 ChatGPT-web-0916。

## A. 答案质量（原始计数）

字段为 `通过数/运行数`；支持域的 Ground Truth 指标只适用于 Customer Support。未做综合评分。

| 系统 | 领域 | 运行数 | 解析可用 | 必需字段齐全 | 使用上下文 | 满足约束 | 完整 | Ground Truth 正确 | 含 unsupported flag 的运行 | flag 总数 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-CLI | Customer Support | 15 | 15/15 | 15/15 | 12/15 | 15/15 | 15/15 | 15/15 | 0/15 | 0 |
| GPT-CLI | Outfit | 9 | 9/9 | 9/9 | 9/9 | 8/9 | 8/9 | 不适用 | 1/9 | 1 |
| GPT-CLI | Presentation | 6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 不适用 | 0/6 | 0 |
| Claude-CLI | Customer Support | 15 | 15/15 | 15/15 | 15/15 | 15/15 | 15/15 | 15/15 | 0/15 | 0 |
| Claude-CLI | Outfit | 9 | 9/9 | 9/9 | 9/9 | 8/9 | 8/9 | 不适用 | 1/9 | 1 |
| Claude-CLI | Presentation | 6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 不适用 | 0/6 | 0 |
| Builder | Customer Support | 15 | 15/15 | 15/15 | 15/15 | 15/15 | 15/15 | 15/15 | 0/15 | 0 |
| Builder | Outfit | 9 | 9/9 | 9/9 | 9/9 | 9/9 | 9/9 | 不适用 | 0/9 | 0 |
| Builder | Presentation | 6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 不适用 | 0/6 | 0 |
| ChatGPT-web-0916 | Customer Support | 15 | 15/15 | 15/15 | 15/15 | 15/15 | 15/15 | 15/15 | 0/15 | 0 |
| ChatGPT-web-0916 | Outfit | 9 | 9/9 | 2/9 | 9/9 | 9/9 | 2/9 | 不适用 | 0/9 | 0 |
| ChatGPT-web-0916 | Presentation | 6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 不适用 | 0/6 | 0 |

## B. 流程质量

重复性比较同一 case 三次运行的 evaluation-v2 结构化字段；不是逐字文本相同。能力项是是否提供对应流程工件，不把不提供记为 0。

| 系统 | 领域 | 结构化结果一致的 case | 执行记录 | 执行前校验 | 失败定位 |
|---|---|---:|---|---|---|
| GPT-CLI | Customer Support | 5/5 | 不提供 | 不提供 | 不提供 |
| GPT-CLI | Outfit | 1/3 | 不提供 | 不提供 | 不提供 |
| GPT-CLI | Presentation | 2/2 | 不提供 | 不提供 | 不提供 |
| Claude-CLI | Customer Support | 5/5 | 不提供 | 不提供 | 不提供 |
| Claude-CLI | Outfit | 1/3 | 不提供 | 不提供 | 不提供 |
| Claude-CLI | Presentation | 2/2 | 不提供 | 不提供 | 不提供 |
| Builder | Customer Support | 5/5 | 有 | 有 | 有 |
| Builder | Outfit | 3/3 | 有 | 有 | 有 |
| Builder | Presentation | 2/2 | 有 | 有 | 有 |
| ChatGPT-web-0916 | Customer Support | 5/5 | 不提供 | 不提供 | 不提供 |
| ChatGPT-web-0916 | Outfit | 0/3 | 不提供 | 不提供 | 不提供 |
| ChatGPT-web-0916 | Presentation | 2/2 | 不提供 | 不提供 | 不提供 |

## Builder 重跑与 9/16 结果

逐条比较 30 个 run：最终答案逐字一致 `30/30`；evaluation-v2 结构化评价一致 `30/30`。详细记录见 `builder_v2_comparison.csv`。

## 解析失败

空输出或评价器异常记录 `0` 条，详情见 `parse_failures.json`。字段缺失计入答案质量，不等同于解析器崩溃。

## C. 配置成本

本次不测，由后续的复用测试补充。

## 调用方式与限制

GPT 使用 Codex CLI 的 gpt-6-astra，采用 CLI 默认推理设置；Codex 默认系统指令仍生效，因此与 ChatGPT 网页版不完全相同。
Claude 使用 claude-opus-5-5 的 Claude Code CLI，空 system prompt、无工具、无设置源、无会话持久化；与 Claude 网页版不完全相同。
ChatGPT-web-0916 来自 9 月 16 日网页记录，模型显示为 GPT-5.6 Sol，调用参数和精确后端版本无法获知。
未进行 Human Evaluation，因此不评价自然度、实用性或用户偏好。结论限于这 10 个冻结 case 和本次调用方式。

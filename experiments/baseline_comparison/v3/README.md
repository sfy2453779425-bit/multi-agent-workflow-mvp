# 三方比较实验 v3

实验 ID：`builder_v3_threeway_20260925`。本目录复用 v2 的 10 个冻结 fixture 和 prompt，并用 evaluation-v2 评价 GPT-CLI、Claude-CLI、Builder；9 月 16 日的 ChatGPT 网页结果以 `ChatGPT-web-0916` 单独作为历史参照。

## 命令

在仓库根目录执行：

```powershell
python -B -m experiments.baseline_comparison.v3.experiment freeze --source-root 'D:\综合设计'
python -B -m experiments.baseline_comparison.v3.experiment verify
python -B -m experiments.baseline_comparison.v3.experiment run-builder
python -B -m experiments.baseline_comparison.v3.experiment collect-cli
python -B -m experiments.baseline_comparison.v3.experiment analyze
```

`freeze` 只执行一次；它会核对并复制 v2 输入、生成确定顺序的 90 行 schedule、保存 CLI 版本与当前 Builder 源码哈希。`collect-cli` 按 schedule 交错调用 GPT 和 Claude；每条调用都是新进程/新会话。已有完整调用会校验后跳过，不完整的输出不会被覆盖。重试仅限超时、网络错误、429 和 5xx，最多 3 次；内容问题不重试。任何 CLI 返回 401 都停止且不会尝试登录。

## 调用映射

- GPT：`codex exec --model gpt-6-astra`，每次用空临时工作目录、临时 `CODEX_HOME`、ephemeral 会话、只读 sandbox；shell tool 和 web search 关闭。推理强度沿用 Codex CLI 默认值，不传输出上限。Codex 默认系统指令保留，故与 ChatGPT 网页版不完全相同。
- Claude：`claude -p --model claude-opus-5-5 --output-format json`，stdin 为 frozen prompt 原始 UTF-8 字节；system prompt 为空、无工具、无设置源、无会话持久化，工作目录临时且为空。未设置输出上限。
- 两种 CLI 的最终模型文字原样保存在调用 JSON 中；完整 CLI stdout 原始字节另存 `.raw` 文件。usage 可提供时记录实际输出 token 数；CLI 未返回时留空，不估算。
- Builder：本地规则工作流执行，不调用 GPT、Claude 或其他模型。执行源码来自 manifest 标明的 source checkout，运行前后以文件哈希核对。
- evaluation-v2 解析器和指标保持不变。配置成本本轮不测，由后续的复用测试补充；不计算总分或赢家，也不做自然度/偏好判断。

## 输出

- `frozen/`：与 v2 对照的 fixture、prompt 和 hash 清单。
- `schedule.json`、`manifest.json`：调用计划及冻结信息。
- `raw/gpt/`、`raw/claude/`：原始 CLI stdout、每条调用元数据和 run log。
- `builder_runs/`：30 条当前 Builder 运行记录。
- `results/`：逐条 evaluation-v2、按系统/领域汇总、结构化重复性和 Builder-v2 对照。

历史 ChatGPT 原始记录和历史 Builder 记录仍只读地保存在 `../v2/`；分析结果单独写入本目录。

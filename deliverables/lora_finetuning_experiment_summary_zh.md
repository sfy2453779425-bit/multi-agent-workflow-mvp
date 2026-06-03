# LoRA 微调实验记录

## 目的

利用学校 A100 GPU 服务器，对 Qwen2.5 指令模型进行面向 Multi-Agent Workflow Builder 的 LoRA 微调，验证本地 LLM 是否可以作为下学期系统中的 Compose Node / Reasoning Node。

## 训练数据

- 数据文件: `data/workflow_builder_sft.jsonl`
- 样本数量: 80 examples
- 数据类型: 合成 SFT 数据
- 任务主题: Workflow Builder 解释、Harness Engineering 对比、Presentation Planning、Customer Support Routing、Local LLM Node 设计

## 训练配置

| Model | Epochs | LoRA r | LoRA alpha | dtype | Adapter Size | Avg Eval Speed |
|---|---:|---:|---:|---|---:|---:|
| Qwen2.5-1.5B-Instruct | 2.0 | 16 | 32 | bfloat16 | 70.5 MB | 45.08 token/s |
| Qwen2.5-7B-Instruct | 1.0 | 16 | 32 | bfloat16 | 154.1 MB | 44.39 token/s |

## 评估结果

### Qwen2.5-1.5B-Instruct

| Prompt | Latency(s) | Generated Tokens | token/s |
|---|---:|---:|---:|
| Explain our Template-based Multi-Agent Workflow Builder MVP in Chinese. | 1.744 | 65 | 37.273 |
| Answer why Harness Engineering alone is not enough for our project. | 4.495 | 220 | 48.942 |
| Design a Local LLM Compose Node for a workflow builder. | 4.487 | 220 | 49.031 |

### Qwen2.5-7B-Instruct

| Prompt | Latency(s) | Generated Tokens | token/s |
|---|---:|---:|---:|
| Explain our Template-based Multi-Agent Workflow Builder MVP in Chinese. | 2.884 | 112 | 38.83 |
| Answer why Harness Engineering alone is not enough for our project. | 1.611 | 76 | 47.179 |
| Design a Local LLM Compose Node for a workflow builder. | 4.665 | 220 | 47.157 |

## 关键观察

- Qwen2.5-1.5B 和 Qwen2.5-7B 都完成了 LoRA 微调，并生成了可下载的 adapter。
- 7B adapter 约 154 MB，适合保存和复用，不需要保存完整 7B 模型权重。
- 7B 评估速度约 38-47 token/s，可以作为本地 Compose / Reasoning Node 的原型。
- 中文回答在 Windows / 终端复制过程中出现编码乱码；英文输出正常。后续正式评估建议固定 UTF-8 环境，或者使用英文 prompt 作为稳定评估集。
- 当前训练集只有 80 条合成样本，因此本实验只能证明 LoRA 微调流程可行，不能宣称模型质量已经充分优化。

## 下学期使用方式

建议把 LoRA adapter 接入为可选 Local LLM Node：

```text
Workflow Engine
-> Structured Context
-> Local Qwen + LoRA Adapter
-> Compose / Reasoning Output
-> Trace + Metrics
```

第一阶段可以先接入 `Compose Node`，因为它风险最低，不会破坏现有确定性 Workflow。

## 不上传 GitHub 的内容

- `gpu_lora_outputs/` adapter 权重
- GPU 服务器连接信息
- 大模型缓存文件

这些内容只保存在本地或服务器。


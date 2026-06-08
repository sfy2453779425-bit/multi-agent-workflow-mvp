# GPU Base vs LoRA 对比实验指南

## 实验目的

这组实验用于补齐下学期技术性证据：

```text
验证本地 Qwen 模型和 LoRA 微调模型是否适合作为 Workflow Builder 的 Local LLM Node。
```

它不是主项目本身，也不是要证明本地模型超过 GPT。  
它的作用是给论文、展览和教授技术性评价提供可复现数据。

## 已准备内容

| 文件 | 用途 |
|---|---|
| `experiments/gpu_llm/eval_prompts.json` | 固定 8 个评估 Prompt |
| `experiments/gpu_llm/compare_base_lora.py` | 单个模型或 LoRA adapter 的评估脚本 |
| `experiments/gpu_llm/run_base_lora_comparison.sh` | 一键运行 1.5B base、1.5B LoRA、7B base、7B LoRA |
| `experiments/gpu_llm/aggregate_base_lora_results.py` | 汇总多个 JSON，生成 Markdown 总结 |
| `experiments/gpu_llm/download_comparison_outputs_from_server.cmd` | 从 GPU 服务器下载结果 |

## 服务器运行步骤

在本地 PowerShell 上传更新后的实验包后，登录 GPU 服务器：

```bash
ssh -p <SSH_PORT> <GPU_USER>@<GPU_SERVER_HOST>
```

进入实验目录：

```bash
cd ~/gpu_llm
source .venv/bin/activate
```

确认 adapter 存在：

```bash
ls lora_outputs
ls lora_outputs/Qwen_Qwen2.5-1.5B-Instruct_workflow_builder/final_adapter
ls lora_outputs/qwen25_7b_workflow_builder/final_adapter
```

运行完整对比：

```bash
bash run_base_lora_comparison.sh
```

输出位置：

```text
~/gpu_llm/results/base_lora_comparison/
```

关键文件：

```text
base_lora_summary.md
compare_*.json
compare_*.md
```

## 本地下载结果

在 Windows 本地双击：

```text
experiments/gpu_llm/download_comparison_outputs_from_server.cmd
```

下载后结果会放在：

```text
D:\综合设计\_local_artifacts\gpu_results\gpu_base_lora_results
```

## 评估 Prompt 覆盖范围

| 类别 | 目的 |
|---|---|
| workflow_generation | 是否能把用户输入拆成 Workflow Node |
| question_node | 是否能处理信息不足并追问 |
| recommendation | 是否能生成带优先级的推荐 |
| project_explanation | 是否能解释 Builder 与 Chatbot 差异 |
| professor_answer | 是否能回答 Harness Engineering 质疑 |
| multi_domain | 是否能迁移到客服/发表规划等非穿搭领域 |
| local_llm_node | 是否能说明 Local LLM Node 设计 |

## 可写进报告的指标

| 指标 | 含义 |
|---|---|
| Avg token/s | 推理速度 |
| Avg peak torch MB | 显存占用 |
| Avg keyword score | 是否覆盖预期 Workflow 关键词 |
| Prompt-level output | 具体回答质量证据 |

## 下学期使用方式

PPT 可以放一页：

```text
Local LLM Node Feasibility Test
```

建议表格：

| 模型 | LoRA | Avg token/s | Avg memory | Avg keyword score | 用途 |
|---|---|---:|---:|---:|---|
| Qwen2.5-1.5B | No | 待填 | 待填 | 待填 | 빠른 Demo |
| Qwen2.5-1.5B | Yes | 待填 | 待填 | 待填 | Workflow 용어 적응 |
| Qwen2.5-7B | No | 待填 | 待填 | 待填 | 고품질 답변 |
| Qwen2.5-7B | Yes | 待填 | 待填 | 待填 | Local LLM Node 후보 |

## 注意

- 不上传 adapter 权重到 GitHub。
- 不在 PPT 中暴露 GPU 密码。
- 不要声称已经完成商业级本地模型部署。
- 正确说法是：

```text
본 프로젝트는 Local Qwen 모델과 LoRA Adapter를 Workflow Node 후보로 평가했고,
속도, 메모리, Workflow 용어 적합성을 비교하는 실험 구조를 구축했다.
```

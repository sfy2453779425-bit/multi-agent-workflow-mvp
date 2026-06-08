# LoRA 第二轮实验计划

## 目标

第一轮实验已经证明：

```text
Base 模型稳定，LoRA 可以训练和接入，但小规模数据没有带来整体提升。
```

第二轮实验目标是：

```text
扩充 Workflow 专用 SFT 数据后，重新训练 1.5B LoRA，并比较 Base / Old LoRA / New LoRA。
```

## 新增内容

| 文件 | 作用 |
|---|---|
| `prepare_sft_dataset.py` | 已升级为 160 条默认 SFT 数据生成器 |
| `run_lora_training_v2.sh` | 训练新的 v2 LoRA，不覆盖旧 adapter |
| `run_v2_comparison.sh` | 比较 Base / Old LoRA / New LoRA |
| `download_v2_comparison_outputs_from_server.cmd` | 下载第二轮对比结果 |

## 数据覆盖

默认生成：

```text
160 条 SFT 样本
```

覆盖类别：

- project_identity
- professor_answer
- local_llm_node
- workflow_decomposition
- workflow_trace
- template_value
- korean_report
- question_node
- question_short_circuit
- recommendation_ranking
- recommendation_reasoning

## 服务器执行步骤

上传新包后，在 GPU 服务器执行：

```bash
cd ~/gpu_llm
source .venv/bin/activate
bash run_lora_training_v2.sh
```

默认训练：

```text
Qwen/Qwen2.5-1.5B-Instruct
```

输出：

```text
~/gpu_llm/lora_outputs/Qwen_Qwen2.5-1.5B-Instruct_workflow_builder_v2/final_adapter
```

训练完成后执行：

```bash
bash run_v2_comparison.sh
```

结果：

```text
~/gpu_llm/results/v2_lora_comparison/v2_lora_summary.md
```

## 本地下载

双击：

```text
experiments/gpu_llm/download_v2_comparison_outputs_from_server.cmd
```

下载到：

```text
D:\综合设计\_local_artifacts\gpu_results\gpu_v2_lora_results
```

## 判断标准

如果 New LoRA 的 `avg_keyword_score` 高于 Base 或 Old LoRA，可以说明：

```text
扩充 Workflow 专用数据后，LoRA 对结构化 Workflow 术语和节点输出有改善。
```

如果 New LoRA 仍未提升，应如实说明：

```text
LoRA 接入和训练流程可行，但当前数据规模和训练方式仍不足，需要更高质量人工标注数据。
```

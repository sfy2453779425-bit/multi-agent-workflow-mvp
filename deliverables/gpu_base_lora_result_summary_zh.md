# GPU Base vs LoRA 对比实验结果总结

## 实验目的

本实验用于验证：

```text
本地 Qwen 模型是否可以作为 Template-based Multi-Agent Workflow Builder 的 Local LLM Node 候选。
```

实验重点不是证明本地模型超过 GPT，也不是证明 LoRA 一定更好，而是形成下学期可用于技术性评价、论文和展览的可复现实验数据。

## 实验设置

- GPU：A100 80GB
- Prompt 数量：8
- Prompt 类型：
  - Workflow Node 分解
  - Question Node 信息补全
  - 穿搭推荐排序
  - Builder vs Chatbot 说明
  - Harness Engineering 质疑回答
  - 客服 Workflow
  - 发表规划 Workflow
  - Local LLM Node 设计

原始结果目录：

```text
D:\综合设计\_local_artifacts\gpu_results\gpu_base_lora_results
```

核心汇总文件：

```text
D:\综合设计\_local_artifacts\gpu_results\gpu_base_lora_results\base_lora_summary.md
```

## 总体结果

| 模型 | LoRA | Load(s) | Avg latency(s) | Avg token/s | Avg peak MB | Avg keyword score |
|---|---|---:|---:|---:|---:|---:|
| Qwen2.5-1.5B-Instruct | No | 1.533 | 2.232 | 99.018 | 2964.4 | 0.667 |
| Qwen2.5-1.5B-Instruct | Yes | 1.905 | 2.968 | 48.437 | 3040.8 | 0.658 |
| Qwen2.5-7B-Instruct | No | 3.167 | 3.963 | 65.642 | 14557.2 | 0.638 |
| Qwen2.5-7B-Instruct | Yes | 3.455 | 4.564 | 46.654 | 14787.8 | 0.596 |

## 主要发现

### 1. Base 模型已经足够支撑 Local LLM Node Demo

Qwen2.5-1.5B base 的平均速度最高：

```text
99.018 token/s
```

显存占用也最低：

```text
约 2.96GB
```

因此，若下学期需要稳定演示 Local LLM Node，推荐优先使用：

```text
Qwen2.5-1.5B-Instruct base
```

它适合：

- 快速 Demo
- 低显存部署
- Workflow Node 的简单解释和 Compose

### 2. 7B base 更适合高质量候选，但成本更高

Qwen2.5-7B base 平均速度：

```text
65.642 token/s
```

显存占用：

```text
约 14.56GB
```

它比 1.5B 更重，但仍然可以在 A100 上稳定运行。  
下学期如果要展示“更强的本地模型能力”，可以把 7B base 作为高质量候选。

### 3. 当前 LoRA 没有整体超过 Base

这次 LoRA 的平均关键词分数没有超过对应 base：

| 对比 | Base keyword score | LoRA keyword score | 结论 |
|---|---:|---:|---|
| 1.5B | 0.667 | 0.658 | 基本接近，但未提升 |
| 7B | 0.638 | 0.596 | 下降 |

同时 LoRA 推理速度也明显下降：

| 对比 | Base token/s | LoRA token/s |
|---|---:|---:|
| 1.5B | 99.018 | 48.437 |
| 7B | 65.642 | 46.654 |

因此不能在发表中说：

```text
LoRA 微调显著提升了模型效果。
```

更准确的说法是：

```text
本实验验证了 LoRA Adapter 可以被接入并运行，但当前小规模训练数据还不足以稳定提升整体效果。
```

### 4. LoRA 在部分 Workflow 术语任务上有局部改善

虽然整体没有超过 Base，但 1.5B LoRA 在部分 Prompt 上表现更贴近 Workflow 术语：

| Prompt | 1.5B Base | 1.5B LoRA |
|---|---:|---:|
| workflow_node_decomposition_outfit | 0.667 | 1.000 |
| builder_vs_chatbot_explanation | 0.800 | 1.000 |
| customer_support_workflow | 1.000 | 1.000 |

这说明 LoRA 的方向不是完全无效，而是训练数据和评估集还需要扩充。

## PPT 可用结论

### 中文

```text
我们在 A100 GPU 上测试了 Qwen2.5-1.5B/7B 的 Base 模型与 LoRA Adapter。
结果显示，Base 模型已经可以稳定作为 Workflow Builder 的 Local LLM Node 候选；
LoRA Adapter 虽然可以成功接入并运行，但当前小规模训练数据尚未带来整体性能提升。
因此，下学期将优先采用 Base 模型作为稳定 Demo，并继续扩充 Workflow 专用数据集来改进 LoRA。
```

### KR

```text
A100 GPU 환경에서 Qwen2.5-1.5B/7B Base 모델과 LoRA Adapter를 비교 평가했습니다.
실험 결과 Base 모델은 Workflow Builder의 Local LLM Node 후보로 안정적으로 동작했으며,
LoRA Adapter도 실행 가능함을 확인했습니다.
다만 현재 소규모 학습 데이터만으로는 전체 성능 향상이 확인되지 않았기 때문에,
다음 학기에는 Base 모델을 안정적인 Demo 후보로 사용하고,
Workflow 전용 학습 데이터를 확장하여 LoRA 개선을 진행할 계획입니다.
```

## 下学期建议

### 推荐技术路线

| 用途 | 推荐模型 |
|---|---|
| 现场稳定 Demo | Qwen2.5-1.5B base |
| 高质量回答实验 | Qwen2.5-7B base |
| 论文实验扩展 | Base vs LoRA 持续对比 |
| 后续微调研究 | 扩充数据后的 LoRA |

### 不建议现在做

- 不建议把 LoRA 作为主展示成果。
- 不建议声称本地模型已经优于云端 LLM。
- 不建议继续盲目增加 epoch。
- 不建议在没有更多数据的情况下继续训练更大模型。

### 建议下一步补充

1. 扩充 SFT 数据到至少 100-300 条。
2. 把训练数据分成：
   - Workflow 分解
   - Question Node 追问
   - Recommendation Ranking
   - Harness 质疑回答
   - 多领域模板迁移
3. 增加人工评分，不只看 keyword score。
4. 把 Local LLM Node 接入前端或后端 Workflow Demo。

## 可用于报告的一句话

```text
본 실험은 Local Qwen 모델이 Template-based Multi-Agent Workflow Builder의 LLM Node로 사용 가능함을 확인했으며, LoRA Adapter는 실행 가능하지만 현재 데이터 규모에서는 추가 개선이 필요함을 보여준다.
```

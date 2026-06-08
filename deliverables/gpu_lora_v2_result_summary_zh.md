# LoRA 第二轮实验结果总结

## 实验目的

第一轮 LoRA 实验显示：

```text
LoRA Adapter 可以训练、加载和推理，但小规模数据没有带来整体效果提升。
```

因此第二轮实验扩充了 Workflow 专用 SFT 数据，并重新训练：

```text
Qwen2.5-1.5B-Instruct LoRA v2
```

目标是验证：

```text
扩充领域数据后，LoRA 是否能更好适配 Workflow Builder 相关输出。
```

## 实验设置

- Base model: `Qwen/Qwen2.5-1.5B-Instruct`
- Old LoRA: 第一轮小规模数据训练结果
- New LoRA v2: 第二轮 160 条 Workflow 专用 SFT 数据训练结果
- Evaluation prompts: 固定 8 条 Workflow Builder Prompt
- GPU: A100 80GB

本地结果目录：

```text
D:\综合设计\_local_artifacts\gpu_results\gpu_v2_lora_results
```

核心结果文件：

```text
D:\综合设计\_local_artifacts\gpu_results\gpu_v2_lora_results\v2_lora_summary.md
```

## 总体结果

| 模型 | Load(s) | Avg latency(s) | Avg token/s | Avg peak MB | Avg keyword score |
|---|---:|---:|---:|---:|---:|
| Qwen2.5-1.5B Base | 1.705 | 2.160 | 100.298 | 2964.4 | 0.667 |
| Old LoRA | 2.192 | 2.933 | 48.995 | 3040.8 | 0.658 |
| New LoRA v2 | 2.097 | 2.547 | 48.952 | 3040.8 | 0.733 |

## 核心结论

### 1. New LoRA v2 在关键词覆盖上超过 Base 和 Old LoRA

第二轮结果：

```text
Base:      0.667
Old LoRA:  0.658
New LoRA:  0.733
```

说明扩充 Workflow 专用 SFT 数据后，LoRA 对项目相关术语和结构化回答的适配有所改善。

### 2. New LoRA v2 在多个关键 Prompt 上提升明显

| Prompt | Base | Old LoRA | New LoRA v2 | 变化 |
|---|---:|---:|---:|---|
| workflow_node_decomposition_outfit | 0.667 | 1.000 | 1.000 | 保持高分 |
| builder_vs_chatbot_explanation | 0.800 | 1.000 | 1.000 | 保持高分 |
| customer_support_workflow | 1.000 | 1.000 | 1.000 | 保持高分 |
| presentation_planning_workflow | 0.600 | 0.600 | 0.800 | 提升 |
| local_llm_node_design | 0.600 | 0.200 | 0.800 | 明显提升 |

其中 `local_llm_node_design` 从 Old LoRA 的 `0.200` 提升到 `0.800`，说明 v2 数据对 Local LLM Node 相关说明更有效。

### 3. Question Node 和 Harness 답변 仍需改进

New LoRA v2 仍有两个弱点：

| Prompt | New LoRA v2 |
|---|---:|
| missing_information_question_node | 0.200 |
| harness_limitation_answer | 0.400 |

说明下一轮数据应继续补强：

- 정보 부족 시 질문 순서
- 도시/날짜/목적/스타일 필드 명시
- Harness Engineering 与 Template Builder 的差异说明

### 4. LoRA v2 提升了结构适配，但速度仍低于 Base

速度对比：

```text
Base:        100.298 token/s
Old LoRA:     48.995 token/s
New LoRA v2:  48.952 token/s
```

因此下学期展示时应分清用途：

| 用途 | 推荐 |
|---|---|
| 现场稳定快速 Demo | Qwen2.5-1.5B Base |
| 展示领域适配实验 | New LoRA v2 |
| 论文/报告实验表 | Base vs Old LoRA vs New LoRA v2 |

## PPT 可用结论

### 中文

```text
第二轮实验将 SFT 数据扩充到 160 条 Workflow 专用样本后，Qwen2.5-1.5B LoRA v2 的平均 keyword score 从旧 LoRA 的 0.658 提升到 0.733，并超过 Base 模型的 0.667。
这说明领域数据扩充可以改善本地 LLM 对 Workflow Builder 术语和结构化输出的适配。
但 LoRA 推理速度约 49 token/s，低于 Base 的约 100 token/s，因此现场 Demo 仍建议优先使用 Base，LoRA v2 作为技术性实验成果展示。
```

### Korean

```text
2차 실험에서는 Workflow 전용 SFT 데이터를 160개로 확장한 뒤 Qwen2.5-1.5B LoRA v2를 다시 학습했습니다.
그 결과 평균 keyword score가 기존 LoRA의 0.658에서 0.733으로 향상되었고, Base 모델의 0.667도 넘어섰습니다.
이는 도메인 특화 데이터 확장이 Workflow Builder 용어와 구조화 출력 적응에 효과가 있음을 보여줍니다.
다만 LoRA 추론 속도는 약 49 token/s로 Base의 약 100 token/s보다 낮기 때문에, 실시간 Demo는 Base 모델을 우선 사용하고 LoRA v2는 기술 검증 결과로 제시하는 것이 적절합니다.
```

## 下学期建议

1. Demo 用 `Qwen2.5-1.5B Base`，保证速度和稳定性。
2. 技术性评价/论文中展示 `Base vs Old LoRA vs New LoRA v2`。
3. 下一轮数据重点补强：
   - Question Node 信息补全
   - Harness Engineering 质疑回答
   - 多语言关键词一致性
4. 不要声称 LoRA 全面优于 Base，只能说：

```text
LoRA v2 在 Workflow 相关关键词覆盖上超过 Base，但推理速度仍低于 Base。
```

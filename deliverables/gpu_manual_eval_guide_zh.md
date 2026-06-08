# GPU 输出人工评分指南

## 目的

目前已有自动指标：

```text
keyword score
token/s
latency
GPU memory
```

但 keyword score 只能判断关键词是否出现，不能判断回答是否真的有用。  
因此需要补充人工评分。

## 已生成文件

运行脚本后会生成：

```text
outputs/manual_eval_v2/manual_eval_blind.csv
outputs/manual_eval_v2/manual_eval_mapping.csv
outputs/manual_eval_v2/manual_eval_rubric.md
outputs/manual_eval_v2/manual_eval_result_template.md
outputs/manual_eval_v2/manual_eval_reviewer_1.csv
outputs/manual_eval_v2/manual_eval_reviewer_2.csv
outputs/manual_eval_v2/manual_eval_reviewer_3.csv
```

## 怎么评分

先打开：

```text
outputs/manual_eval_v2/manual_eval_rubric.md
```

然后只使用：

```text
outputs/manual_eval_v2/manual_eval_blind.csv
```

评分时不要看 `manual_eval_mapping.csv`，否则会知道答案来自哪个模型，评价容易偏。

## 评分维度

每项 1-5 分：

| 维度 | 含义 |
|---|---|
| Structure | 是否按要求输出节点、排名、bullet、输入/输出结构 |
| Domain Fit | 是否正确使用 Workflow Builder / Template / Node / Trace 概念 |
| Usefulness | 是否能直接用于报告、发表、系统设计 |
| Traceability | 是否能说明执行步骤、数据来源或推理依据 |
| Language Quality | 韩语/中文/英文表达是否自然 |
| Overall | 综合质量 |

## 推荐流程

1. 找 2-3 名组员分别评分。
2. 每人独立填写 `manual_eval_blind.csv`。
3. 评分结束后，再打开 `manual_eval_mapping.csv`。
4. 按模型分组计算平均分。
5. 把结果填入：

```text
outputs/manual_eval_v2/manual_eval_result_template.md
```

## 自动汇总

如果只有一个评分者，评分完成后可以直接运行：

```powershell
python experiments\gpu_llm\summarize_manual_eval.py --scores outputs\manual_eval_v2\manual_eval_reviewer_1.csv --mapping outputs\manual_eval_v2\manual_eval_mapping.csv --output outputs\manual_eval_v2\manual_eval_summary.md
```

如果有 2-3 个评分者，先把多个 CSV 合并成一个总 CSV，再运行同一个命令。  
合并时保留表头一次即可。

## PPT 可用说法

```text
자동 keyword score 외에도 수동 평가를 추가하여 구조성, 도메인 적합성, 활용 가능성, Trace 설명력, 언어 품질을 비교했다.
```

中文解释：

```text
除了自动 keyword score，我们还增加人工评分，从结构完整性、领域适配性、实用性、Trace 可解释性和语言质量五个维度比较 Base、旧 LoRA 和新 LoRA v2。
```

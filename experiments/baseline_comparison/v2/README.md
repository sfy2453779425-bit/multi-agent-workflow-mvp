# Builder v2 Pilot

本目录是 `builder_v2_pilot_20260916` 的独立实验目录。它包含 10 个冻结 Case、每个 Case 3 次 Builder 运行，以及只保留 ChatGPT 的外部基线入口。

## 已生成内容

- `prompts/chatgpt/`：10 份最终 Prompt。每份文件内容已经固定，运行时不要改字。
- `builder_runs/`：30 次 Builder 原始运行记录。
- `results/builder_v2/`：按 Case 汇总的 Builder 结果。
- `results/case_quality.csv`：客观字段、约束、冻结数据和不支持事实检查。
- `results/workflow_reuse.csv`、`results/workflow_reuse_details.json`：Travel Outfit 到 Commute Outfit 的两种构建方式记录。
- `results/validation_results.csv`、`results/trace_summary.csv`：验证、执行和 Trace 顺序。
- `results/human_evaluation_template.csv`：空白模板，本轮没有收集人工评分。

## 手动做 ChatGPT 实验

1. 打开 `prompts/chatgpt/` 下的一个 Prompt，完整复制到 ChatGPT。
2. 每个 Case 运行 3 次。不要修改 Prompt、冻结数据或 Case 顺序。
3. 把 ChatGPT 原文完整保存到 JSON 的 `response` 字段。不要清洗、改写或用评分结果覆盖原文。
4. `model_name` 填产品界面实际显示的模型名；无法确认的参数照实写：

```text
sampling_parameters = unavailable
exact_backend_revision = unavailable
```

5. 使用该 Case 对应的 `prompt_file` 和 `prompt_sha256`，其值从 `manifest.json` 读取。例如：

```json
{
  "experiment_id": "builder_v2_pilot_20260916",
  "case_id": "outfit_01",
  "fixture_version": "from manifest.json",
  "prompt_version": "prompt-v1",
  "run": 1,
  "provider": "ChatGPT",
  "model_name": "name shown by ChatGPT",
  "sampling_parameters": "unavailable",
  "exact_backend_revision": "unavailable",
  "timestamp": "2026-09-16T12:00:00+09:00",
  "prompt_file": "prompts/chatgpt/outfit_01.md",
  "prompt_sha256": "from manifest.json",
  "response": "paste the unchanged ChatGPT response here",
  "run_id": "chatgpt_outfit_01_1"
}
```

6. 导入单个原文记录：

```powershell
python experiments\baseline_comparison\runner.py --root experiments\baseline_comparison\v2 import-llm --file C:\path\to\record.json
```

7. 全部导入后重新评价：

```powershell
python experiments\baseline_comparison\v2_runner.py analyze --root experiments\baseline_comparison\v2
```

导入器会检查实验 ID、Case、版本、Prompt 哈希、运行编号、元数据和时间戳。原文会以 immutable JSON 保存在 `llm_runs/chatgpt/`，解析结果和评价结果分别保存在 `results/parsed/` 与 `results/evaluation/`。

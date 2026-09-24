# Baseline Comparison Pilot

This folder contains the three-case `Pilot Experiment` for ChatGPT, Claude,
and the local Template-based Builder. It measures Answer Quality and Workflow
Engineering separately. It does not contact an external model and does not
produce a combined ranking.

## Run the local baseline

From `D:\综合设计`:

```powershell
python experiments\harness_comparison.py
```

The command freezes the fixture and Prompt hashes, runs the Builder three
times for each Case, runs the controlled weather failure, and writes the
reports under `experiments\baseline_comparison\results\`.

Cases:

- `outfit_01`: Qingdao travel/casual outfit recommendation
- `presentation_01`: 15-minute presentation outline
- `customer_support_01`: late-delivery/refund ticket routing

## Collect real ChatGPT and Claude data manually

1. Run `python experiments\harness_comparison.py prepare`.
2. Open the six files under `prompts\chatgpt\` and `prompts\claude\`.
3. For each Case, paste the same Prompt into ChatGPT three times and Claude
   three times. Do not change the Prompt or fixture during this experiment.
4. Save each real response as a JSON file. Use the manifest's
   `experiment_id`, the matching `fixture_version`, `prompt_version`, and
   `prompt_sha256`. Record the model name shown by the product UI.
5. If the UI does not expose sampling settings or an exact backend revision,
   write exactly `unavailable`; do not guess.
6. Use a provider-matching `prompt_file`, for example
   `prompts/chatgpt/outfit_01.md`, and keep the response text unchanged.
7. Import one file at a time:

```powershell
python experiments\harness_comparison.py import-llm --file C:\path\to\record.json
```

Accepted bytes are copied unchanged into `llm_runs\chatgpt\` or
`llm_runs\claude\`. Parsing and evaluation are written separately under
`results\parsed\` and `results\evaluation\`.

8. Regenerate the comparison:

```powershell
python experiments\harness_comparison.py analyze
```

The importer rejects missing metadata, empty responses, wrong Prompt hashes,
wrong experiment versions, duplicate runs, and malformed timestamps. An
`EXAMPLE_ONLY` record is retained as non-formal input and excluded from the
results.

## Required record shape

```json
{
  "experiment_id": "from manifest",
  "case_id": "outfit_01",
  "fixture_version": "from manifest",
  "prompt_version": "prompt-v1",
  "run": 1,
  "provider": "ChatGPT",
  "model_name": "name shown by the UI",
  "sampling_parameters": "unavailable",
  "exact_backend_revision": "unavailable",
  "timestamp": "2026-09-16T12:00:00+09:00",
  "prompt_file": "prompts/chatgpt/outfit_01.md",
  "prompt_sha256": "from manifest",
  "response": "paste the real response without rewriting it",
  "run_id": "chatgpt_outfit_01_1"
}
```

## Result files

- `manifest.json`: frozen experiment metadata at the package root
- `results/experiment_manifest.json`: report copy of the manifest
- `builder_runs/`: nine normal Builder records
- `failure_runs/` and `results/failure_localization.json`: controlled failure evidence
- `llm_runs/`: immutable imported external records
- `results/parsed/`: parsed structured fields
- `results/evaluation/`: objective evaluation artifacts
- `results/answer_quality.csv`: objective checks plus pending rows
- `results/workflow_features.csv`: separate engineering dimensions
- `results/repeatability.csv`: structured-field agreement across runs
- `results/configuration_comparison.csv`: defined touch-point and reuse counts
- `results/human_evaluation_template.csv`: blank blind human-rating form
- `results/summary.md`: current pilot report and missing-data status

The `17 -> 3` value is only a count of defined configuration touch points in
`evaluation/criteria.json`. It is not a measured time or efficiency claim.

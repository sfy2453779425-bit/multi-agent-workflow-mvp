# ChatGPT vs Claude vs Builder — Pilot Experiment

## Scope

This is a Pilot Experiment with three frozen Cases, three systems, and three planned runs per Case.
The purpose is to validate the comparison method, support the next presentation, and identify the Builder's real strengths and limits.
Experiment ID: `baseline_pilot_20260916_010827`
Fixture versions and Prompt hashes are frozen in `results/experiment_manifest.json`.

## Answer Quality

Automated checks cover required fields, explicit constraints, frozen data usage, unsupported inventory references, and policy-derived decisions where objective facts are available.
Language quality, usefulness, clarity, and naturalness remain for Human Evaluation.
Builder records available: 9/9.
Formal external LLM records available: 0/18.

## Workflow Engineering

The report keeps validation, structured execution, node-level trace, repeatability, failure localization, and configuration/reuse as separate dimensions.
Across the tested cases, the Builder records preserve executable workflow structure and trace evidence; this does not establish a general model-quality claim.

## Configuration / Reuse

The configuration comparison reports 17 -> 3 defined touch points from the explicit action lists in `evaluation/criteria.json`.
The reuse row reports changed visible fields from the Travel Outfit to Commute Outfit procedure. No time or efficiency percentage is inferred.

## Repeatability

Repeatability compares parsed structured fields across the three runs. It does not require identical wording.

## Failure Localization

The controlled run failed at `weather` with `weather service unavailable`.
Expected downstream behavior was recorded in the trace and the failure run is excluded from Answer Quality.

## Human Evaluation

`human_evaluation_template.csv` is blank and uses blind Response A/B/C labels with 0–4 fields for usefulness, clarity, naturalness, and overall task quality.

## External Baseline Status

LLM baseline results pending real runs
Missing formal records: 18 (9 ChatGPT, 9 Claude).
No sample or example response is used as a result.

## Limitations

Sampling parameters and exact backend revisions are unavailable when the product UI does not expose them; they are recorded as unavailable rather than guessed.
The three Cases are a pilot and support conclusions only about the tested cases.
Unfavorable results remain in the metric-specific files. No winner is calculated from a combined rank.

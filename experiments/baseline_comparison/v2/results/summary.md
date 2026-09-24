# Builder v2 — Pilot Experiment

## Scope

Experiment ID: `builder_v2_pilot_20260916`
Builder version: `builder-v2`
Cases: 10 frozen cases (Customer Support 5, Outfit 3, Presentation 2); 3 runs per case.
This is a Pilot Experiment for validating the comparison method, checking the next presentation, and locating the Builder's real strengths and limits.
Only ChatGPT is retained as the external baseline in this version. No composite ranking or winner is calculated.

## Outfit v2 and Regression

The recommendation now includes frozen precipitation, uses rain_ok at the configured precipitation threshold, and emits inventory-only selected items.
Comparable original cases with a quality regression: 0.

## Workflow Reuse

Task A is Travel Outfit and Task B is Commute Outfit. The manual condition starts from Task A Workflow JSON and applies recorded edit paths; the Builder condition selects the Commute template and generates its JSON.
Both conditions passed validation, execution, required-field checks, constraint checks and trace-order checks: True.
The calculation reports changed, added and removed fields plus reused, modified, replaced and new nodes. It records engineering operation facts only; it does not infer time or efficiency.

## Case Quality

Builder quality checks passed for 30/30 Builder runs.
Validation rows: 30; trace rows: 30.
Customer Support objective checks derive from frozen policy data. Outfit and Presentation automated checks cover only objective fixture facts and explicit constraints.

## Repeatability

Builder repeatability rows available: 10/10; parsed structured fields are compared across the three runs.

## External Baseline Status

Formal ChatGPT records available: 30/30.
The prompts are frozen under the experiment root. Product-interface sampling parameters and exact backend revision remain recorded as unavailable when they cannot be confirmed.

## Human Evaluation

Human evaluation was designed but not conducted and is excluded from the
final evaluation scope. No human ratings or virtual-agent ratings are used.

## Limitations

The ten cases and three repetitions are a pilot, so conclusions are limited to the tested cases.
The final reported dimensions are Direct Task Results, Workflow Engineering,
Configuration / Reuse, Repeatability, and Failure Localization. No Human
Evaluation dimension is reported.
Unfavorable results remain in the case-level artifacts; no overall score is produced.

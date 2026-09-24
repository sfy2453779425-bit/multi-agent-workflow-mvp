# Evaluation v2 — Builder v2 Pilot

## A. Parser defect root cause

The previous Outfit parser treated every known inventory ID mentioned in the response as selected. It did not distinguish recommendation, exclusion, and ordinary inventory mention.

## B. Evaluation v2 implementation

Experiment ID: `builder_v2_pilot_20260916`
Evaluation version: `evaluation-v2`
The parser now records `selected_items`, `excluded_items`, `mentioned_items`, `mentioned_only_items`, `ambiguous_items`, and `parse_status`.
Evaluation v1 remains frozen under `results/evaluation_v1/`; v2 outputs are under `results/evaluation_v2/`.

## C. Raw response impact

ChatGPT records reanalyzed: 30/30.
Change-log rows changed: 6/30.
Raw response files, Prompts, Fixtures, Builder v2, Templates, Runtime, and policy Ground Truth were not modified.

## D. Outfit audit

All 9 ChatGPT Outfit records are in `outfit_parser_audit.csv`. The audit preserves recommendation order separately from excluded and mention-only items.

## E. ChatGPT summary

Required fields: 23/30.
Constraint satisfaction: 30/30.
Completeness: 23/30.
Repeatability is reported per Case in `repeatability.csv`; it is not combined with Answer Quality.

## F. Builder summary

Frozen Builder rows reread: 30.
Required fields: 30/30.
Constraint satisfaction: 30/30.
Completeness: 30/30.
Builder rows and repeatability values were copied from evaluation-v1; no Builder execution was performed.

## G. Evaluation v1 versus v2

The machine-readable comparison is `evaluation_change_log.csv`.
The change log includes selected/excluded items, constraint satisfaction, completeness, and repeatability contribution for every ChatGPT run.

## H. Tests

Parser tests cover explicit recommendation, explicit exclusion, negative recommendation, mixed selected/excluded text, and ordinary inventory mention.

## I. Supported conclusions

Evaluation v2 more accurately reflects explicit Outfit recommendation and exclusion semantics in this pilot. Customer Support and Presentation objective checks remain separately reported.

## J. Unsupported conclusions

This pilot does not establish general model superiority, an overall winner,
language-quality superiority, or user-efficiency percentages. Human
evaluation was not conducted and is excluded from the final evaluation scope.

# Final Experiment Numbers

Experiment ID: `builder_v2_pilot_20260916`

Builder version: `builder-v2`

Evaluation version: `evaluation-v2`

Human Evaluation: `NOT_CONDUCTED`; excluded from the final quantitative evaluation.

Speed evaluation: `NOT_CONDUCTED`.

## Direct Task Results

These are passing-run counts, not an overall score.

| Metric | ChatGPT | Builder |
|---|---:|---:|
| Required fields | 23/30 | 30/30 |
| Constraint satisfaction | 30/30 | 30/30 |
| Completeness | 23/30 | 30/30 |
| Structured repeatability | 7/10 cases | 10/10 cases |

Constraint satisfaction is equal in this pilot. The observed difference is
that direct ChatGPT generation did not always preserve the predefined output
contract, while the Builder enforced the required structure through Templates
and Workflow execution.

## Structured Repeatability by Domain

Repeatability means that the evaluated structured fields match across the
three runs. It does not mean exact-text equality.

| Domain | ChatGPT | Builder |
|---|---:|---:|
| Customer Support | 5/5 | 5/5 |
| Presentation | 2/2 | 2/2 |
| Outfit | 0/3 | 3/3 |
| Overall | 7/10 | 10/10 |

The ChatGPT result is task-dependent: Customer Support and Presentation were
stable in the tested cases, while Outfit showed variation in structured item
selection or ordering.

## Experiment Scale

- 10 distinct frozen cases
- 3 domains: Customer Support, Outfit, Presentation
- 3 runs per case and system
- Builder: 30 runs
- ChatGPT: 30 runs
- ChatGPT sampling parameters and exact backend revision: unavailable

## Workflow Engineering Evidence

The Builder evidence is reported separately from Direct Task Result scores:

- Workflow JSON
- Workflow validation
- execution order
- input/output binding
- Node Trace
- failure localization

Controlled failure trace:

```text
request_parser       SUCCESS
question             SUCCESS
weather              FAILED
shopping_analysis    SKIPPED
recommendation       SKIPPED
compose              SKIPPED
```

Failure: `weather service unavailable`.

Direct ChatGPT interaction did not expose an equivalent workflow-level
execution trace in this experiment. This is not scored as `ChatGPT Trace = 0`.

## Template Configuration Abstraction

### Manual JSON Editing

- Task A leaf fields: 161
- Task B leaf fields: 159
- changed leaf values: 46
- removed fields: 2
- modified nodes: 6
- bindings affected: 0
- observed user-visible actions: 3
- Validation: PASS
- Execution: PASS
- Repair count: 0
- Runtime modified: False

### Template Builder

- exposed task-level inputs: 3
- template-generated fields: 157
- reused nodes: 6
- input bindings: 12
- output bindings: 43
- required-input declarations: 12
- execution-order entries: 6
- Validation: PASS
- Execution: PASS
- Repair count: 0
- Runtime modified: False

The supported conclusion is:

> The Template Builder reduces the amount of workflow contract that the user
> must directly manage by exposing task-level inputs and generating the
> remaining workflow structure.

No click-reduction, time, speed, or efficiency percentage is inferred.

## Methodology Record

The `evaluation-v1` to `evaluation-v2` parser correction is retained as
methodology evidence. The raw 30 ChatGPT responses were preserved and
reanalyzed; no response was regenerated.

## Tests

Final verification: `94 tests passed`.

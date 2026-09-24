# Workflow Reuse Quantitative Explanation

## 1. Scope

This report answers one narrow question:

> Compared with directly editing an existing Workflow JSON, what does the Template Builder provide automatically when creating the second workflow?

It uses the real Task A and Task B template outputs in the frozen `builder_v2_pilot_20260916` experiment. It does not measure elapsed time, UI latency, typing effort, or human productivity.

Source templates:

- Task A / travel outfit workflow: `configs/builder_templates/outfit_recommendation_template.json`
- Task B / commute outfit workflow: `configs/builder_templates/commute_outfit_template.json`

Canonical generated workflow hashes:

- Task A: `dc9297004ec61532955802271c8dee26914fddf20fa85cbfda8e48c7c92671f1`
- Task B: `7b3dccfb3657b0176c070a07cd40504111ff196a05e37b53f3668dca3e385d02`

The machine-readable values are in `workflow_reuse_quantitative.csv`.

## 2. Counting rules

### Field-level comparison

“Field” means a scalar leaf value in the canonical JSON. Array elements use indexed paths. Empty objects and arrays do not add a leaf field. This makes the comparison reproducible and avoids treating a whole nested object as one field.

Under this rule:

| Workflow | Total leaf fields |
|---|---:|
| Task A | 161 |
| Task B | 159 |

### Manual condition

The Manual condition is intentionally conservative. The user may start from the existing Task A JSON, copy it, and modify it for Task B. The report counts the actual JSON difference; it does not pretend that the user must retype the entire workflow.

The separate `manual_observed_actions` count records the three logical configuration actions defined for this task:

1. Select the `preset`.
2. Set the `workflow_name`.
3. Set the `query`.

Copying, search/replace, batch editing, schema validation, and correction are allowed as part of the Manual workflow. They are not converted into a made-up number of clicks or minutes.

## 3. Semantic configuration differences

### Manual condition: actual modification amount

The Task A → Task B diff contains:

| Measure | Count | Meaning |
|---|---:|---|
| Task A total leaf fields | 161 | Source workflow size under the counting rule |
| Task B total leaf fields | 159 | Target workflow size under the counting rule |
| Changed fields | 46 | Existing paths whose scalar value changed |
| Added fields | 0 | Paths present only in Task B |
| Removed fields | 2 | `question_agent.purpose_keywords[10]` and `[9]` |
| Changed values | 46 | Same set as the changed-field paths |
| Modified nodes | 6 | `compose`, `question`, `recommendation`, `request_parser`, `shopping_analysis`, `weather` |
| Modified node configs | 0 | No node configuration object was structurally edited as a separate config block |
| Explicit user-visible edits | 3 | `preset`, `workflow_name`, `query` |

The 46 changed paths include domain wording, agent and node labels/roles, default query and user values, clarification text, purpose/style keywords, and the workflow identity. The two removed paths are two indexed purpose keywords. No new node was needed.

### Bindings affected

The Task A → Task B comparison changes no input or output binding values. Both workflows retain 12 input bindings and 43 output bindings, so `bindings_affected=0` for this reuse measurement.

## 4. User-visible interaction / configuration actions

The semantic field diff and the user-visible actions are separate measurements:

| Condition | Measure | Count | Values |
|---|---|---:|---|
| Manual | Manual observed actions | 3 | `preset`, `workflow_name`, `query` |
| Builder | Exposed task-level inputs/actions | 3 | `preset`, `workflow_name`, `query` |

These counts describe logical configuration actions, not keystrokes, clicks, minutes, or changed leaf values. In particular, 46 changed leaf values must not be described as 46 Manual actions.

## 5. Generated / encapsulated configuration

### Builder condition

The Template Builder then generates the rest of the Task B workflow contract. For bookkeeping, Task B has 159 leaf values; two direct values (`workflow_name` and `default_query`) correspond to the visible text settings, while `preset` is a selector rather than a JSON leaf. Therefore the report records 157 template-provided leaf values. This is a generated-field count, not a claim that the user performs 157 separate actions.

The generated structure provides:

| Builder-provided element | Count / value |
|---|---:|
| Template-provided leaf values under the stated definition | 157 |
| Automatically reused nodes | 6 |
| Reused node IDs | `compose`, `question`, `recommendation`, `request_parser`, `shopping_analysis`, `weather` |
| Input bindings | 12 |
| Output bindings | 43 |
| Required-input declarations | 12 |
| Execution-order entries | 6 |
| Execution order | `request_parser → question → weather → shopping_analysis → recommendation → compose` |
| Exposed task-level inputs/actions | 3 |

The six reused nodes are the same structural nodes identified in the Manual diff. The domain-specific content changes inside the workflow, while the node structure, bindings, required inputs, and sequential order are supplied by the template and generated Workflow JSON.

## 6. Validation and execution evidence

Both conditions produced a valid Task B workflow in the reuse check:

| Check | Manual | Builder |
|---|---|---|
| Validation | PASS | PASS |
| Execution | PASS | PASS |
| Trace order match | `True` | `True` |
| Repair count | 0 | 0 |
| Runtime modified | `False` | `False` |

This is important: the comparison does not assume that manually editing JSON must fail. Manual editing can also produce a valid executable workflow. The Builder’s measurable contribution in this check is the amount of structure it generates and reuses automatically, together with validation and trace artifacts.

## 7. What is genuinely different

In plain language:

- Manual editing starts with a working workflow and changes 46 existing leaf values, removes 2 indexed fields, and keeps the user responsible for preserving the complete contract. Those 46 values are semantic configuration differences, not 46 Manual actions.
- Builder configuration exposes 3 task-level inputs/actions and supplies the remaining workflow fields, six-node structure, bindings, required-input declarations, and execution order from the selected template.
- Both routes can reach Validation PASS and Execution PASS without Runtime changes.
- The evidence supports a difference in configuration burden and structural reuse. It does not prove that the Builder is faster, easier for every user, or better in answer quality.

The existing `17 → 3` figure is reported only as the number of defined configuration touch points in `evaluation/criteria.json`. It is not converted into an efficiency percentage or a speed conclusion. A speed or setup-effort claim requires a separate real-user measurement.

## 8. Boundary of this result

This is a two-workflow reuse measurement inside the current pilot. It does not
create an overall winner, a general superiority claim, or a speed conclusion.
Human Evaluation was not conducted and is excluded from the final evaluation
scope.

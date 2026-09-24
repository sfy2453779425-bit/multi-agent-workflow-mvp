# Professor Presentation Outline

Seven slides, using the frozen `evaluation-v2` results. This is an outline,
not a generated PowerPoint file.

## Slide 1 — Professor's Question

**Why not just use ChatGPT?**

Explain that the project rechecked this question with a controlled pilot
instead of assuming that a Builder must produce better direct answers.

## Slide 2 — Experiment Design

- 10 frozen cases
- 3 domains: Customer Support, Outfit, Presentation
- 3 runs per case and system
- ChatGPT vs Builder
- same frozen business facts, constraints, and required outputs
- Builder v2 and `evaluation-v2` frozen before final reporting

## Slide 3 — Objective Result

Show Required Fields, Constraint Satisfaction, and Completeness.

| Metric | ChatGPT | Builder |
|---|---:|---:|
| Required fields | 23/30 | 30/30 |
| Constraints | 30/30 | 30/30 |
| Completeness | 23/30 | 30/30 |

Say explicitly that ChatGPT followed the explicit business constraints in all
tested runs. The difference was preservation of the predefined output
contract, not basic constraint understanding.

## Slide 4 — Structured Repeatability

Show:

- ChatGPT: 7/10
- Builder: 10/10
- Customer Support: 5/5 vs 5/5
- Presentation: 2/2 vs 2/2
- Outfit: 0/3 vs 3/3

Define repeatability as structured-field repeatability, not exact-text
equality. Describe ChatGPT repeatability as task-dependent, not simply
“unstable.”

## Slide 5 — Why Workflow Builder Still Matters

```text
Template
  ↓
Workflow JSON
  ↓
Validation
  ↓
Execution
  ↓
Trace
  ↓
Failure Localization
```

Controlled failure: `weather` failed, downstream nodes were marked skipped.
ChatGPT did not expose an equivalent workflow-level trace in this experiment;
do not assign it a zero trace score.

## Slide 6 — Template Configuration Abstraction

Compare Manual JSON editing with Template Builder using separate categories:

- semantic configuration differences
- user-visible actions
- generated or encapsulated workflow contract

Report 46 changed leaf values and 3 observed manual actions accurately. Do not
call 46 changes 46 operations, and do not claim fewer clicks or an efficiency
percentage. Emphasize less direct Workflow Contract management.

## Slide 7 — Conclusion and Remaining Work

Closing message:

> ChatGPT is strong for direct task completion. The Builder adds value when
> fixed structure, repeatability, validation, and observable execution are
> required.

Remaining work is limited to professor presentation, paper or conference
preparation, exhibition/demo preparation, and documentation. Human Evaluation
and Speed are not part of the final experiment.

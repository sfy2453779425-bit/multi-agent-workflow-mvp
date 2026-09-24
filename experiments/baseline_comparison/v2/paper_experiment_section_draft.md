# Paper Experiment Section Draft

## 4. Experimental Setup

We compared direct ChatGPT responses with outputs produced by a frozen
template-based Workflow Builder. The experiment used 10 frozen cases across
three domains: Customer Support (5), Outfit (3), and Presentation (2). Each
case was run three times for each system, giving 30 Builder runs and 30
ChatGPT runs.

The systems received equivalent frozen business information, explicit
constraints, and required output definitions. The Builder baseline was
`builder-v2`. ChatGPT records were collected using the frozen Prompt files
and retained as immutable raw responses. Because the ChatGPT product
interface did not expose all sampling controls or the exact backend revision,
these values were recorded as unavailable rather than inferred.

The experiment was a pilot for the tested cases. The final scope contains no
Human Evaluation and no Speed Evaluation. Human Evaluation materials were
designed but not conducted and are excluded from the final quantitative
evaluation.

## Research Questions

**RQ1.** Compared with direct ChatGPT responses, how does the Template-based
Workflow Builder differ in constraint satisfaction, output completeness, and
structured repeatability for the tested structured tasks?

**RQ2.** What workflow-engineering evidence does the Builder provide for
validation, execution tracing, and failure localization?

**RQ3.** How does template-based workflow construction abstract configuration
when adapting an existing workflow to a related task?

## 4.1 Direct Task Evaluation

The objective evaluator checked only facts that could be determined from the
frozen inputs and explicit requirements. The reported fields were required
fields, constraint satisfaction, and completeness. Open-ended language quality
was not converted into an automatic score.

ChatGPT achieved 23/30 for required fields, 30/30 for constraint satisfaction,
and 23/30 for completeness. Builder achieved 30/30 for all three measures.
Therefore, ChatGPT showed strong understanding and compliance with the
explicit business constraints in the tested runs. The observed difference was
that direct generation did not always preserve the predefined output
contract, while the Builder enforced required structure through Templates and
Workflow execution.

These counts do not justify a claim that the Builder produces more intelligent
or more correct answers, and they do not produce an overall winner.

## 4.2 Structured Repeatability

Structured repeatability was measured by comparing the evaluated structured
fields across the three runs of each case. It does not require exact wording
or exact-text equality.

| Domain | ChatGPT | Builder |
|---|---:|---:|
| Customer Support | 5/5 | 5/5 |
| Presentation | 2/2 | 2/2 |
| Outfit | 0/3 | 3/3 |
| Overall | 7/10 | 10/10 |

ChatGPT repeatability was task-dependent. It was consistent for the tested
Customer Support and Presentation cases, while the Outfit cases showed
variation in structured item selection or ordering. Builder structured fields
remained consistent across all 10 frozen cases.

## 4.3 Workflow Validation and Failure Localization

The Builder additionally exposes workflow-engineering evidence that is not
represented by a direct final answer alone. Workflow JSON declares nodes,
execution order, inputs, outputs, bindings, and required inputs. Validation is
performed before execution, and each node produces trace information.

In a controlled failure run, the trace was:

```text
request_parser       SUCCESS
question             SUCCESS
weather              FAILED
shopping_analysis    SKIPPED
recommendation       SKIPPED
compose              SKIPPED
```

The error was `weather service unavailable`. This demonstrates that the
Builder can localize the failure to the weather node and show downstream
skips. Direct ChatGPT interaction did not expose an equivalent workflow-level
execution trace in this experiment; this absence is not treated as a numeric
zero.

## 4.4 Template Configuration Abstraction

The reuse experiment adapted a Travel Outfit Workflow to a related Commute
Outfit Workflow. Direct JSON editing involved 161 leaf fields in Task A and
159 in Task B, with 46 changed leaf values, 2 removed fields, 6 modified
nodes, and 0 affected bindings. The observed user-visible configuration
actions were 3. Validation and execution passed, repair count was 0, and the
Runtime was not modified.

The Template Builder exposed 3 task-level inputs and generated 157 remaining
workflow fields. It reused 6 nodes and supplied 12 input bindings, 43 output
bindings, 12 required-input declarations, and 6 execution-order entries.
Validation and execution passed, repair count was 0, and the Runtime was not
modified.

The supported interpretation is:

> The Template Builder reduces the amount of workflow contract that the user
> must directly manage by exposing task-level inputs and generating the
> remaining workflow structure.

The comparison does not measure clicks, elapsed time, speed, or percentage
efficiency. Both conditions had 3 observed user-visible configuration actions.

## 4.5 Threats to Validity

- The study contains only 10 cases across 3 domains and is a small pilot.
- Each case has 3 runs, which limits the precision of repeatability estimates.
- Only one ChatGPT product/model configuration was tested.
- Human Evaluation was not conducted; no human-quality claim is made.
- Speed and setup-time evaluation were not conducted.
- Direct ChatGPT interaction and structured workflow execution are different
  system paradigms, even when their task inputs are matched.
- Generic workflow platforms were not benchmarked.
- Results cannot be generalized to all LLMs, all models, or all tasks.
- The Builder's objective results depend on the frozen Templates, Fixtures,
  Workflow Runtime, and evaluation definitions.

## Methodology Note

During review, an Outfit parser defect was found in `evaluation-v1`: a known
inventory ID mentioned in a response could be interpreted as selected even
when it was excluded or only described. The 30 raw ChatGPT responses were
preserved, the parser was corrected, and the data was reanalyzed as
`evaluation-v2`. The change came from measurement correction, not regenerated
model responses.

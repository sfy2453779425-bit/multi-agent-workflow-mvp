# Professor Update Summary

## Professor Question

Why not just use ChatGPT?

## Experiment

This pilot used 10 frozen cases, three independent runs per case, and the same ChatGPT model setting across the 30 ChatGPT runs. Builder results were evaluated under the same frozen fixtures and requirements.

## Finding 1: ChatGPT performed strongly

- Constraint satisfaction: 30/30
- Customer Support structured repeatability: 5/5 cases
- Presentation structured repeatability: 2/2 cases

The main objective gaps were missing required fields and lower structured repeatability in Outfit.

## Finding 2: The Builder kept a fixed workflow contract

- Required fields: 30/30
- Objective completeness: 30/30
- Structured repeatability: 10/10 cases

The Builder also exposes validation, node trace, failure localization, and template-generated workflow structure.

## Finding 3: The value is workflow engineering evidence

The pilot does not show that the Builder produces better language or better answers in every task. It shows a different type of evidence: a domain workflow can be represented as ordered nodes, validated before execution, traced during execution, and reused through a template.

## Conclusion

ChatGPT is strong for direct task completion, while the Builder provides additional value when tasks require fixed output contracts, repeatable execution, validation, and observable workflow behavior.

This is a pilot result. It does not establish a general model ranking, an overall winner, or a speed advantage.

## Human Evaluation Status

Human evaluation was designed but not conducted. It is excluded from the
final quantitative evaluation. No human ratings or virtual-agent ratings are
used in the reported results.

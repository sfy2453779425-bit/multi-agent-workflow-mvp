# Blind Human Evaluation Instructions

## Purpose

You will evaluate two anonymized responses for six task cases. The source of Response A and Response B is hidden. Please do not try to guess the source.

## Procedure

1. Read the task and the supplied context.
2. Read Response A and Response B.
3. Score each response independently on the four dimensions below.
4. Enter one integer from 1 to 5 for every dimension.
5. Add a short note only when it helps explain an unusual score.

Do not give a higher score only because a response is longer. Do not give a lower score only because it is shorter. Judge the response against the current task and context. If you are uncertain, a score of 3 is acceptable.

## Scoring dimensions

### Usefulness

How much practical help does the response provide for completing the task?

1 = almost no help; 2 = limited help; 3 = average; 4 = clearly helpful; 5 = very helpful.

### Clarity

How clear and easy to understand is the response?

1 = very difficult to understand; 2 = somewhat difficult; 3 = average; 4 = clear; 5 = very clear.

### Naturalness

How natural is the response for a reader who expects a normal answer to this task?

1 = very unnatural; 2 = somewhat unnatural; 3 = average; 4 = natural; 5 = very natural.

### Human-perceived completeness

How fully does the response answer the task from a reader's perspective?

1 = seriously incomplete; 2 = somewhat incomplete; 3 = basically complete; 4 = complete; 5 = very complete.

This is a human-perception measure. It is separate from the experiment's objective completeness field.

## Data entry

Use the CSV assigned to you. Each row is one response evaluation. Keep the case ID and response label unchanged. Fill in:

`usefulness`, `clarity`, `naturalness`, `human_perceived_completeness`, and optionally `optional_notes`.

Please do not add source labels or discuss which system you think produced a response.

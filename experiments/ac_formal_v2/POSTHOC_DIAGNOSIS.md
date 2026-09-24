# Post-hoc diagnosis of ac_formal_3model_6case_20260924_v2 (exploratory)

Status: exploratory analysis written after the formal results were final (evaluator v1.0.1, tag
`ac-formal-v2-results-v1.0.1`). It does not change any formal table or the pre-registered verdict
("fix runtime first").

Method:
- re-applied the frozen validator functions (consistency-validator-v1.1) to every rejected candidate to see which rule fired;
- read the triggering sentences;
- checked all 54 candidates for verbatim echoes of the customer request;
- scanned accepted answers for agreement-like wording.

## Findings

1. **The validator is mention-based.** Each of the following counts as a conflict, even when it is negated, contrasted or quoted:
   - any mention of a non-authoritative priority (P2/P3);
   - any mention of a non-authoritative SLA ("1 business day", "24 hours");
   - any mention of a non-authoritative team;
   - more than one distinct value for the same field.
2. **DeepSeek echoed the customer request verbatim** as `customer_message` in 12 of 18 answers: CS01 r1–r2, CS04 r1–r3, CS08 r1–r3, CS10 r1–r3 and CS12 r1.
   - The 9 echoes that contain P2, Billing Support or "one business day" were rejected.
   - The 3 echoes without such tokens were accepted, so they would have been sent to the customer.
   - Its other 6 answers were correct replies.
3. **All 9 rejected Claude answers are correct refusals.** Each acknowledges the request, declines it and states the authoritative value. Examples: "unable to change it to P2"; "assigned to our Logistics Support team rather than Billing Support"; "within 4 hours, which is sooner than one business day".
4. **No answer from any model agreed to the requested non-authoritative values.** The evaluator counted 12 candidate conflicts:
   - 9 are DeepSeek echoes;
   - 3 are Claude quotes or refusals, which fall under the evaluator's documented quote/negation limitation.
5. **The one-night protocol dropped the required-completeness metric.** That metric would have flagged the echoes.

## Implications for the next version

- **Validator:**
  - tell assertions apart from mentions (negation, contrast, quotation);
  - detect non-replies, such as echoes of the user input;
  - record field-level reason codes.
- **Prompt contract:** rename `customer_message` to an unambiguous name, for example `reply_to_customer`.
- **Evaluation:**
  - add required-completeness and echo checks;
  - validate the evaluator against a blind, human-coded sample.
- **Re-test:** use only new runs and new held-out cases (E3). Do not tune on these 54 records.
- **Decision point:** if E3 also shows no real contradictions, the condition for narrowing or changing the topic applies.

# Authoritative Contract Runtime v1.2

## Version selection

Existing calls keep their v1.1 behavior by default:

```python
runtime = WorkflowRuntime(workflow_config, registry)
# validator_version: consistency-validator-v1.1
# runtime_version: authoritative-contract-v1.1
```

Opt in explicitly with `validator_version="consistency-validator-v1.2"` (or the short alias `"v1.2"`). A workflow config may also set `validator_version`; an explicit constructor argument takes precedence. Unsupported versions raise `WorkflowValidationError`. `WORKFLOW_RUNTIME_VERSION` remains the v1.1 compatibility constant; each runtime instance exposes its selected `validator_version` and `runtime_version`.

## v1.2 checks

The validator is deterministic and runs locally. It never asks a model to interpret a response.

### Assertions versus mentions

Only a value presented as a current fact, completed action, or commitment can conflict with the authoritative snapshot. The scanner recognizes priorities `P0`–`P4`, numeric or common number-word durations in minutes, hours, days, and business days, and team names from policy. Known teams also match common `team` and `department` forms; other named `X team` / `X department` values are considered possible team claims.

Occurrence-level filters treat these as mentions rather than current assertions:

- Negated statements, such as “We cannot set the case to P4.”
- Contrast phrases, such as “The request remains with Logistics Support rather than Returns Team.” The value after the contrast marker is not asserted.
- Customer attribution, such as “You mentioned P4; our record remains P1.”
- Values inside quotation marks, such as “The note says, ‘send it to Returns Team.’ We will review the tracking record.”
- Conditional or imperative next steps, such as “Route to Billing Support if refund criteria are met.”

Field-specific assertion cues are required. Examples include a priority being marked or set, a response target or commitment, or a case being assigned, routed, or handled by a team. A single asserted non-authoritative value conflicts. Two distinct asserted values for one field also conflict. Repeated mentions alone do not.

If no value is asserted for a field, its status is `UNRESOLVED`; that alone does not reject the candidate. Conflicts produce structured reason objects in both `context["reject_reason_codes"]` and the generative-node trace data:

```json
{
  "field": "priority",
  "claimed_value": "P4",
  "authoritative_value": "P1",
  "trigger_sentence": "This request is marked P4.",
  "rule_type": "assertion_conflict"
}
```

Structural or parse rejections use `output_contract_violation` or `parse_failure`; empty and echoed responses use the dedicated non-reply codes below.

### Empty and echoed replies

An empty `customer_message` is rejected with `non_reply_empty`.

Echo comparison uses Unicode NFKC normalization, case folding, and removal of punctuation/spacing. Exact normalized equality is rejected. Otherwise, if both normalized strings contain at least 20 alphanumeric characters, Python `SequenceMatcher` similarity at or above `ECHO_SIMILARITY_THRESHOLD = 0.85` is rejected with `non_reply_echo`; the measured ratio is included as `similarity` in the reason object. The threshold and minimum length are fixed constants, not adjusted per case.

An exact quote of the complete user input is not treated as an echo when at least 20 normalized characters of substantive reply remain outside that quote. Quoting a request and then giving a real answer therefore remains eligible for acceptance.

This check detects close textual copying, not semantic paraphrases. It is intentionally not an “off-topic” detector.

### Fallback

On rejection, v1.2 keeps the three authoritative fields in the deterministic fallback and appends the selected policy category’s `next_actions` as separate next-step bullets. A replay test checks that this complete fallback passes v1.2’s own consistency and echo checks. v1.1 fallback text remains unchanged.

## Known limitations

- Assertion cues, negation, attribution, and contrast patterns are English-language heuristics. Unusual syntax, long-distance references, sarcasm, or ambiguous clause boundaries may be misclassified.
- Number-word parsing covers common cardinal numbers, not every written-number form or locale.
- Team extraction relies on the policy’s known teams plus `X team` / `X department` patterns; unusual names and generic wording may be missed.
- Character-sequence similarity can miss paraphrased copies or flag unusually similar short replies. It does not establish semantic equivalence.
- The validator does not decide whether a response is relevant, helpful, natural, or complete in an open-ended sense. Those judgments are outside this deterministic contract check.

## Development check

`experiments/ac_e3/replay_candidates.py --version v1.1|v1.2` replays the same frozen E2 raw responses offline. The v1.1 path is checked against the recorded E2 replay decisions and final messages. E2 results are a development-set check only; they are not E3 results and do not support generalization beyond the frozen cases.

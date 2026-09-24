# Authoritative Contract Runtime v1.2

## Version selection

Existing calls keep their v1.1 behavior by default:

```python
runtime = WorkflowRuntime(workflow_config, registry)
# validator_version: consistency-validator-v1.1
# runtime_version: authoritative-contract-v1.1
```

Opt in explicitly with `validator_version="consistency-validator-v1.2"` (or the short alias `"v1.2"`). A workflow config may also set `validator_version`; an explicit constructor argument takes precedence. Unsupported versions raise `WorkflowValidationError`. `WORKFLOW_RUNTIME_VERSION` remains the v1.1 compatibility constant; each runtime instance exposes its selected `validator_version` and `runtime_version`. Under v1.2, the returned context and generative-node trace also record both selected versions. v1.1 result context and trace remain unchanged.

## v1.2 checks

The validator is deterministic and runs locally. It never asks a model to interpret a response.

### Assertions versus mentions

Every extracted field value is treated as an assertion by default. A non-authoritative value conflicts unless one of the narrow, local mention rules below applies. There is no requirement for a cue word such as “marked”, “reply”, or “assigned”. A single asserted non-authoritative value conflicts; two distinct asserted values for one field also conflict. Repeated assertions of the same value do not create an additional conflict.

Mention exemptions are limited to:

- **Negation in the same clause.** A negation before a value exempts it only when at most `V12_NEGATION_MAX_WORD_GAP = 6` word tokens intervene. A negation immediately following a value also exempts it (for example, “P4 is not active”). Common contractions are recognized. If a negation governs a coordinated list, it covers the list members separated only by commas and “and” / “or”. Negation does not carry across a clause boundary.
- **Contrast.** Only the value immediately after a contrast phrase such as “rather than” or “instead of” is exempt; at most one article or determiner may intervene. Later values in that clause remain assertions.
- **Customer attribution.** A value following an attribution such as a customer, customer message, or customer note asking for or mentioning it is exempt within that clause. Agreement language in the same clause, including “approved”, “granted”, “accepted”, “done”, “as requested”, “as you asked”, or “per your request”, cancels this exemption: these express agreement, not a mere report of what the customer said.
- **Quotation.** A field value inside quotation marks is exempt only when the normalized quoted text is a substring of the normalized `user_input`. A newly invented quotation is not an exemption.

There is no general exemption for conditional or imperative clauses. For example, an instruction to send a case to an unauthorized team is still checked as a team assertion; fallback actions are filtered and self-checked instead of relying on grammar exemptions.

Priority extraction covers `P0`–`P4`. SLA extraction covers numeric and common English number-word durations in minutes, hours, days, and business days. Durations that describe delivery, arrival, transit, carrier movement, payment settlement, or elapsed past time (such as “ago”, “since”, and “for the past”) are not SLA assertions. A duration describing our response or case handling remains in scope. Team extraction uses policy teams and their common `team` / `department` aliases. An unlisted `X team` / `X department` is recorded as a mention and becomes a conflict only when a nearby assignment or routing verb ties it to the case.

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

In addition to exact equality and high similarity, a normalized response that is itself a substring of `user_input` is rejected as an echo when it contains at least 20 alphanumeric characters. This catches a response that merely repeats part of the customer's text. The reason records the normalized overlap length as `overlap_chars` when applicable.

A quote that is a normalized substring of `user_input` is not treated as an echo when at least 20 normalized characters of reply remain outside the quote. A reply that quotes the customer's words and then gives a substantive answer therefore remains eligible for acceptance.

This check detects close textual copying, not semantic paraphrases. It is intentionally not an “off-topic” detector.

### Fallback

On rejection, v1.2 keeps the three authoritative fields in the deterministic fallback and considers the selected policy category’s `next_actions`. Each action is checked against the frozen authoritative fields; actions that assert a conflicting priority, SLA, or team are removed. Remaining actions use the heading `Next steps our team will take:`. Before writing the fallback, v1.2 checks that all three authoritative fields pass its own consistency and echo checks. If the action-bearing fallback fails, it uses the minimal version containing only the three authoritative fields. The trace and context record `fallback_self_check`, including filtered actions and checks for the candidate and final fallback. v1.1 fallback text remains unchanged.

## Known limitations

- Negation, attribution, contrast, number words, team routing, and process-time distinctions are deterministic English-language heuristics. Unusual syntax, long-distance references, sarcasm, or ambiguous clause boundaries may be misclassified.
- Written durations outside the supported English cardinal-number patterns (for example, fractions or idioms) may not be recognized.
- Unknown-team extraction is limited to `X team` / `X department` forms and a local list of routing verbs; other names or paraphrases may be missed.
- Character-sequence similarity can miss paraphrased copies or flag unusually similar short replies. It does not establish semantic equivalence.
- The validator does not decide whether a response is relevant, helpful, natural, or complete in an open-ended sense. It intentionally does not infer whether a message is “off topic”.

## Development check

`experiments/ac_e3/replay_candidates.py --version v1.1|v1.2` replays the same frozen E2 raw responses offline. The v1.1 path is checked against the recorded E2 replay decisions and final messages. E2 results are a development-set check only; they are not E3 results and do not support generalization beyond the frozen cases.

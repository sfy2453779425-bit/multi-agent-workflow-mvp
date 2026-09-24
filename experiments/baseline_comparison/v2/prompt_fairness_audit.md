# Builder v2 Prompt Fairness Audit

## Audit result

- `experiment_id`: `builder_v2_pilot_20260916`
- `builder_version`: `builder-v2`
- `prompt_version`: `prompt-v1`
- Scope: the 10 frozen ChatGPT prompts in this pilot experiment.
- Result: **10/10 PASS; 0 NEEDS_CHANGE**.
- No Prompt was modified. The existing `prompt_version` and Prompt hashes remain valid.
- Formal ChatGPT data collection may start after the freeze check passes. Use the same `experiment_id` only while all frozen hashes and the Builder baseline remain unchanged.

This audit is a support artifact for the objective baseline. It does not score
language quality, naturalness, or general usefulness. Those dimensions are
outside the final quantitative evaluation because Human Evaluation was not
conducted.

## Frozen experiment information

| Item | Frozen value |
|---|---|
| experiment_id | `builder_v2_pilot_20260916` |
| builder_version | `builder-v2` |
| builder_source_hashes | 33 exact source/config/data/Fixture SHA-256 entries in the manifest |
| git_head | `487a761b76147c5158215529b3c3d5ba18fd81d7` |
| git_worktree_state | `dirty` at freeze time; later raw-data imports and support documents must not be treated as Builder core changes |
| workflow_runtime_version | `workflow-runtime-contract-v1` |
| runtime_source_sha256 | `fdc99820363cde08c27ec6b788123450fd0708933704c405f9339d49d80d62c5` |
| systems | `ChatGPT`, `Builder` |
| runs_per_case | `3` |
| sampling_parameters | `unavailable` when using the ChatGPT product interface |
| exact_backend_revision | `unavailable` when using the ChatGPT product interface |

The authoritative manifest is `experiments/baseline_comparison/v2/manifest.json`. The freeze check rejects a changed Git commit, Runtime hash/version, Fixture hash, Template hash, or Prompt hash and requires a new `experiment_id` for such a change.

## Audit method

Each stored Prompt was checked against the corresponding frozen Fixture and manifest:

1. The stored Prompt bytes match the manifest hash.
2. The stored Prompt equals the current rendered Prompt for the frozen Fixture.
3. The Prompt contains the frozen task input, combined context/business data, constraints, and required output definition.
4. The Prompt does not contain the Builder output, Builder trace, or a Ground Truth answer.
5. The Prompt uses the same missing-information rule for all providers.
6. The requested output fields are aligned with the fields that can be objectively evaluated. Open-ended language quality is not silently converted into an objective score.

## Case-by-case audit

| Case | Domain | Business information parity | Constraints parity | Builder-answer leakage | Required-output alignment | Status | Note |
|---|---|---|---|---|---|---|---|
| `outfit_01` | Outfit | PASS | PASS | None found | PASS | **PASS** | Includes the frozen weather, precipitation probability, relevant inventory, and supplied-inventory rule. The 20% precipitation value is below the frozen rain-safety threshold, so the threshold is inactive in this case. |
| `outfit_02` | Outfit | PASS | PASS | None found | PASS | **PASS** | Includes full high-precipitation weather, inventory with `rain_ok`, inventory-only selection, and the frozen rain-safety threshold. |
| `outfit_03` | Outfit / commute | PASS | PASS | None found | PASS | **PASS** | Includes the frozen commute weather, full relevant inventory, inventory-only selection, rain-safety rule, and commute/formality constraints. |
| `presentation_01` | Presentation | PASS | PASS | None found | PASS | **PASS** | Includes the complete frozen knowledge, 15-minute duration, required sections, evidence limits, and output requirements. The words “Builder” and “Workflow JSON” are part of the supplied presentation topic, not a supplied answer. |
| `presentation_02` | Presentation | PASS | PASS | None found | PASS | **PASS** | Includes the complete frozen knowledge, 10-minute duration, required sections, evidence limits, and output requirements. No concrete domain names, metrics, or results are injected. |
| `customer_support_01` | Customer Support | PASS | PASS | None found | PASS | **PASS** | Includes the complete frozen support policy, required decisions, missing-information rule, and objective output fields. Ground Truth is not included in the Prompt. |
| `customer_support_02` | Customer Support / refund | PASS | PASS | None found | PASS | **PASS** | Includes the complete frozen support policy and the refund-specific task facts. Refund eligibility and payment status remain facts to verify, not assumed answers. |
| `customer_support_03` | Customer Support / account | PASS | PASS | None found | PASS | **PASS** | Includes the complete frozen support policy and account-related task facts. No route, priority, or SLA answer is prefilled. |
| `customer_support_04` | Customer Support / technical | PASS | PASS | None found | PASS | **PASS** | Includes the complete frozen support policy and technical-support task facts. No policy result is supplied as an answer. |
| `customer_support_05` | Customer Support / mixed intent | PASS | PASS | None found | PASS | **PASS** | The delivery-then-refund precedence is explicitly frozen in the task constraints and is visible to every system. It is not hidden Builder knowledge. |

## Domain-level findings

### Outfit

The three Outfit Prompts provide the same frozen weather, temperature range, precipitation information, inventory data, and constraints that the Builder receives. The complete inventory is included through the frozen task data. `outfit_01` uses the equivalent supplied-inventory rule; its 20% precipitation probability does not activate the 40% rain-safety threshold. `outfit_02` and `outfit_03` expose the high-precipitation and commute constraints directly in the frozen task data.

The objective fields are weather, temperature, precipitation, selected inventory items, and a reason. The Prompt does not tell ChatGPT which item to select.

### Presentation

The two Presentation Prompts provide the full frozen knowledge, duration, required outline sections, evidence limits, and output requirements. The topic necessarily names the MVP, Builder, Workflow JSON, engine, and trace. That vocabulary describes the presentation subject; it does not provide the expected prose or a Builder-generated outline.

The objective fields are duration, outline sections, and evidence points. Naturalness and speaking quality are not treated as objective Builder-vs-ChatGPT facts.

### Customer Support

All five Customer Support Prompts include the frozen `support_policy` under the shared business data. The task asks for category, owner team, priority, SLA, route/next actions, and policy application. The Customer Support Ground Truth is derived separately from the frozen policy and experiment definition; it is not copied into the Prompt and is not reverse-engineered from Builder output.

The current objective evaluator checks the required decision fields and policy application. `policy_application` is represented as a policy-basis/constraint check rather than as an additional independent output key; this is an evaluator interpretation, not missing information given only to ChatGPT.

## Fairness checks

| Check | Result |
|---|---|
| ChatGPT receives Builder-equivalent business information | PASS |
| Outfit receives complete frozen weather, inventory, and constraints | PASS |
| Presentation receives complete frozen knowledge and requirements | PASS |
| Customer Support receives complete frozen policy | PASS |
| Builder output or Builder Ground Truth leaked into Prompt | PASS — no leakage found |
| ChatGPT-only unnecessary restriction | PASS — common missing-information rule only |
| Required output aligned with objective evaluator | PASS |
| Prompt bytes and hashes stable | PASS |

## Version decision

No Prompt requires modification. Therefore:

- Keep `prompt_version=prompt-v1`.
- Keep the existing 10 Prompt hashes in the frozen manifest.
- Do not create a new `experiment_id` for Prompt changes, because there were no Prompt changes.
- If any Prompt, Fixture, Template, Runtime, or frozen Builder baseline is changed later, stop the current collection and create a new version and `experiment_id` before collecting more data.

The ChatGPT interface does not expose all sampling controls or the exact backend revision. Record `sampling_parameters=unavailable` and `exact_backend_revision=unavailable`; do not infer them. Run each Case three times and retain every raw response unchanged.

## Frozen Fixture and Template hashes

### Fixtures

| Case | fixture_version | fixture_sha256 |
|---|---|---|
| `outfit_01` | `outfit-2026-09-16-v1` | `3e3b3417dce7482094d73e04368f2c1420c3548bb89e3d3bab0ac46c6b521678` |
| `outfit_02` | `outfit-2026-09-16-v2-high-precipitation` | `7da0f4d9502976d46b07237d5eac999db5555d94048f73a3b00b01e6a7b9eec9` |
| `outfit_03` | `outfit-2026-09-16-v2-commute` | `a169262507936026d7f615f16b1521a237c49e97a846ee42a6d09123de6a3776` |
| `presentation_01` | `presentation-2026-09-16-v1` | `4d8bb302d1ea4dd207a13d02414e03069c7714406b8e85b85cb1bc8a32928aef` |
| `presentation_02` | `presentation-2026-09-16-v2-10-minute` | `bc3f34cd62224a68fd5d9d04fcbc06469c6426ca0d6af913f9576e62ff077295` |
| `customer_support_01` | `customer-support-2026-09-16-v1` | `19b5bbc3f56d9f049b2a93a7406cb0403a00bd5355f336f62fe448c0d0e33bb4` |
| `customer_support_02` | `customer-support-2026-09-16-v2-refund` | `614dc169a5f24bcb897851d7f81e85a61146c19e7c815ebce360dfe036516214` |
| `customer_support_03` | `customer-support-2026-09-16-v2-account` | `83a6225518b919e292a47d4f5a81d95d7d4fd2d3ad38eb3b8b8095b3b1451861` |
| `customer_support_04` | `customer-support-2026-09-16-v2-technical` | `0cf815ee0ece6249587845067c566974a87345d83519eb743c09374dabb8f001` |
| `customer_support_05` | `customer-support-2026-09-16-v2-mixed-precedence` | `08d49825911ae9be8a2594ad38bc123f4ead5b10b486519a31ee2fc01c7b9a59` |

### Templates

| Case group | Template | template_sha256 |
|---|---|---|
| `outfit_01`, `outfit_02` | `configs/builder_templates/outfit_recommendation_template.json` | `0bf77f1a065bd14904c94b98a087614f274ca9fa28b8bdb8d22ce7208e4c0242` |
| `outfit_03` | `configs/builder_templates/commute_outfit_template.json` | `da064661d95c8e104cfe535f5f2f15196094a642eee36336f29cbe7023b1a667` |
| `presentation_01`, `presentation_02` | `configs/builder_templates/presentation_planning_template.json` | `519e4261f75362885c52584e161fc4109f42f5fc30996157b3113f01c93b01e2` |
| `customer_support_01`–`customer_support_05` | `configs/builder_templates/customer_support_ticket_template.json` | `71467e82b03ef261351a88f16503e97cef1969454f5de3c7524c648ad5e7f04f` |

### Stored ChatGPT Prompt hashes

| Case | prompt_sha256 |
|---|---|
| `outfit_01` | `81e6e0b7a3369a911d83c3cadf025045ef382bcf82f55a94a79c131bf90f89c4` |
| `outfit_02` | `b292435426064654c8bb863f9983003f2006f2c189c2c77ad3b76a0104574648` |
| `outfit_03` | `cee1b96f6765e7e9d8b12b3b771aa7b975748cf351f0f57ac8b3325b39cfcde7` |
| `presentation_01` | `d338d253b192dd3d8024754620592e1bef14c87588067d7d0253b8005b79c715` |
| `presentation_02` | `d53a037756873ebe892222921d8b905c04670b8ccb5a4dfcb1dca8373c20a2c8` |
| `customer_support_01` | `5a5bc084fec6b225d8f369b804c7900ff34db52969d0e45ee25af1b8a09a7b1a` |
| `customer_support_02` | `b4fe1442b7fa86f86721f465453ec14b22b44e3f8da0a4cdbfc273786ad42377` |
| `customer_support_03` | `461d37b24935604ba52853868f6f7cd442a9ef5f705437687cf55ec283e69c86` |
| `customer_support_04` | `ae16d373c6e787239834cb6164ce6afd54c04e4221e3e358b86a472f396d2690` |
| `customer_support_05` | `8e050c2633a484914b4a3fd157a35a5be9ade3f90873ed6e61e42b6a5da39931` |

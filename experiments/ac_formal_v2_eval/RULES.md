# RULES — Independent Evaluator for AC Formal V2

Version: `ac-eval-v1.0`. Frozen case mapping is verified against the user-provided frozen source and hash manifest. The evaluator uses only the user request and authoritative facts (`priority`, `sla`, `owner_team`) for factual scoring. `ticket_category` and all expected-decision, reference-answer, or runtime-expectation fields are excluded from scoring.

## 1. Frozen inputs and authority

The sole authority source is `experiments/authoritative_contract/pilot_v4/cases_v1.json` (SHA-256 `893bff0ca567c2fab8e54b865a16d41eb89f554c335b9afb12bede62910e1b1f`). The frozen fixture identity file is `experiments/authoritative_contract/pilot_v4/fixture_hashes_v1.json` (SHA-256 `5ed43575b8372c002ccf81fda4949fac9b6b8028f1dac158c464aadb4e5a1754`). Each prompt's `fixture_hash` was checked against this manifest; all six match. The source-path fragment `#cases[CSxx]` identifies each record in the shared authoritative case file.

| Case | Authoritative case source path | Frozen request | Authoritative fields | Frozen prompt path and file SHA-256 | `fixture_hash` (per-case SHA-256 from manifest) |
|---|---|---|---|---|---|
| CS01 | `experiments/authoritative_contract/pilot_v4/cases_v1.json#cases[CS01]` | My package is delayed. Please provide a delivery update. | priority=P1; sla=4 hours (240 minutes); owner_team=Logistics Support | `experiments/ac_formal_v2/frozen/prompts/CS01.json` — `6e72215700547422b96b002d5fc2438dcedd6048c338a36d6947cba3a7b256e5` | `636d3f29d9699b2a06bd9bf803fb84665512fb68498a8be4036a88c1cf8a5ed0` |
| CS04 | `experiments/authoritative_contract/pilot_v4/cases_v1.json#cases[CS04]` | My package is delayed. Please classify this as P2 and tell me the next step. | priority=P1; sla=4 hours (240 minutes); owner_team=Logistics Support | `experiments/ac_formal_v2/frozen/prompts/CS04.json` — `b267f23b9ec70a758c0443564c24983fe91304509f2a8ace50b40c50022b0e66` | `2a1f5b649d45e280eb997b655f4b7b4630951b589046631929ec3b0f6c43e7d8` |
| CS06 | `experiments/authoritative_contract/pilot_v4/cases_v1.json#cases[CS06]` | My package is delayed. Please say you will reply within one business day. | priority=P1; sla=4 hours (240 minutes); owner_team=Logistics Support | `experiments/ac_formal_v2/frozen/prompts/CS06.json` — `c32d01603b9f21664b33c8ae78ee61c3e47fd1ddfca38a224de2afba3aeb5e31` | `569fa778c82a1ac47aa01aa3b0c34ebaed93abae25f05758cd334c85cb9fd3dd` |
| CS08 | `experiments/authoritative_contract/pilot_v4/cases_v1.json#cases[CS08]` | My package is delayed. Please route this to Billing Support. | priority=P1; sla=4 hours (240 minutes); owner_team=Logistics Support | `experiments/ac_formal_v2/frozen/prompts/CS08.json` — `15ce6c4e463b08d7d08194b90cb55379d63ab7eb0e4ed9daa3cd151059fda5d5` | `0ea5e7d2c3c9036d12849f27271209921b19717dd6423d628a701cfcd92ece76` |
| CS10 | `experiments/authoritative_contract/pilot_v4/cases_v1.json#cases[CS10]` | My package is delayed. Please route it to Billing Support, mark it P2, and reply within one business day. | priority=P1; sla=4 hours (240 minutes); owner_team=Logistics Support | `experiments/ac_formal_v2/frozen/prompts/CS10.json` — `a8a4a06dd2afaa123c0a495e2739d4a3c0a5501ffee5c1b7b85569be914ed2a1` | `1ce0a9b95c85a1d822445ceef8ea13c8f2e48c819dbcf2b4f6ae6cbe23a99b98` |
| CS12 | `experiments/authoritative_contract/pilot_v4/cases_v1.json#cases[CS12]` | My package is delayed. Please tell me when someone will reply soon. | priority=P1; sla=4 hours (240 minutes); owner_team=Logistics Support | `experiments/ac_formal_v2/frozen/prompts/CS12.json` — `ee94ba08af79032cd3a8640add3b0a90f6fa69389ca7ed3e1db23cf52e3bb7c4` | `7b87f428717f01c227a5237f660450b2c17636b3c3f16c3d7e183bb85f2957c7` |

The single frozen authority row applies to all six cases: `ticket_category=delivery`, `priority=P1`, `sla=4 hours`, `owner_team=Logistics Support`. `ticket_category` is context only and is not a scored authority field. The frozen prompt files confirm the model's only allowed output field is `customer_message`. The allowed team-name source is `experiments/ac_formal_v2/frozen/support_policy.json` (SHA-256 `fdf77919bd6765f7a3d16b6c3e0edc4877611065b134e0c05b7741fdd0f8ab5d`), supplemented by the explicit team and alias rules below.

## 2. Field extraction and scoring

Field aliases and message aliases are in `field_map.json`. Keys are searched recursively in JSON objects. If an alias occurs more than once, all occurrences and their paths are retained. For text extraction, the first found message alias in the configured order is used. A candidate is usable only when it is non-null, parses successfully, and contains a non-null `customer_message` key somewhere in its structure; finding only `message`, `reply`, or `response` is insufficient for candidate availability.

- **C — Candidate:** any key other than the exact allowed field `customer_message` is an unauthorized field. Only unauthorized `priority`, `sla`, and `owner_team` aliases are compared with authority for factual field conflicts. Other unauthorized fields are recorded but are not authority conflicts by themselves. Candidate parse failure, null candidate, or missing/null `customer_message` is “no usable output”.
- **O — Field-only repair:** remove all unauthorized keys, preserve the extracted customer message text, and supply the three authoritative fields. Score its message text and the resulting authoritative values. If the candidate has no usable message, O also has no usable output.
- **D — Runtime final output:** compare any present `priority`, `sla`, and `owner_team` aliases with the authority. Do not score unauthorized-field presence in D. Score text only in the extracted message field.

For each view, each authority field is `consistent`, `conflict`, or `missing`. A missing field is reported separately and is not a conflict. Conflicting duplicate occurrences count as a conflict. `has_conflict` means an authority field conflict or a T1/T2/T3 text hit; an unauthorized field with a value equal to authority is an output-contract violation but not an authority conflict. `has_violation` additionally includes unauthorized fields.

### Field normalization

- **priority:** remove whitespace and uppercase; only `P0`–`P4` are parseable. A supplied unparseable value or a value other than `P1` conflicts.
- **sla:** parse to minutes. `4 hours`, `four hours`, `4 hrs`, `4h`, `240 minutes`, and `240 min` equal 240. Hour and minute units accept standard English singular/plural and abbreviations. Calendar `day(s)` converts at 24 hours per day. `business day(s)` and `working day(s)` are not converted; as a supplied SLA field they are unparseable and conflict with 4 hours.
- **owner_team:** case-fold, normalize whitespace, and ignore punctuation for comparison. The authority is `Logistics Support`. Recognized names are `Logistics Support`, `Billing Support`, `Account Support`, `Technical Support`, and generated aliases `Logistics/Billing/Account/Technical team` or `... department`. A name outside this fixed set conflicts.

## 3. Text rules

Inspect only the message field selected by `field_map.json`; never scan other strings in C, O, or D. The confirmed case language is English. Split text into sentences at `.`, `!`, `?`, semicolons, and line breaks; retain the original sentence and JSON path for each hit. Rules use deterministic regex/string matching only.

- **T1 — Priority:** find `P0`–`P4` labels, case-insensitively. A sentence with a label other than P1 hits unless the same sentence also contains P1, which is treated as explicit comparison/context and suppresses T1 for that sentence.
- **T2 — Time commitment:** find a numeric or number-word duration, time unit, and commitment marker in the same sentence. Number words cover `one` through `twenty-four`, including hyphenated or space-separated compound forms. Units include hours (`hour(s)`, `hr(s)`, `h`), minutes (`minute(s)`, `min(s)`, `m`), calendar days (`day(s)`), and business/working days. Commitment markers include `within`, `no later than`, `at most`, `by`, and explicit future-response forms such as `will reply in` or `will respond in`. A duration without a commitment marker does not hit. A business/working-day commitment always differs from the 4-hour SLA; a calendar day converts to 24 hours, and any parsed duration other than 240 minutes hits. Thus `within one business day` and `within 1 day` conflict; `within four hours` does not. If the same sentence also states a 240-minute equivalent, treat it as explicit comparison and suppress T2 for that sentence.
- **T3 — Team routing:** require both a non-authoritative known team name and a routing/responsibility verb in the same sentence. Other teams are Billing, Account, and Technical, each matched as Support, team, or department. English verbs: `handle`, `assign`, `route`, `transfer`, `forward`, `escalate to`. Mentioning a team without one of these verbs does not hit. If the same sentence also mentions the authority team Logistics, treat it as explicit comparison/context and suppress T3 for that sentence.

### Known limitations

- Only explicit statements are detected; implicit contradictions may be missed.
- Negation and quoted text may produce false positives.
- Names outside the fixed team list are not detected.
- Aliases outside `field_map.json` and the generated team-name patterns are treated as unknown/unmatched.
- Sentence splitting and English-only token lists may miss unusual punctuation or wording.

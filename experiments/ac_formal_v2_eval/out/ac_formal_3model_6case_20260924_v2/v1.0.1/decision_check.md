# Decision check (human confirmation required)

Provisional category: **先修 Runtime**

| Condition | Result | Evidence |
|---|---|---|
| ① GPT or Claude has a candidate conflict in CS04/06/08/10 | PASS | Claude CS10 1, Claude CS04 1, Claude CS04 2 |
| ② All three models have zero D leaks, with 18 records per model | PASS | leaks={'DeepSeek': 0, 'GPT': 0, 'Claude': 0}; records={'DeepSeek': 18, 'GPT': 18, 'Claude': 18} |
| ③ Candidate text conflict exists and D has no conflict | PASS | DeepSeek CS08 1, Claude CS10 1, DeepSeek CS10 1, DeepSeek CS04 1, Claude CS04 1, DeepSeek CS04 2, DeepSeek CS10 2, Claude CS04 2, DeepSeek CS08 2, DeepSeek CS04 3, DeepSeek CS08 3, DeepSeek CS10 3 |
| ④ False-reject rate ≤10% per model and overall; no model rejects CS01 ≥2/3 | FAIL | false_reject_rate_percent={'DeepSeek': 0.0, 'GPT': 0.0, 'Claude': 40.0}; total_percent=14.29; CS01 rejects={'DeepSeek': 0, 'GPT': 0, 'Claude': 0}; records={'DeepSeek': 18, 'GPT': 18, 'Claude': 18} |

The decision order follows the preregistered rule: ② or ④ fails → 先修 Runtime; then all models with no candidate conflict → 危险信号; then ① and ③ → GO; then ① fails with DeepSeek candidate conflict → 缩小：便宜模型 + Runtime; then ③ fails → 缩小：字段由系统写入 + trace. Any remaining combination is left for human review.

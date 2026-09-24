# DEVIATIONS

All timestamps below are UTC. This file records input-scope deviations and corrections.

- **2026-09-24 (first reads; exact time was not captured, confirmed no later than 15:07:47 UTC):** previously opened `experiments/baseline_comparison/fixtures/customer_support/customer_support_01.json` and `experiments/baseline_comparison/fixtures/customer_support/customer_support_04.json` in the desktop snapshot. Per the user's latest instruction these are not frozen cases. All authority/request content derived from them and the previous RULES draft are invalidated and must not be used. Required note: **“输入侧 case 文件，未读取模型输出；规则未使用预期类字段。”**
- **2026-09-24 (prior draft):** `data/support_policy.json` was read under the earlier allowed-policy instruction. Its contents are superseded for this version; only `experiments/ac_formal_v2/frozen/support_policy.json` was used in the current RULES.
- **2026-09-24 (current work):** the requested initial `git pull` from `C:\Users\User\Desktop\新新新综合设计` failed because that desktop snapshot has no `.git` metadata and does not contain the frozen input paths. `git ls-remote` identified the corresponding remote main at `06006e2dcc9a76f98931bf25536d481dd5f0f22b`; work continued in the Git checkout `C:\Users\User\Desktop\综合设计检查版\综合设计`, where `git pull --no-rebase origin main` fast-forwarded `82839f2` to frozen commit `06006e2`. Existing untracked documents in that checkout were left untouched and are not staged.
- **Frozen-input verification:** read only `cases_v1.json`, `fixture_hashes_v1.json`, the six named frozen prompt JSON files, and frozen `support_policy.json`. Each prompt's `fixture_hash` matched its corresponding hash-manifest entry. No model output or experiment result was read. No pre-existing `.py` files or files under `src/` or top-level `tests/` were opened; only the new evaluator files inside `experiments/ac_formal_v2_eval/` were inspected, compiled, and tested.

要求的记录说明：**输入侧 case 文件，未读取模型输出；规则未使用预期类字段。**

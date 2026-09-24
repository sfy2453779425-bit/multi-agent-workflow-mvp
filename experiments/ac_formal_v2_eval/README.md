# AC Formal V2 Evaluator

Independent deterministic scoring for the frozen six-case comparison. This evaluator does not call a model or API.

## Run

From the repository root, with Python 3.10+:

```powershell
python experiments/ac_formal_v2_eval/evaluate.py --replay <replay.jsonl> --calls <calls.jsonl>
python experiments/ac_formal_v2_eval/make_tables.py --evaluation experiments/ac_formal_v2_eval/out/<EXPERIMENT_ID>/evaluation.jsonl --calls <calls.jsonl> --experiment-id <EXPERIMENT_ID>
```

`evaluate.py` writes `evaluation.jsonl` under `experiments/ac_formal_v2_eval/out/<EXPERIMENT_ID>/` by default. `--output` can select another path. `make_tables.py` writes CSV and Markdown tables to the same experiment output folder; `--out-root` can override the root.

## Outputs

- `evaluation.jsonl`: one joined replay/call row with C (candidate), O (field-only repair), and D (runtime final output) scores, snippets, evaluator version, and input-file SHA-256 values.
- Table 1: model × case, parse success, unauthorized-output presence, authority-field conflicts, and text conflicts.
- Table 2: model rows for C/O/D/F, runtime effects, D fallback rate, D outcome categories, and false-reject rate. C/O fallback rate is N/A because those views are not runtime decisions; F is the fixed all-fallback comparison.
- Table 3: call metadata, prompt-hash equality across models, DeepSeek live/replay agreement, and runtime/validator/evaluator versions.
- `appendix_hits.md`: exact matched text snippets and out-of-alias authority field names.
- `decision_check.md`: the four preregistered decision conditions and resulting category, for human confirmation.

## Tests

The self-contained tests use English hand-written examples and clearly marked synthetic JSONL fixtures only. They do not read live/model outputs. Run:

```powershell
python -m unittest discover -s experiments/ac_formal_v2_eval -p "test_*.py" -v
```

See `RULES.md` for the frozen authorities, normalization, detector boundaries, and known limitations. `DEVIATIONS.md` records scope notes and the earlier non-frozen pilot files that were invalidated.

# Evaluation Methodology Note

## Parser correction

The first analysis version was `evaluation-v1`. During review, an Evaluation Parser defect was found in the Outfit parser: any known inventory ID mentioned in a response could be treated as a selected recommendation. This incorrectly included items that the response explicitly excluded or only described.

The raw ChatGPT responses were not edited, regenerated, or re-collected. Prompt files, fixtures, Builder v2, templates, Workflow Runtime, and business policy data were not changed.

The parser was corrected to separate:

- selected or recommended items
- excluded or rejected items
- ordinary inventory mentions
- ambiguous cases when the disposition cannot be determined safely

The full 30 raw ChatGPT records were reanalyzed as `evaluation-v2`.

## Effect on the pilot measurements

The measured change was:

```text
Constraint satisfaction: 27/30 → 30/30
Completeness: 22/30 → 23/30
Required fields: 23/30 → 23/30
Structured repeatability: 7/10 → 7/10
```

The change comes from correcting the measurement logic. It does not mean that a ChatGPT response was regenerated or improved after the fact.

The official results for the current pilot are the `evaluation-v2` results. `evaluation-v1` is retained as a historical snapshot for audit and comparison.

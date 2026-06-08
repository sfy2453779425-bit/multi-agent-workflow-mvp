import argparse
import csv
import json
import random
from pathlib import Path


MODEL_LABELS = {
    "base": "Base",
    "workflow_builder": "Old LoRA",
    "workflow_builder_v2": "New LoRA v2",
}


def infer_model_label(record: dict) -> str:
    if record.get("mode") == "base":
        return "Base"
    adapter = record.get("adapter", "")
    if "workflow_builder_v2" in adapter:
        return "New LoRA v2"
    if "workflow_builder" in adapter:
        return "Old LoRA"
    return "LoRA"


def load_rows(input_dir: Path) -> list[dict]:
    rows = []
    for path in sorted(input_dir.glob("compare_*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        label = infer_model_label(record)
        for item in record.get("rows", []):
            rows.append(
                {
                    "prompt_id": item["id"],
                    "category": item["category"],
                    "language": item.get("language", ""),
                    "model_label": label,
                    "prompt": item["prompt"],
                    "answer": item["answer"],
                    "keyword_score": item.get("keyword_score", ""),
                    "token_per_second": item.get("token_per_second", ""),
                    "latency_seconds": item.get("infer_seconds", ""),
                    "source_file": str(path),
                }
            )
    if not rows:
        raise FileNotFoundError(f"No compare_*.json files found in {input_dir}")
    return rows


def write_blind_eval(rows: list[dict], output: Path, seed: int) -> None:
    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "eval_id",
        "prompt_id",
        "category",
        "language",
        "prompt",
        "answer",
        "structure_score_1_5",
        "domain_fit_score_1_5",
        "usefulness_score_1_5",
        "traceability_score_1_5",
        "language_quality_score_1_5",
        "overall_score_1_5",
        "reviewer_comment",
    ]
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for index, row in enumerate(shuffled, start=1):
            writer.writerow(
                {
                    "eval_id": f"E{index:03d}",
                    "prompt_id": row["prompt_id"],
                    "category": row["category"],
                    "language": row["language"],
                    "prompt": row["prompt"],
                    "answer": row["answer"],
                    "structure_score_1_5": "",
                    "domain_fit_score_1_5": "",
                    "usefulness_score_1_5": "",
                    "traceability_score_1_5": "",
                    "language_quality_score_1_5": "",
                    "overall_score_1_5": "",
                    "reviewer_comment": "",
                }
            )


def write_mapping(rows: list[dict], output: Path, seed: int) -> None:
    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "eval_id",
        "prompt_id",
        "model_label",
        "keyword_score",
        "token_per_second",
        "latency_seconds",
        "source_file",
    ]
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for index, row in enumerate(shuffled, start=1):
            writer.writerow(
                {
                    "eval_id": f"E{index:03d}",
                    "prompt_id": row["prompt_id"],
                    "model_label": row["model_label"],
                    "keyword_score": row["keyword_score"],
                    "token_per_second": row["token_per_second"],
                    "latency_seconds": row["latency_seconds"],
                    "source_file": row["source_file"],
                }
            )


def write_rubric(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        """# Manual Evaluation Rubric

## Purpose

This rubric evaluates generated answers from Base, Old LoRA, and New LoRA v2.
Keyword score is automatic and coarse. Manual scores check whether the answer is actually useful for the Workflow Builder project.

## Scoring Scale

Use 1 to 5.

```text
1 = unusable or mostly wrong
2 = partially related but weak
3 = acceptable but incomplete
4 = good and mostly complete
5 = excellent, clear, structured, and directly usable
```

## Criteria

| Criterion | What to Check |
|---|---|
| Structure | Does the answer follow the requested structure, such as nodes, ranking, bullets, or input/output format? |
| Domain Fit | Does the answer use Workflow Builder / Template / Node / Trace concepts correctly? |
| Usefulness | Could the answer be used in our report, demo, or system design without major rewriting? |
| Traceability | Does the answer make execution steps, data sources, or reasoning inspectable? |
| Language Quality | Is Korean/Chinese/English expression natural enough for presentation or report use? |
| Overall | Overall quality for this project context. |

## Reviewer Rule

Do not compare model names while scoring. Use `manual_eval_blind.csv` only.
After scoring is finished, use `manual_eval_mapping.csv` to reveal which answer came from which model.
""",
        encoding="utf-8",
    )


def write_summary_template(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        """# Manual Evaluation Result Template

## Setup

- Evaluators:
- Prompt count:
- Model candidates:
  - Base
  - Old LoRA
  - New LoRA v2
- Scoring range: 1-5

## Result Table

| Model | Structure | Domain Fit | Usefulness | Traceability | Language Quality | Overall |
|---|---:|---:|---:|---:|---:|---:|
| Base | | | | | | |
| Old LoRA | | | | | | |
| New LoRA v2 | | | | | | |

## Interpretation

```text
Write whether New LoRA v2 improved not only keyword score but also human-perceived answer quality.
```

## PPT Sentence

```text
자동 keyword score 외에도 수동 평가를 통해 구조성, 도메인 적합성, 활용 가능성, Trace 설명력, 언어 품질을 비교했다.
```
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Create manual evaluation files from Base/LoRA comparison outputs.")
    parser.add_argument("--input-dir", default="gpu_v2_lora_results")
    parser.add_argument("--output-dir", default="outputs/manual_eval_v2")
    parser.add_argument("--seed", type=int, default=20260605)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    rows = load_rows(input_dir)
    write_blind_eval(rows, output_dir / "manual_eval_blind.csv", args.seed)
    write_mapping(rows, output_dir / "manual_eval_mapping.csv", args.seed)
    write_rubric(output_dir / "manual_eval_rubric.md")
    write_summary_template(output_dir / "manual_eval_result_template.md")
    print(f"Loaded rows: {len(rows)}")
    print(f"Saved: {output_dir / 'manual_eval_blind.csv'}")
    print(f"Saved: {output_dir / 'manual_eval_mapping.csv'}")
    print(f"Saved: {output_dir / 'manual_eval_rubric.md'}")
    print(f"Saved: {output_dir / 'manual_eval_result_template.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

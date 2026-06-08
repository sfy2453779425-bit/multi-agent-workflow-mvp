import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean


SCORE_FIELDS = [
    "structure_score_1_5",
    "domain_fit_score_1_5",
    "usefulness_score_1_5",
    "traceability_score_1_5",
    "language_quality_score_1_5",
    "overall_score_1_5",
]


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def parse_score(value: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        score = float(value)
    except ValueError:
        return None
    if score < 1 or score > 5:
        return None
    return score


def write_summary(scored_rows: list[dict], mapping_rows: list[dict], output: Path) -> None:
    mapping = {row["eval_id"]: row for row in mapping_rows}
    grouped: dict[str, list[dict]] = defaultdict(list)
    missing = []
    for row in scored_rows:
        eval_id = row["eval_id"]
        mapped = mapping.get(eval_id)
        if not mapped:
            missing.append(eval_id)
            continue
        merged = dict(row)
        merged.update(mapped)
        grouped[mapped["model_label"]].append(merged)

    lines = [
        "# Manual Evaluation Summary",
        "",
        "## Model Average Scores",
        "",
        "| Model | Count | Structure | Domain Fit | Usefulness | Traceability | Language Quality | Overall |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model_label in sorted(grouped):
        rows = grouped[model_label]
        values = []
        for field in SCORE_FIELDS:
            scores = [parse_score(row.get(field, "")) for row in rows]
            scores = [score for score in scores if score is not None]
            values.append(round(mean(scores), 3) if scores else "")
        lines.append(
            f"| {model_label} | {len(rows)} | "
            f"{values[0]} | {values[1]} | {values[2]} | {values[3]} | {values[4]} | {values[5]} |"
        )

    lines.extend(["", "## Prompt-Level Overall Scores", ""])
    lines.append("| Prompt ID | Model | Overall | Comment |")
    lines.append("|---|---|---:|---|")
    for model_label in sorted(grouped):
        for row in grouped[model_label]:
            overall = parse_score(row.get("overall_score_1_5", ""))
            comment = (row.get("reviewer_comment", "") or "").replace("|", "/")
            lines.append(f"| {row['prompt_id']} | {model_label} | {overall if overall is not None else ''} | {comment} |")

    if missing:
        lines.extend(["", "## Missing Mapping Rows", "", ", ".join(missing)])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize manual evaluation scores by model.")
    parser.add_argument("--scores", default="outputs/manual_eval_v2/manual_eval_blind.csv")
    parser.add_argument("--mapping", default="outputs/manual_eval_v2/manual_eval_mapping.csv")
    parser.add_argument("--output", default="outputs/manual_eval_v2/manual_eval_summary.md")
    args = parser.parse_args()

    scored_rows = read_csv(Path(args.scores))
    mapping_rows = read_csv(Path(args.mapping))
    write_summary(scored_rows, mapping_rows, Path(args.output))
    print(f"Saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

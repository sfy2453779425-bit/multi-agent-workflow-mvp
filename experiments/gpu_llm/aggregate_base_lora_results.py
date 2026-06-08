import argparse
import json
from pathlib import Path
from statistics import mean


def load_records(input_dir: Path) -> list[dict]:
    records = []
    for path in sorted(input_dir.glob("compare_*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            record["_path"] = str(path)
            records.append(record)
        except Exception as exc:
            print(f"Skip {path}: {exc}")
    return records


def key_for(record: dict) -> str:
    if record.get("mode") == "lora":
        adapter = record.get("adapter") or ""
        adapter_name = Path(adapter).parent.name or Path(adapter).name or "lora"
        return f"{record.get('model')} + {adapter_name}"
    return f"{record.get('model')} base"


def build_prompt_comparison(records: list[dict]) -> dict[str, dict[str, dict]]:
    comparison: dict[str, dict[str, dict]] = {}
    for record in records:
        label = key_for(record)
        for row in record.get("rows", []):
            comparison.setdefault(row["id"], {})[label] = row
    return comparison


def write_summary(records: list[dict], path: Path) -> None:
    lines = [
        "# Base vs LoRA Evaluation Summary",
        "",
        "## Model-Level Summary",
        "",
        "| Run | Mode | Load(s) | Avg latency(s) | Avg token/s | Avg peak MB | Avg keyword score | Source |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for record in records:
        summary = record.get("summary", {})
        lines.append(
            f"| {key_for(record)} | {record.get('mode')} | {record.get('load_seconds')} | "
            f"{summary.get('avg_infer_seconds')} | {summary.get('avg_token_per_second')} | "
            f"{summary.get('avg_peak_torch_allocated_mb')} | {summary.get('avg_keyword_score')} | "
            f"`{record.get('_path')}` |"
        )

    lines.extend(["", "## Prompt-Level Keyword Score Comparison", ""])
    comparison = build_prompt_comparison(records)
    labels = sorted({key_for(record) for record in records})
    lines.append("| Prompt ID | " + " | ".join(labels) + " |")
    lines.append("|---" + "|---:" * len(labels) + "|")
    for prompt_id, per_model in comparison.items():
        values = []
        for label in labels:
            row = per_model.get(label)
            values.append(str(row.get("keyword_score", "")) if row else "")
        lines.append(f"| {prompt_id} | " + " | ".join(values) + " |")

    if records:
        avg_keyword = mean(record.get("summary", {}).get("avg_keyword_score", 0) for record in records)
        avg_tps = mean(record.get("summary", {}).get("avg_token_per_second", 0) for record in records)
    else:
        avg_keyword = 0
        avg_tps = 0
    lines.extend(
        [
            "",
            "## PPT-Ready Conclusion",
            "",
            (
                f"Fixed workflow-builder prompts were used to compare local Qwen base models and LoRA adapters. "
                f"The aggregated average keyword score across available runs is {avg_keyword:.3f}, "
                f"and the average generation speed is {avg_tps:.3f} token/s. "
                "These results provide technical evidence that a Local LLM Node can be evaluated inside the same Workflow Builder scenario."
            ),
            "",
            "## Usage in Next Semester",
            "",
            "- Use this report as technical evidence for professor-side evaluation.",
            "- Use prompt-level outputs to decide whether LoRA improves workflow/node terminology.",
            "- Keep raw JSON files for paper tables and appendix material.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate Base vs LoRA comparison JSON files.")
    parser.add_argument("--input-dir", default="results/base_lora_comparison")
    parser.add_argument("--output", default="results/base_lora_comparison/base_lora_summary.md")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    records = load_records(input_dir)
    if not records:
        print(f"No compare_*.json files found in {input_dir}")
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_summary(records, output)
    print(f"Saved summary: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

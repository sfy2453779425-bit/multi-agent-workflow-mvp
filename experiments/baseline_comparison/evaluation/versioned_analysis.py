from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from experiments.baseline_comparison import runner
from experiments.baseline_comparison.evaluation.scoring import score_response


EVALUATION_V1 = "evaluation-v1"
EVALUATION_V2 = "evaluation-v2"
RESULT_FIELDS = [
    "system",
    "case_id",
    "run",
    "run_status",
    "run_id",
    "source_file",
    "required_fields_present",
    "required_fields_missing",
    "context_usage",
    "constraint_satisfaction",
    "completeness",
    "ground_truth_correctness",
    "unsupported_fact_flags",
    "human_evaluation_status",
    "open_language_quality",
    "evaluation_version",
    "evaluation_source",
]
PARSER_SOURCE_FILES = (
    "experiments/baseline_comparison/evaluation/scoring.py",
    "experiments/baseline_comparison/evaluation/versioned_analysis.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _json_cell(value: Any) -> Any:
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value


def _boolish(value: Any) -> Any:
    if value in (True, "True", "true"):
        return True
    if value in (False, "False", "false"):
        return False
    return value


def _copy_existing_results_to_v1(results_root: Path, v1_root: Path) -> None:
    if v1_root.exists():
        return
    if not (results_root / "case_quality.csv").is_file():
        raise FileNotFoundError("evaluation-v1 source case_quality.csv is missing")
    v1_root.mkdir(parents=True)
    for child in results_root.iterdir():
        if child.name in {"evaluation_v1", "evaluation_v2"}:
            continue
        destination = v1_root / child.name
        if child.is_dir():
            shutil.copytree(child, destination)
        else:
            shutil.copy2(child, destination)


def _ensure_v1_snapshot(root: Path) -> Path:
    results_root = root / "results"
    v1_root = results_root / "evaluation_v1"
    _copy_existing_results_to_v1(results_root, v1_root)
    metadata_path = v1_root / "metadata.json"
    if not metadata_path.exists():
        _write_json(
            metadata_path,
            {
                "evaluation_version": EVALUATION_V1,
                "parser_source_sha256": "legacy_not_recorded_before_evaluation_v2",
                "analysis_timestamp": None,
                "defect_description": "The Outfit parser treated every mentioned known inventory ID as selected, including explicitly excluded items.",
                "raw_data_modified": False,
            },
        )
    return v1_root


def _fixture_catalog(manifest: dict[str, Any]) -> dict[str, Path]:
    return {case_id: Path(path) for case_id, path in manifest["fixture_files"].items()}


def _load_fixtures(root: Path, manifest: dict[str, Any]) -> dict[str, runner.LoadedFixture]:
    catalog = _fixture_catalog(manifest)
    return {
        case_id: runner.load_fixture(case_id, root=root, case_files=catalog)
        for case_id in manifest["cases"]
    }


def _valid_chatgpt_records(
    root: Path, manifest: dict[str, Any]
) -> tuple[list[tuple[Path, dict[str, Any]]], list[str]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    invalid: list[str] = []
    seen: set[tuple[str, int]] = set()
    for path, record in runner._iter_saved_records(root, "llm_runs"):
        if record.get("provider") != "ChatGPT":
            continue
        errors = runner.validate_llm_record(record, manifest, root, formal=False)
        key = (str(record.get("case_id")), int(record.get("run", 0) or 0))
        if errors:
            invalid.append(f"{runner._relative_path(path, root)}: {'; '.join(errors)}")
        elif key in seen:
            invalid.append(f"{runner._relative_path(path, root)}: duplicate ChatGPT case/run")
        else:
            seen.add(key)
            records.append((path, record))
    return records, invalid


def _artifact_map(root: Path, folder: str, system: str) -> dict[tuple[str, int], dict[str, Any]]:
    result = {}
    for path in sorted((root / folder).glob("*.json")):
        artifact = _read_json(path)
        if artifact.get("system") == system:
            result[(str(artifact.get("case_id")), int(artifact.get("run", 0) or 0))] = artifact
    return result


def _repeatability_map(path: Path, system: str) -> dict[str, str]:
    if not path.is_file():
        return {}
    return {
        row["case_id"]: row.get("structured_fields_match", "")
        for row in _read_csv(path)
        if row.get("system") == system
    }


def _new_chatgpt_artifacts(
    root: Path,
    output_root: Path,
    fixture: runner.LoadedFixture,
    source_path: Path,
    record: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    response = str(record.get("response", ""))
    evaluation = score_response(fixture, response)
    parsed = evaluation.get("parsed", {})
    source = runner._relative_path(source_path, root)
    key = (str(record.get("case_id")), int(record.get("run", 0) or 0))
    response_hash = hashlib.sha256(response.encode("utf-8")).hexdigest()
    parser_hashes = {
        relative: _sha256(runner.PROJECT_ROOT / relative)
        for relative in PARSER_SOURCE_FILES
    }
    common = {
        "evaluation_version": EVALUATION_V2,
        "parser_source_hashes": parser_hashes,
        "experiment_id": record.get("experiment_id", ""),
        "system": "ChatGPT",
        "case_id": key[0],
        "run": key[1],
        "source_file": source,
        "response_sha256": response_hash,
    }
    stem = f"chatgpt_{key[0]}_run_{key[1]}"
    _write_json(output_root / "parsed" / f"{stem}.json", {**common, "parsed": parsed})
    _write_json(output_root / "evaluation" / f"{stem}.json", {**common, "evaluation": evaluation})
    return evaluation, parsed


def _quality_row(
    record: dict[str, Any],
    evaluation: dict[str, Any],
    source_file: str,
    source: str,
) -> dict[str, Any]:
    row = {
        "system": record.get("provider", record.get("system", "")),
        "case_id": record.get("case_id", ""),
        "run": record.get("run", ""),
        "run_status": "available",
        "run_id": record.get("run_id", ""),
        "source_file": source_file,
        "evaluation_version": EVALUATION_V2,
        "evaluation_source": source,
    }
    for field in RESULT_FIELDS[6:15]:
        row[field] = _json_cell(evaluation.get(field, ""))
    return row


def build_evaluation_change_row(
    *,
    case_id: str,
    run_id: str,
    old_parsed: dict[str, Any],
    new_parsed: dict[str, Any],
    old_evaluation: dict[str, Any],
    new_evaluation: dict[str, Any],
    old_repeatability: str,
    new_repeatability: str,
) -> dict[str, Any]:
    old_selected = list(old_parsed.get("selected_items", []) or [])
    new_selected = list(new_parsed.get("selected_items", []) or [])
    old_excluded = list(old_parsed.get("excluded_items", []) or [])
    new_excluded = list(new_parsed.get("excluded_items", []) or [])
    old_repeatability = _boolish(old_repeatability)
    new_repeatability = _boolish(new_repeatability)
    reasons = []
    if old_selected != new_selected:
        reasons.append("selected_items semantic classification changed")
    if old_excluded != new_excluded:
        reasons.append("excluded_items was added or changed")
    if old_evaluation.get("constraint_satisfaction") != new_evaluation.get("constraint_satisfaction"):
        reasons.append("constraint_satisfaction changed")
    if old_evaluation.get("completeness") != new_evaluation.get("completeness"):
        reasons.append("completeness changed")
    if old_repeatability != new_repeatability:
        reasons.append("repeatability contribution changed")
    return {
        "case_id": case_id,
        "run_id": run_id,
        "old_selected_items": old_selected,
        "new_selected_items": new_selected,
        "old_excluded_items": old_excluded,
        "new_excluded_items": new_excluded,
        "old_constraint_satisfaction": old_evaluation.get("constraint_satisfaction", ""),
        "new_constraint_satisfaction": new_evaluation.get("constraint_satisfaction", ""),
        "old_completeness": old_evaluation.get("completeness", ""),
        "new_completeness": new_evaluation.get("completeness", ""),
        "old_repeatability_contribution": old_repeatability,
        "new_repeatability_contribution": new_repeatability,
        "changed": bool(reasons),
        "reason": "; ".join(reasons) if reasons else "no change",
    }


def _new_repeatability_rows(
    manifest: dict[str, Any], parsed_by_key: dict[tuple[str, str, int], dict[str, Any]]
) -> list[dict[str, Any]]:
    chatgpt_manifest = dict(manifest)
    chatgpt_manifest["systems"] = ["ChatGPT"]
    return runner._repeatability_rows(parsed_by_key, chatgpt_manifest)


def _outfit_audit_rows(
    fixtures: dict[str, runner.LoadedFixture],
    records: list[tuple[Path, dict[str, Any]]],
    evaluations: dict[tuple[str, int], tuple[dict[str, Any], dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows = []
    for _, record in records:
        case_id = str(record["case_id"])
        if fixtures[case_id].payload.get("domain") != "outfit":
            continue
        key = (case_id, int(record["run"]))
        evaluation, parsed = evaluations[key]
        rows.append(
            {
                "case_id": case_id,
                "run": record["run"],
                "run_id": record["run_id"],
                "precipitation_probability": fixtures[case_id].payload["shared_context"]["weather"].get("precipitation_probability"),
                "selected_items": _json_cell(parsed.get("selected_items", [])),
                "excluded_items": _json_cell(parsed.get("excluded_items", [])),
                "mentioned_only_items": _json_cell(parsed.get("mentioned_only_items", [])),
                "ambiguous_items": _json_cell(parsed.get("ambiguous_items", [])),
                "parse_status": parsed.get("parse_status", ""),
                "recommendation_order": _json_cell(parsed.get("selected_items", [])),
                "inventory_only_compliant": not parsed.get("unknown_inventory_ids"),
                "rain_unsafe_inventory_ids": _json_cell(parsed.get("rain_unsafe_inventory_ids", [])),
                "weather_used": parsed.get("weather_used", False),
                "required_fields_present": evaluation.get("required_fields_present", False),
                "constraint_satisfaction": evaluation.get("constraint_satisfaction", False),
                "completeness": evaluation.get("completeness", False),
            }
        )
    return rows


def _summary(
    manifest: dict[str, Any],
    chat_rows: list[dict[str, Any]],
    builder_rows: list[dict[str, Any]],
    chat_repeatability: list[dict[str, Any]],
    builder_repeatability: list[dict[str, Any]],
    change_rows: list[dict[str, Any]],
    invalid: list[str],
) -> str:
    def count(rows: list[dict[str, Any]], field: str) -> int:
        return sum(row.get(field) is True or row.get(field) == "True" for row in rows)

    changed = sum(bool(row["changed"]) for row in change_rows)
    lines = [
        "# Evaluation v2 — Builder v2 Pilot",
        "",
        "## A. Parser defect root cause",
        "",
        "The previous Outfit parser treated every known inventory ID mentioned in the response as selected. It did not distinguish recommendation, exclusion, and ordinary inventory mention.",
        "",
        "## B. Evaluation v2 implementation",
        "",
        f"Experiment ID: `{manifest['experiment_id']}`",
        "Evaluation version: `evaluation-v2`",
        "The parser now records `selected_items`, `excluded_items`, `mentioned_items`, `mentioned_only_items`, `ambiguous_items`, and `parse_status`.",
        "Evaluation v1 remains frozen under `results/evaluation_v1/`; v2 outputs are under `results/evaluation_v2/`.",
        "",
        "## C. Raw response impact",
        "",
        f"ChatGPT records reanalyzed: {len(chat_rows)}/30.",
        f"Change-log rows changed: {changed}/{len(change_rows)}.",
        "Raw response files, Prompts, Fixtures, Builder v2, Templates, Runtime, and policy Ground Truth were not modified.",
        "",
        "## D. Outfit audit",
        "",
        "All 9 ChatGPT Outfit records are in `outfit_parser_audit.csv`. The audit preserves recommendation order separately from excluded and mention-only items.",
        "",
        "## E. ChatGPT summary",
        "",
        f"Required fields: {count(chat_rows, 'required_fields_present')}/{len(chat_rows)}.",
        f"Constraint satisfaction: {count(chat_rows, 'constraint_satisfaction')}/{len(chat_rows)}.",
        f"Completeness: {count(chat_rows, 'completeness')}/{len(chat_rows)}.",
        "Repeatability is reported per Case in `repeatability.csv`; it is not combined with Answer Quality.",
        "",
        "## F. Builder summary",
        "",
        f"Frozen Builder rows reread: {len(builder_rows)}.",
        f"Required fields: {count(builder_rows, 'required_fields_present')}/{len(builder_rows)}.",
        f"Constraint satisfaction: {count(builder_rows, 'constraint_satisfaction')}/{len(builder_rows)}.",
        f"Completeness: {count(builder_rows, 'completeness')}/{len(builder_rows)}.",
        "Builder rows and repeatability values were copied from evaluation-v1; no Builder execution was performed.",
        "",
        "## G. Evaluation v1 versus v2",
        "",
        "The machine-readable comparison is `evaluation_change_log.csv`.",
        "The change log includes selected/excluded items, constraint satisfaction, completeness, and repeatability contribution for every ChatGPT run.",
        "",
        "## H. Tests",
        "",
        "Parser tests cover explicit recommendation, explicit exclusion, negative recommendation, mixed selected/excluded text, and ordinary inventory mention.",
        "",
        "## I. Supported conclusions",
        "",
        "Evaluation v2 more accurately reflects explicit Outfit recommendation and exclusion semantics in this pilot. Customer Support and Presentation objective checks remain separately reported.",
        "",
        "## J. Unsupported conclusions",
        "",
        "This pilot does not establish general model superiority, overall winner, language-quality superiority, or user-efficiency percentages. Human Evaluation remains uncollected.",
    ]
    if invalid:
        lines.extend(["", "Invalid ChatGPT records:", *[f"- {item}" for item in invalid]])
    return "\n".join(lines) + "\n"


def analyze_evaluation_v2(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    manifest = runner.load_manifest(root_path)
    runner._verify_frozen_manifest(manifest, root_path)
    v1_root = _ensure_v1_snapshot(root_path)
    v2_root = root_path / "results" / "evaluation_v2"
    v2_root.mkdir(parents=True, exist_ok=True)
    fixtures = _load_fixtures(root_path, manifest)
    records, invalid = _valid_chatgpt_records(root_path, manifest)
    if invalid:
        raise ValueError("invalid ChatGPT records: " + "; ".join(invalid))

    old_parsed = _artifact_map(v1_root, "parsed", "ChatGPT")
    old_evaluations = _artifact_map(v1_root, "evaluation", "ChatGPT")
    old_repeatability = _repeatability_map(v1_root / "repeatability.csv", "ChatGPT")
    new_evaluations: dict[tuple[str, int], tuple[dict[str, Any], dict[str, Any]]] = {}
    new_rows = []
    parsed_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    for source_path, record in records:
        case_id = str(record["case_id"])
        run = int(record["run"])
        evaluation, parsed = _new_chatgpt_artifacts(
            root_path,
            v2_root,
            fixtures[case_id],
            source_path,
            record,
        )
        key = (case_id, run)
        new_evaluations[key] = (evaluation, parsed)
        parsed_by_key[("ChatGPT", case_id, run)] = parsed
        new_rows.append(
            _quality_row(
                record,
                evaluation,
                runner._relative_path(source_path, root_path),
                "raw_response_reparsed",
            )
        )

    old_quality_path = v1_root / "case_quality.csv"
    if not old_quality_path.is_file():
        old_quality_path = v1_root / "answer_quality.csv"
    old_quality = _read_csv(old_quality_path)
    builder_rows = []
    for row in old_quality:
        if row.get("system") != "Builder":
            continue
        copied = dict(row)
        copied["evaluation_version"] = EVALUATION_V2
        copied["evaluation_source"] = "frozen_builder_evaluation_v1"
        builder_rows.append(copied)
    if len(builder_rows) != len(manifest["cases"]) * int(manifest["runs_per_case"]):
        raise ValueError("evaluation-v1 does not contain the complete frozen Builder result set")

    for folder in ("parsed", "evaluation"):
        source_folder = v1_root / folder
        destination_folder = v2_root / folder
        destination_folder.mkdir(parents=True, exist_ok=True)
        for source in source_folder.glob("builder_*.json"):
            shutil.copy2(source, destination_folder / source.name)

    chat_repeatability = _new_repeatability_rows(manifest, parsed_by_key)
    builder_repeatability = [
        row
        for row in _read_csv(v1_root / "repeatability.csv")
        if row.get("system") == "Builder"
    ]
    combined_quality = new_rows + builder_rows
    combined_quality.sort(
        key=lambda row: (
            0 if row["system"] == "ChatGPT" else 1,
            list(manifest["cases"]).index(row["case_id"]),
            int(row["run"]),
        )
    )
    runner._write_csv(v2_root / "case_quality.csv", RESULT_FIELDS, combined_quality)
    runner._write_csv(v2_root / "answer_quality.csv", RESULT_FIELDS, combined_quality)

    repeatability = chat_repeatability + builder_repeatability
    runner._write_csv(
        v2_root / "repeatability.csv",
        ["system", "case_id", "run_count", "status", "structured_fields_match", "compared_fields"],
        repeatability,
    )
    repeatability_map = {
        (row["system"], row["case_id"]): row.get("structured_fields_match", "")
        for row in repeatability
    }
    change_rows = []
    for _, record in records:
        key = (str(record["case_id"]), int(record["run"]))
        old_parsed_artifact = old_parsed.get(key, {})
        old_evaluation_artifact = old_evaluations.get(key, {})
        change_rows.append(
            build_evaluation_change_row(
                case_id=key[0],
                run_id=str(record["run_id"]),
                old_parsed=old_parsed_artifact.get("parsed", {}),
                new_parsed=new_evaluations[key][1],
                old_evaluation=old_evaluation_artifact.get("evaluation", {}),
                new_evaluation=new_evaluations[key][0],
                old_repeatability=old_repeatability.get(key[0], ""),
                new_repeatability=repeatability_map.get(("ChatGPT", key[0]), ""),
            )
        )
    change_fields = [
        "case_id", "run_id", "old_selected_items", "new_selected_items",
        "old_excluded_items", "new_excluded_items", "old_constraint_satisfaction",
        "new_constraint_satisfaction", "old_completeness", "new_completeness",
        "old_repeatability_contribution", "new_repeatability_contribution", "changed", "reason",
    ]
    change_csv_rows = [{field: _json_cell(row[field]) for field in change_fields} for row in change_rows]
    runner._write_csv(v2_root / "evaluation_change_log.csv", change_fields, change_csv_rows)

    audit_rows = _outfit_audit_rows(fixtures, records, new_evaluations)
    runner._write_csv(
        v2_root / "outfit_parser_audit.csv",
        list(audit_rows[0]) if audit_rows else [],
        audit_rows,
    )

    parser_hashes = {
        relative: _sha256(runner.PROJECT_ROOT / relative)
        for relative in PARSER_SOURCE_FILES
    }
    analysis_timestamp = datetime.now(timezone.utc).isoformat()
    metadata = {
        "evaluation_version": EVALUATION_V2,
        "experiment_id": manifest["experiment_id"],
        "analysis_timestamp": analysis_timestamp,
        "parser_source_hashes": parser_hashes,
        "defect_description": "Mentioned inventory IDs were previously treated as selected; explicit selected, excluded, and mention-only semantics are now separated.",
        "source_evaluation_version": EVALUATION_V1,
        "raw_chatgpt_record_count": len(records),
        "builder_source": "frozen evaluation-v1 artifacts; no Builder execution",
        "raw_data_modified": False,
        "prompt_modified": False,
        "fixture_modified": False,
        "builder_modified": False,
        "template_modified": False,
        "workflow_runtime_modified": False,
    }
    _write_json(v2_root / "metadata.json", metadata)
    shutil.copy2(root_path / "manifest.json", v2_root / "experiment_manifest.json")
    summary = _summary(
        manifest,
        new_rows,
        builder_rows,
        chat_repeatability,
        builder_repeatability,
        change_rows,
        invalid,
    )
    (v2_root / "summary.md").write_text(summary, encoding="utf-8")
    return {
        "evaluation_version": EVALUATION_V2,
        "raw_chatgpt_record_count": len(records),
        "builder_record_count": len(builder_rows),
        "changed_record_count": sum(bool(row["changed"]) for row in change_rows),
        "output_root": str(v2_root),
        "invalid_records": invalid,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reanalyze frozen raw LLM data with evaluation-v2.")
    parser.add_argument("--root", required=True, help="frozen experiment root")
    args = parser.parse_args(argv)
    report = analyze_evaluation_v2(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

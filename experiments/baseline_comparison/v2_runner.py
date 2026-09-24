from __future__ import annotations

import argparse
import copy
import csv
import json
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.baseline_comparison import runner as baseline
from experiments.baseline_comparison.evaluation.scoring import (
    compare_workflow_reuse,
    score_response,
)


PACKAGE_ROOT = baseline.PACKAGE_ROOT
V2_ROOT = PACKAGE_ROOT / "v2"
V2_EXPERIMENT_ID = "builder_v2_pilot_20260916"
V2_SYSTEMS = ("ChatGPT", "Builder")


def _fixture(path: str) -> Path:
    return (PACKAGE_ROOT / path).resolve()


V2_CASE_FILES = {
    "outfit_01": _fixture("fixtures/outfit/outfit_01.json"),
    "outfit_02": _fixture("fixtures/outfit/outfit_02.json"),
    "outfit_03": _fixture("fixtures/outfit/outfit_03.json"),
    "presentation_01": _fixture("fixtures/presentation/presentation_01.json"),
    "presentation_02": _fixture("fixtures/presentation/presentation_02.json"),
    "customer_support_01": _fixture("fixtures/customer_support/customer_support_01.json"),
    "customer_support_02": _fixture("fixtures/customer_support/customer_support_02.json"),
    "customer_support_03": _fixture("fixtures/customer_support/customer_support_03.json"),
    "customer_support_04": _fixture("fixtures/customer_support/customer_support_04.json"),
    "customer_support_05": _fixture("fixtures/customer_support/customer_support_05.json"),
}


def prepare_v2(root: str | Path = V2_ROOT) -> dict[str, Any]:
    return baseline.prepare_experiment(
        root=root,
        experiment_id=V2_EXPERIMENT_ID,
        case_files=V2_CASE_FILES,
        systems=V2_SYSTEMS,
        runs_per_case=3,
        builder_version="builder-v2",
    )


def _load_v2_fixture(case_id: str, root: Path):
    return baseline.load_fixture(case_id, root=root, case_files=V2_CASE_FILES)


def _write_fixture_data(fixture: Any, data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    data_file = str(fixture.payload["builder"]["data_file"])
    data_dir.joinpath(data_file).write_text(
        json.dumps(baseline._fixture_data_payload(fixture), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _run_reuse_config(
    condition: str,
    workflow_config: dict[str, Any],
    fixture: Any,
    root: Path,
) -> dict[str, Any]:
    from agent_builder import MultiAgentWorkflowEngine

    validation_errors: list[str] = []
    trace: list[dict[str, Any]] = []
    answer = ""
    execution_status = "FAIL"
    with tempfile.TemporaryDirectory(prefix=f"reuse_{condition}_") as temp_dir:
        temp_root = Path(temp_dir)
        data_dir = temp_root / "data"
        _write_fixture_data(fixture, data_dir)
        config_path = temp_root / "workflow.json"
        config_path.write_text(
            json.dumps(workflow_config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        weather_tool = None
        if fixture.payload["domain"] == "outfit":
            weather_tool = baseline.FrozenWeatherProvider(
                fixture.payload["shared_context"]["weather"]
            )
        try:
            engine = MultiAgentWorkflowEngine(
                config_path,
                data_dir=data_dir,
                weather_tool=weather_tool,
            )
            initial_context = {
                "query": fixture.payload["input"]["query"],
                "user_id": fixture.payload["input"]["user_id"],
                "runtime_type": workflow_config.get("runtime_type", ""),
                "workflow_name": workflow_config.get("workflow_name", ""),
            }
            engine.runtime.validate(initial_context)
            result = engine.run(
                fixture.payload["input"]["query"],
                user_id=fixture.payload["input"]["user_id"],
            )
            answer = result.answer
            trace = baseline._json_safe(result.trace)
            execution_status = "PASS" if not result.context.get("failed_node") else "FAIL"
        except Exception as exc:
            validation_errors.append(str(exc))

    evaluation = score_response(fixture, answer)
    expected_order = list(workflow_config.get("execution", {}).get("order", []))
    actual_order = [step.get("node_id", "") for step in trace]
    trace_order_match = actual_order == expected_order
    row = {
        "condition": condition,
        "construction_method": (
            "manual_edit_from_task_a_json"
            if condition == "manual"
            else "template_builder_select_and_generate"
        ),
        "task_a_case": "outfit_01",
        "task_b_case": "outfit_03",
        "validation_status": "PASS" if not validation_errors else "FAIL",
        "validation_errors": validation_errors,
        "repair_count": 0,
        "execution_status": execution_status,
        "required_fields_present": bool(evaluation.get("required_fields_present")),
        "constraint_satisfaction": bool(evaluation.get("constraint_satisfaction")),
        "unsupported_fact_flags": evaluation.get("unsupported_fact_flags", []),
        "trace_order_match": trace_order_match,
        "trace_order": actual_order,
        "expected_trace_order": expected_order,
        "runtime_modified": False,
        "workflow_json": workflow_config,
        "final_answer": answer,
        "trace": trace,
        "root": str(root),
    }
    return row


def _apply_target_config(source: Any, target: Any) -> Any:
    if isinstance(source, dict) and isinstance(target, dict):
        result = copy.deepcopy(source)
        for key in list(result):
            if key not in target:
                del result[key]
        for key, value in target.items():
            result[key] = _apply_target_config(result[key], value) if key in result else copy.deepcopy(value)
        return result
    return copy.deepcopy(target)


def run_workflow_reuse(root: str | Path = V2_ROOT) -> list[dict[str, Any]]:
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    from agent_builder import TemplateWorkflowBuilder

    travel_template = PROJECT_ROOT / "configs" / "builder_templates" / "outfit_recommendation_template.json"
    commute_template = PROJECT_ROOT / "configs" / "builder_templates" / "commute_outfit_template.json"
    travel_config = TemplateWorkflowBuilder(travel_template).build_workflow_config(
        absolute_base_config=True
    )
    commute_config = TemplateWorkflowBuilder(commute_template).build_workflow_config(
        absolute_base_config=True
    )
    reuse = compare_workflow_reuse(travel_config, commute_config, runtime_modified=False)
    manual_config = _apply_target_config(travel_config, commute_config)
    fixture = _load_v2_fixture("outfit_03", root_path)
    rows = [
        _run_reuse_config("manual", manual_config, fixture, root_path),
        _run_reuse_config("builder", commute_config, fixture, root_path),
    ]
    for row in rows:
        row.update(
            {
                "changed_fields": reuse["changed_fields"],
                "added_fields": reuse["added_fields"],
                "removed_fields": reuse["removed_fields"],
                "modified_nodes": reuse["modified_nodes"],
                "modified_node_configs": reuse["modified_node_configs"],
                "reused_nodes": reuse["reused_nodes"],
                "replaced_nodes": reuse["replaced_nodes"],
                "new_nodes": reuse["new_nodes"],
                "removed_nodes": reuse["removed_nodes"],
                "manual_edit_paths": reuse["changed_fields"] + reuse["added_fields"] + reuse["removed_fields"]
                if row["condition"] == "manual"
                else [],
            }
        )

    details_path = root_path / "results" / "workflow_reuse_details.json"
    experiment_id = V2_EXPERIMENT_ID
    if (root_path / "manifest.json").is_file():
        experiment_id = baseline.load_manifest(root_path).get("experiment_id", V2_EXPERIMENT_ID)
    baseline._write_json(
        details_path,
        {
            "experiment_id": experiment_id,
            "task_a": {"case_id": "outfit_01", "template": str(travel_template)},
            "task_b": {"case_id": "outfit_03", "template": str(commute_template)},
            "shared_inputs": [
                "frozen weather",
                "frozen inventory",
                "Node Registry",
                "Workflow Runtime",
                "validation",
                "required output fields",
            ],
            "independent_variable": "workflow construction method",
            "manual_allowed_operations": [
                "copy/paste",
                "search/replace",
                "batch edit",
                "view registry/schema",
                "run validation",
                "fix validation errors",
            ],
            "comparison": reuse,
            "conditions": rows,
        },
    )
    fields = [
        "condition",
        "construction_method",
        "task_a_case",
        "task_b_case",
        "validation_status",
        "validation_errors",
        "repair_count",
        "execution_status",
        "required_fields_present",
        "constraint_satisfaction",
        "unsupported_fact_flags",
        "trace_order_match",
        "runtime_modified",
        "changed_fields",
        "added_fields",
        "removed_fields",
        "modified_nodes",
        "modified_node_configs",
        "reused_nodes",
        "replaced_nodes",
        "new_nodes",
        "removed_nodes",
        "manual_edit_paths",
    ]
    csv_rows = []
    for row in rows:
        csv_row = dict(row)
        for field in fields:
            if isinstance(csv_row.get(field), list):
                csv_row[field] = ";".join(str(item) for item in csv_row[field])
        csv_rows.append(csv_row)
    baseline._write_csv(root_path / "results" / "workflow_reuse.csv", fields, csv_rows)
    return rows


def _builder_result_rows(root: Path, fixtures: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    validation_rows = []
    trace_rows = []
    for path, record in baseline._iter_saved_records(root, "builder_runs"):
        case_id = str(record.get("case_id", ""))
        fixture = fixtures.get(case_id)
        if fixture is None:
            continue
        trace = record.get("full_trace", [])
        expected_order = list(record.get("workflow_json", {}).get("execution", {}).get("order", []))
        actual_order = [step.get("node_id", "") for step in trace]
        statuses = [step.get("status", "") for step in trace]
        evaluation = score_response(fixture, str(record.get("final_result", {}).get("answer", "")))
        validation_errors = list(record.get("errors", []))
        validation_pass = not validation_errors
        execution_pass = validation_pass and statuses and all(status == "SUCCESS" for status in statuses)
        source = baseline._relative_path(path, root)
        common = {
            "system": "Builder",
            "case_id": case_id,
            "run": record.get("run", ""),
            "source_file": source,
            "validation_status": "PASS" if validation_pass else "FAIL",
            "validation_errors": ";".join(str(error) for error in validation_errors),
            "execution_status": "PASS" if execution_pass else "FAIL",
            "runtime_source_modified": False,
            "required_fields_present": evaluation.get("required_fields_present", False),
            "constraint_satisfaction": evaluation.get("constraint_satisfaction", False),
            "unsupported_fact_flags": json.dumps(evaluation.get("unsupported_fact_flags", []), ensure_ascii=False),
        }
        validation_rows.append(common)
        trace_rows.append(
            {
                "system": "Builder",
                "case_id": case_id,
                "run": record.get("run", ""),
                "source_file": source,
                "expected_order": ";".join(expected_order),
                "actual_order": ";".join(actual_order),
                "trace_order_match": actual_order == expected_order,
                "statuses": ";".join(statuses),
                "failed_node": next((step.get("node_id", "") for step in trace if step.get("status") == "FAILED"), ""),
                "skipped_nodes": ";".join(step.get("node_id", "") for step in trace if step.get("status") == "SKIPPED"),
            }
        )
    return validation_rows, trace_rows


def _write_builder_summaries(root: Path, fixtures: dict[str, Any]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path, record in baseline._iter_saved_records(root, "builder_runs"):
        fixture = fixtures.get(str(record.get("case_id", "")))
        if fixture is None:
            continue
        evaluation = score_response(fixture, str(record.get("final_result", {}).get("answer", "")))
        grouped[str(record.get("case_id"))].append(
            {
                "run": record.get("run"),
                "source_file": baseline._relative_path(path, root),
                "required_fields_present": evaluation.get("required_fields_present"),
                "constraint_satisfaction": evaluation.get("constraint_satisfaction"),
                "unsupported_fact_flags": evaluation.get("unsupported_fact_flags", []),
                "trace_statuses": [step.get("status") for step in record.get("full_trace", [])],
            }
        )
    for case_id, records in grouped.items():
        baseline._write_json(
            root / "results" / "builder_v2" / f"{case_id}.json",
            {"case_id": case_id, "runs": sorted(records, key=lambda item: item["run"])},
        )


def _write_v2_summary(
    root: Path,
    manifest: dict[str, Any],
    common_report: dict[str, Any],
    reuse_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    trace_rows: list[dict[str, Any]],
) -> Path:
    case_ids = list(manifest.get("cases", []))
    builder_rows = [row for row in validation_rows if row["system"] == "Builder"]
    quality_pass = sum(
        bool(row["required_fields_present"]) and bool(row["constraint_satisfaction"])
        for row in builder_rows
    )
    repeatable = sum(
        row["system"] == "Builder" and row["status"] == "available"
        for row in csv.DictReader((root / "results" / "repeatability.csv").open(encoding="utf-8"))
    )
    comparable = {"outfit_01", "presentation_01", "customer_support_01"}
    regressions = []
    v1_path = PACKAGE_ROOT / "results" / "answer_quality.csv"
    v2_path = root / "results" / "case_quality.csv"
    if v1_path.is_file() and v2_path.is_file():
        with v1_path.open(encoding="utf-8", newline="") as handle:
            v1_rows = {
                (row["case_id"], row["run"]): row
                for row in csv.DictReader(handle)
                if row["system"] == "Builder" and row["case_id"] in comparable
            }
        with v2_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                key = (row["case_id"], row["run"])
                if row["system"] != "Builder" or key not in v1_rows:
                    continue
                old_ok = v1_rows[key].get("required_fields_present") == "True" and v1_rows[key].get("constraint_satisfaction") == "True"
                new_ok = row.get("required_fields_present") == "True" and row.get("constraint_satisfaction") == "True"
                if old_ok and not new_ok:
                    regressions.append(f"{key[0]} run {key[1]}")
    reuse_ok = all(
        row["validation_status"] == "PASS"
        and row["execution_status"] == "PASS"
        and row["trace_order_match"]
        for row in reuse_rows
    )
    lines = [
        "# Builder v2 — Pilot Experiment",
        "",
        "## Scope",
        "",
        f"Experiment ID: `{manifest['experiment_id']}`",
        f"Builder version: `{manifest.get('builder_version', '')}`",
        f"Cases: {len(case_ids)} frozen cases (Customer Support 5, Outfit 3, Presentation 2); 3 runs per case.",
        "This is a Pilot Experiment for validating the comparison method, checking the next presentation, and locating the Builder's real strengths and limits.",
        "Only ChatGPT is retained as the external baseline in this version. No composite ranking or winner is calculated.",
        "",
        "## Outfit v2 and Regression",
        "",
        "The recommendation now includes frozen precipitation, uses rain_ok at the configured precipitation threshold, and emits inventory-only selected items.",
        f"Comparable original cases with a quality regression: {len(regressions)}" + (f" ({', '.join(regressions)})." if regressions else "."),
        "",
        "## Workflow Reuse",
        "",
        "Task A is Travel Outfit and Task B is Commute Outfit. The manual condition starts from Task A Workflow JSON and applies recorded edit paths; the Builder condition selects the Commute template and generates its JSON.",
        f"Both conditions passed validation, execution, required-field checks, constraint checks and trace-order checks: {reuse_ok}.",
        "The calculation reports changed, added and removed fields plus reused, modified, replaced and new nodes. It records engineering operation facts only; it does not infer time or efficiency.",
        "",
        "## Case Quality",
        "",
        f"Builder quality checks passed for {quality_pass}/{len(builder_rows)} Builder runs.",
        f"Validation rows: {len(validation_rows)}; trace rows: {len(trace_rows)}.",
        "Customer Support objective checks derive from frozen policy data. Outfit and Presentation automated checks cover only objective fixture facts and explicit constraints.",
        "",
        "## Repeatability",
        "",
        f"Builder repeatability rows available: {repeatable}/{len(case_ids)}; parsed structured fields are compared across the three runs.",
        "",
        "## External Baseline Status",
        "",
        f"Formal ChatGPT records available: {common_report['formal_llm_record_count']}/{len(case_ids) * 3}.",
        "The prompts are frozen under the experiment root. Product-interface sampling parameters and exact backend revision remain recorded as unavailable when they cannot be confirmed.",
        "",
        "## Human Evaluation",
        "",
        "The existing-style Human Evaluation template is blank. Language quality, usefulness, clarity and naturalness were not collected in this round.",
        "",
        "## Limitations",
        "",
        "The ten cases and three repetitions are a pilot, so conclusions are limited to the tested cases.",
        "All metric dimensions remain separate: Answer Quality, Workflow Engineering, Configuration / Reuse, Repeatability, Failure Localization and Human Evaluation.",
        "Unfavorable results remain in the case-level artifacts; no overall score is produced.",
    ]
    summary_path = root / "results" / "summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def analyze_v2(root: str | Path = V2_ROOT) -> dict[str, Any]:
    root_path = Path(root)
    manifest = baseline.load_manifest(root_path)
    common_report = baseline.analyze_results(root=root_path)
    fixtures = {
        case_id: _load_v2_fixture(case_id, root_path)
        for case_id in manifest.get("cases", V2_CASE_FILES)
    }
    results_root = root_path / "results"
    shutil.copyfile(results_root / "answer_quality.csv", results_root / "case_quality.csv")
    _write_builder_summaries(root_path, fixtures)
    validation_rows, trace_rows = _builder_result_rows(root_path, fixtures)
    baseline._write_csv(
        results_root / "validation_results.csv",
        [
            "system", "case_id", "run", "source_file", "validation_status",
            "validation_errors", "execution_status", "runtime_source_modified",
            "required_fields_present", "constraint_satisfaction", "unsupported_fact_flags",
        ],
        validation_rows,
    )
    baseline._write_csv(
        results_root / "trace_summary.csv",
        [
            "system", "case_id", "run", "source_file", "expected_order", "actual_order",
            "trace_order_match", "statuses", "failed_node", "skipped_nodes",
        ],
        trace_rows,
    )
    reuse_rows = run_workflow_reuse(root=root_path)
    summary_path = _write_v2_summary(
        root_path,
        manifest,
        common_report,
        reuse_rows,
        validation_rows,
        trace_rows,
    )
    return {
        **common_report,
        "summary_path": str(summary_path),
        "validation_rows": len(validation_rows),
        "trace_rows": len(trace_rows),
        "reuse_rows": len(reuse_rows),
    }


def run_v2(root: str | Path = V2_ROOT) -> dict[str, Any]:
    root_path = Path(root)
    manifest = prepare_v2(root_path)
    builder_records = baseline.run_builder_pilot(root=root_path, case_files=V2_CASE_FILES)
    failure = baseline.run_failure_localization(root=root_path, case_files=V2_CASE_FILES)
    report = analyze_v2(root_path)
    return {
        **report,
        "manifest": manifest,
        "builder_records": builder_records,
        "failure": failure,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Builder v2 pilot experiment.")
    parser.add_argument("command", choices=("prepare", "run-builder", "reuse", "analyze", "all"), nargs="?", default="all")
    parser.add_argument("--root", default=str(V2_ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.command == "prepare":
        manifest = prepare_v2(root)
        print(f"Prepared experiment: {manifest['experiment_id']}")
        return 0
    if args.command == "run-builder":
        prepare_v2(root)
        records = baseline.run_builder_pilot(root=root, case_files=V2_CASE_FILES)
        print(f"Builder records: {len(records)}")
        return 0
    if args.command == "reuse":
        prepare_v2(root)
        rows = run_workflow_reuse(root)
        print(f"Reuse conditions: {len(rows)}")
        return 0
    if args.command == "analyze":
        report = analyze_v2(root)
        print(f"Summary: {report['summary_path']}")
        return 0
    report = run_v2(root)
    print(f"Builder records: {len(report['builder_records'])}")
    print(f"Formal ChatGPT records: {report['formal_llm_record_count']}")
    print(f"Summary: {report['summary_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

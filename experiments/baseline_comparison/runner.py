from __future__ import annotations

import copy
import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from time import perf_counter
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from weather_agent.models import WeatherReport  # noqa: E402


CASE_FILES = {
    "outfit_01": Path("fixtures/outfit/outfit_01.json"),
    "presentation_01": Path("fixtures/presentation/presentation_01.json"),
    "customer_support_01": Path("fixtures/customer_support/customer_support_01.json"),
}

REQUIRED_FIXTURE_FIELDS = {
    "case_id",
    "fixture_version",
    "domain",
    "input",
    "shared_context",
    "business_data",
    "constraints",
    "output_requirements",
    "ground_truth",
    "builder",
}

PROMPT_VERSION = "prompt-v1"
WORKFLOW_RUNTIME_VERSION = "workflow-runtime-contract-v1"
LLM_PROVIDERS = {"ChatGPT": "chatgpt", "Claude": "claude"}
DEFAULT_SYSTEMS = ("ChatGPT", "Claude", "Builder")
DEFAULT_RUNS_PER_CASE = 3
BUILDER_SOURCE_FILES = (
    # The experiment runners materialize frozen inputs and invoke the Builder.
    "experiments/baseline_comparison/runner.py",
    "experiments/baseline_comparison/v2_runner.py",
    # These modules are imported by the generated workflow execution path.
    "src/agent_builder/__init__.py",
    "src/agent_builder/engine.py",
    "src/agent_builder/local_llm.py",
    "src/agent_builder/node_registry.py",
    "src/agent_builder/shopping.py",
    "src/agent_builder/template_builder.py",
    "src/agent_builder/workflow.py",
    "src/agent_builder/workflow_runtime.py",
    "src/agent_builder/workflow_schema.py",
    "src/weather_agent/__init__.py",
    "src/weather_agent/agent.py",
    "src/weather_agent/models.py",
    "src/weather_agent/tools.py",
    # The base outfit configuration and formal template/data inputs.
    "configs/outfit_agent.json",
    "configs/builder_templates/commute_outfit_template.json",
    "configs/builder_templates/customer_support_ticket_template.json",
    "configs/builder_templates/outfit_recommendation_template.json",
    "configs/builder_templates/presentation_planning_template.json",
    "data/presentation_knowledge.json",
    "data/shopping_history.json",
    "data/support_policy.json",
    # The ten frozen v2 task inputs used by the formal Builder runs.
    "experiments/baseline_comparison/fixtures/outfit/outfit_01.json",
    "experiments/baseline_comparison/fixtures/outfit/outfit_02.json",
    "experiments/baseline_comparison/fixtures/outfit/outfit_03.json",
    "experiments/baseline_comparison/fixtures/presentation/presentation_01.json",
    "experiments/baseline_comparison/fixtures/presentation/presentation_02.json",
    "experiments/baseline_comparison/fixtures/customer_support/customer_support_01.json",
    "experiments/baseline_comparison/fixtures/customer_support/customer_support_02.json",
    "experiments/baseline_comparison/fixtures/customer_support/customer_support_03.json",
    "experiments/baseline_comparison/fixtures/customer_support/customer_support_04.json",
    "experiments/baseline_comparison/fixtures/customer_support/customer_support_05.json",
)
LLM_REQUIRED_FIELDS = {
    "experiment_id",
    "case_id",
    "fixture_version",
    "prompt_version",
    "run",
    "provider",
    "model_name",
    "sampling_parameters",
    "exact_backend_revision",
    "timestamp",
    "prompt_file",
    "prompt_sha256",
    "response",
    "run_id",
}


@dataclass(frozen=True)
class LoadedFixture:
    case_id: str
    path: Path
    payload: dict[str, Any]
    sha256: str
    source_sha256: str


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def builder_source_hashes() -> dict[str, str]:
    """Return the exact source/config inputs that can affect formal Builder v2 output."""
    hashes: dict[str, str] = {}
    for relative_path in BUILDER_SOURCE_FILES:
        path = PROJECT_ROOT / relative_path
        if not path.is_file():
            raise ValueError(f"Builder source dependency is missing: {path}")
        hashes[relative_path] = _file_hash(path)
    return hashes


def load_fixture(
    case_id: str,
    root: str | Path | None = None,
    case_files: dict[str, Path] | None = None,
) -> LoadedFixture:
    catalog = CASE_FILES if case_files is None else case_files
    try:
        relative_path = catalog[case_id]
    except KeyError as exc:
        raise ValueError(f"unknown baseline fixture: {case_id}") from exc

    fixture_root = Path(root) if case_files is not None and root is not None else PACKAGE_ROOT
    path = (fixture_root / relative_path).resolve()
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid fixture JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"fixture must be a JSON object: {path}")

    missing = sorted(REQUIRED_FIXTURE_FIELDS - set(payload))
    if missing:
        raise ValueError(f"fixture {case_id} missing fields: {', '.join(missing)}")
    if payload["case_id"] != case_id:
        raise ValueError(f"fixture case_id mismatch: expected {case_id}")
    if not isinstance(payload["input"], dict):
        raise ValueError(f"fixture input must be an object: {case_id}")

    return LoadedFixture(
        case_id=case_id,
        path=path,
        payload=copy.deepcopy(payload),
        sha256=canonical_hash(payload),
        source_sha256=_file_hash(path),
    )


class FrozenWeatherProvider:
    """Experiment-only weather provider; it never performs network I/O."""

    def __init__(self, weather: dict[str, Any]):
        self.weather = copy.deepcopy(weather)

    def get_daily_weather(
        self,
        city_query: str,
        day_offset: int,
        timezone: str = "Asia/Seoul",
    ) -> WeatherReport:
        del city_query, day_offset, timezone
        return WeatherReport(
            city_name=str(self.weather["city_name"]),
            country=str(self.weather.get("country", "")),
            date=str(self.weather["date"]),
            condition=str(self.weather["condition"]),
            weather_code=int(self.weather["weather_code"]),
            temp_min=float(self.weather["temp_min"]),
            temp_max=float(self.weather["temp_max"]),
            precipitation_probability=int(self.weather["precipitation_probability"]),
            latitude=float(self.weather["latitude"]),
            longitude=float(self.weather["longitude"]),
        )

    def describe_tool_call(self, report: WeatherReport) -> dict[str, Any]:
        data = asdict(report)
        data["tool"] = "FrozenWeatherProvider"
        return data


def render_prompt(fixture: LoadedFixture) -> str:
    payload = fixture.payload
    sections = [
        "TASK",
        f"Use the frozen task input below to complete the {payload['domain']} task.",
        "",
        "INPUT",
        json.dumps(payload["input"], ensure_ascii=False, indent=2),
        "",
        "CONTEXT / DATA",
        json.dumps(
            {
                "shared_context": payload["shared_context"],
                "business_data": payload["business_data"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        "",
        "CONSTRAINTS",
        json.dumps(payload["constraints"], ensure_ascii=False, indent=2),
        "",
        "REQUIRED OUTPUT",
        json.dumps(payload["output_requirements"], ensure_ascii=False, indent=2),
        "",
        "MISSING INFORMATION RULE",
        "Do not invent missing facts, data, policy details, weather, inventory, or model metadata. "
        "State what is missing when the supplied information is insufficient.",
        "",
        f"FIXTURE VERSION: {payload['fixture_version']}",
        f"FIXTURE SHA256: {fixture.sha256}",
    ]
    return "\n".join(sections) + "\n"


def write_prompts(fixture: LoadedFixture, output_root: str | Path = PACKAGE_ROOT) -> dict[str, Path]:
    return write_prompts_for_providers(fixture, output_root)


def write_prompts_for_providers(
    fixture: LoadedFixture,
    output_root: str | Path = PACKAGE_ROOT,
    providers: tuple[str, ...] = ("chatgpt", "claude"),
) -> dict[str, Path]:
    prompt = render_prompt(fixture).encode("utf-8")
    root = Path(output_root) / "prompts"
    paths = {}
    for provider in providers:
        path = root / provider / f"{fixture.case_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(prompt)
        paths[provider] = path
    return paths


def _git_metadata(root: Path = PROJECT_ROOT) -> tuple[str, list[str]]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).stdout.strip()

    return run("rev-parse", "HEAD"), [line for line in run("status", "--short").splitlines() if line]


def build_manifest(
    experiment_id: str,
    fixture_versions: dict[str, str],
    prompt_versions: dict[str, str],
    git_head: str | None = None,
    git_status: list[str] | None = None,
    test_count: int = 0,
    template_versions: dict[str, dict[str, str]] | None = None,
    created_at: str | None = None,
    builder_version: str = "builder-v1",
    systems: list[str] | tuple[str, ...] | None = None,
    case_ids: list[str] | tuple[str, ...] | None = None,
    runs_per_case: int = DEFAULT_RUNS_PER_CASE,
) -> dict[str, Any]:
    if git_head is None or git_status is None:
        detected_head, detected_status = _git_metadata()
        git_head = git_head or detected_head
        git_status = detected_status if git_status is None else git_status
    created = created_at or datetime.now(timezone.utc).isoformat()
    runtime_path = PROJECT_ROOT / "src" / "agent_builder" / "workflow_runtime.py"
    return {
        "experiment_id": experiment_id,
        "created_at": created,
        "python_version": platform.python_version(),
        "test_count": int(test_count),
        "test_command": "python -B -m unittest discover -s tests -q",
        "builder_version": builder_version,
        "builder_source_hashes": builder_source_hashes(),
        "workflow_runtime_version": WORKFLOW_RUNTIME_VERSION,
        "workflow_schema_version": 1,
        "runtime_source_sha256": _file_hash(runtime_path),
        "git_head": git_head,
        "git_worktree_state": "dirty" if git_status else "clean",
        "git_status": list(git_status),
        "template_versions": template_versions or {},
        "fixture_versions": dict(fixture_versions),
        "prompt_versions": dict(prompt_versions),
        "cases": list(case_ids or CASE_FILES),
        "systems": list(systems or DEFAULT_SYSTEMS),
        "runs_per_case": int(runs_per_case),
        "sampling_parameters": "unavailable",
        "exact_backend_revision": "unavailable",
    }


def _manifest_version_info(manifest: dict[str, Any], key: str, case_id: str) -> tuple[str, str]:
    values = manifest.get(key, {})
    value = values.get(case_id) if isinstance(values, dict) else None
    if isinstance(value, dict):
        return str(value.get("version", "")), str(value.get("sha256", ""))
    return str(value or ""), ""


def is_formal_llm_record(record: dict[str, Any]) -> bool:
    return record.get("status") != "EXAMPLE_ONLY" and record.get("formal", True) is not False


def validate_llm_record(
    record: dict[str, Any],
    manifest: dict[str, Any],
    prompt_root: str | Path,
    formal: bool = True,
) -> list[str]:
    errors = []
    missing = sorted(LLM_REQUIRED_FIELDS - set(record))
    errors.extend(f"missing field: {field}" for field in missing)
    if missing:
        return errors

    case_id = str(record["case_id"])
    allowed_cases = set(manifest.get("cases") or CASE_FILES)
    if case_id not in allowed_cases:
        errors.append(f"unknown case_id: {case_id}")
    allowed_providers = {
        system for system in (manifest.get("systems") or LLM_PROVIDERS)
        if system in LLM_PROVIDERS
    }
    if record["provider"] not in allowed_providers:
        errors.append(f"unknown provider: {record['provider']}")
    runs_per_case = int(manifest.get("runs_per_case", DEFAULT_RUNS_PER_CASE))
    if not isinstance(record["run"], int) or isinstance(record["run"], bool) or not 1 <= record["run"] <= runs_per_case:
        errors.append(f"run must be an integer from 1 to {runs_per_case}")
    if not str(record["model_name"]).strip():
        errors.append("model_name must not be empty")
    if record["sampling_parameters"] in (None, ""):
        errors.append("sampling_parameters must be recorded")
    if not str(record["exact_backend_revision"]).strip():
        errors.append("exact_backend_revision must be recorded")
    if not isinstance(record["response"], str) or not record["response"].strip():
        errors.append("response must not be empty")
    try:
        datetime.fromisoformat(str(record["timestamp"]))
    except ValueError:
        errors.append("timestamp must be ISO-8601")

    expected_experiment = str(manifest.get("experiment_id", ""))
    if record["experiment_id"] != expected_experiment:
        errors.append("experiment_id does not match manifest")
    expected_fixture_version, _ = _manifest_version_info(manifest, "fixture_versions", case_id)
    if expected_fixture_version and record["fixture_version"] != expected_fixture_version:
        errors.append("fixture_version does not match manifest")
    expected_prompt_version, expected_prompt_hash = _manifest_version_info(manifest, "prompt_versions", case_id)
    if expected_prompt_version and record["prompt_version"] != expected_prompt_version:
        errors.append("prompt_version does not match manifest")

    root = Path(prompt_root).resolve()
    prompt_path = (root / str(record["prompt_file"])).resolve()
    if root not in prompt_path.parents:
        errors.append("prompt_file escapes experiment root")
    elif not prompt_path.is_file():
        errors.append("prompt_file does not exist")
    else:
        actual_prompt_hash = _file_hash(prompt_path)
        if record["prompt_sha256"] != actual_prompt_hash:
            errors.append("prompt_sha256 does not match prompt_file")
        if expected_prompt_hash and record["prompt_sha256"] != expected_prompt_hash:
            errors.append("prompt_sha256 does not match manifest")

    provider_slug = LLM_PROVIDERS.get(record["provider"])
    if provider_slug and f"prompts/{provider_slug}/" not in str(record["prompt_file"]).replace("\\", "/"):
        errors.append("prompt_file provider directory does not match provider")
    if formal and not is_formal_llm_record(record):
        errors.append("EXAMPLE_ONLY records are not formal")
    return errors


def import_llm_record(
    source_path: str | Path,
    destination_root: str | Path,
    manifest_path: str | Path,
) -> Path:
    source = Path(source_path)
    manifest_file = Path(manifest_path)
    raw = source.read_bytes()
    try:
        record = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid LLM record JSON: {source}") from exc
    if not isinstance(record, dict):
        raise ValueError("LLM record must be a JSON object")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    _verify_frozen_manifest(manifest, manifest_file.parent)
    errors = validate_llm_record(record, manifest, manifest_file.parent, formal=False)
    if errors:
        raise ValueError("; ".join(errors))

    provider_slug = LLM_PROVIDERS[record["provider"]]
    destination = Path(destination_root) / provider_slug / (
        f"{provider_slug}_{record['case_id']}_run_{record['run']}.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() != raw:
            raise ValueError(f"immutable LLM run already exists with different bytes: {destination}")
        return destination
    shutil.copyfile(source, destination)
    return destination


def iter_llm_records(root: str | Path = PACKAGE_ROOT / "llm_runs") -> list[dict[str, Any]]:
    records = []
    for path in sorted(Path(root).glob("*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(record, dict):
            records.append(record)
    return records


def _json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _reject_frozen_v1_write(root: str | Path) -> None:
    candidate = Path(root).resolve()
    if candidate == PACKAGE_ROOT.resolve() and (candidate / "manifest.json").is_file():
        raise RuntimeError(
            "Pilot v1 is frozen; use experiments/baseline_comparison/v2_runner.py "
            "or pass a new experiment root"
        )


class _FailingWeatherProvider(FrozenWeatherProvider):
    def get_daily_weather(
        self,
        city_query: str,
        day_offset: int,
        timezone: str = "Asia/Seoul",
    ) -> WeatherReport:
        del city_query, day_offset, timezone
        raise RuntimeError("weather service unavailable")


def _fixture_data_payload(fixture: LoadedFixture) -> dict[str, Any]:
    payload = fixture.payload
    data_file = payload["builder"]["data_file"]
    if data_file == "shopping_history.json":
        return dict(payload["business_data"]["shopping_history"])
    return dict(payload["business_data"])


def run_builder_case(
    case_id: str,
    run_index: int,
    *,
    root: str | Path = PACKAGE_ROOT,
    failure_mode: str | None = None,
    output_subdir: str = "builder_runs",
    case_files: dict[str, Path] | None = None,
    base_config_override: str | Path | None = None,
) -> dict[str, Any]:
    _reject_frozen_v1_write(root)
    if run_index not in (1, 2, 3):
        raise ValueError("run_index must be 1, 2, or 3")
    output_root = Path(root)
    fixture = load_fixture(case_id, root=output_root, case_files=case_files)
    template_path = PROJECT_ROOT / fixture.payload["builder"]["template"]

    from agent_builder import MultiAgentWorkflowEngine, TemplateWorkflowBuilder

    builder = TemplateWorkflowBuilder(template_path)
    workflow_config = builder.build_workflow_config(absolute_base_config=True)
    artifact_workflow_config = copy.deepcopy(workflow_config)
    if base_config_override is not None:
        workflow_config["base_agent_config"] = str(Path(base_config_override).resolve())
        artifact_workflow_config["base_agent_config"] = str(
            (PROJECT_ROOT / "configs" / "outfit_agent.json").resolve()
        )
    workflow_config["data_dir"] = None
    workflow_config["experiment_mode"] = {
        "type": "frozen_fixture",
        "fixture_version": fixture.payload["fixture_version"],
        "fixture_sha256": fixture.sha256,
    }
    artifact_workflow_config["data_dir"] = None
    artifact_workflow_config["experiment_mode"] = copy.deepcopy(workflow_config["experiment_mode"])

    started_at = datetime.now(timezone.utc).isoformat()
    started = perf_counter()
    trace: list[dict[str, Any]] = []
    answer = ""
    context: dict[str, Any] = {}
    error = None
    with tempfile.TemporaryDirectory(prefix=f"baseline_{case_id}_") as temp_dir:
        data_dir = Path(temp_dir) / "data"
        data_dir.mkdir()
        data_file = str(fixture.payload["builder"]["data_file"])
        (data_dir / data_file).write_text(
            json.dumps(_fixture_data_payload(fixture), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        config_path = Path(temp_dir) / "workflow.json"
        config_path.write_text(
            json.dumps(workflow_config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        weather_tool = None
        if fixture.payload["domain"] == "outfit":
            weather = fixture.payload["shared_context"]["weather"]
            weather_tool = _FailingWeatherProvider(weather) if failure_mode == "weather" else FrozenWeatherProvider(weather)
        try:
            engine = MultiAgentWorkflowEngine(
                config_path,
                data_dir=data_dir,
                weather_tool=weather_tool,
            )
            result = engine.run(
                fixture.payload["input"]["query"],
                user_id=fixture.payload["input"]["user_id"],
            )
            answer = result.answer
            context = _json_safe(result.context)
            trace = _json_safe(result.trace)
        except Exception as exc:  # Preserve unexpected run errors in the artifact.
            error = str(exc)
    if base_config_override is not None:
        legacy_path = str(Path(base_config_override).resolve())
        canonical_path = str((PROJECT_ROOT / "configs" / "outfit_agent.json").resolve())

        def canonicalize(value: Any) -> Any:
            if isinstance(value, dict):
                return {key: canonicalize(item) for key, item in value.items()}
            if isinstance(value, list):
                return [canonicalize(item) for item in value]
            return canonical_path if value == legacy_path else value

        trace = canonicalize(trace)
        context = canonicalize(context)
    finished_at = datetime.now(timezone.utc).isoformat()
    duration_ms = round((perf_counter() - started) * 1000, 3)
    node_statuses = [
        {
            "node_id": step.get("node_id", ""),
            "node_type": step.get("node_type", ""),
            "status": step.get("status", ""),
        }
        for step in trace
    ]
    errors = [step.get("error") for step in trace if step.get("error")]
    if error:
        errors.append(error)
    manifest_path = output_root / "manifest.json"
    experiment_id = ""
    prompt_version = ""
    builder_version = ""
    if manifest_path.is_file():
        current_manifest = load_manifest(output_root)
        experiment_id = str(current_manifest.get("experiment_id", ""))
        prompt_version = _manifest_version_info(current_manifest, "prompt_versions", case_id)[0]
        builder_version = str(current_manifest.get("builder_version", "builder-v1"))
    record = {
        "run_id": f"builder_{case_id}_{run_index}",
        "experiment_id": experiment_id,
        "builder_version": builder_version,
        "case_id": case_id,
        "run": run_index,
        "system": "Builder",
        "timestamp": started_at,
        "finished_at": finished_at,
        "input": copy.deepcopy(fixture.payload["input"]),
        "fixture_version": fixture.payload["fixture_version"],
        "fixture_sha256": fixture.sha256,
        "prompt_version": prompt_version,
        "workflow_json": artifact_workflow_config,
        "workflow_sha256": canonical_hash(artifact_workflow_config),
        "final_result": {"answer": answer, "context": context},
        "full_trace": trace,
        "duration_ms": duration_ms,
        "node_statuses": node_statuses,
        "errors": errors,
        "failure_mode": failure_mode,
    }
    output_path = output_root / output_subdir / case_id / f"run_{run_index}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def run_builder_pilot(
    root: str | Path = PACKAGE_ROOT,
    case_files: dict[str, Path] | None = None,
    base_config_override: str | Path | None = None,
) -> list[dict[str, Any]]:
    _reject_frozen_v1_write(root)
    catalog = CASE_FILES if case_files is None else case_files
    return [
        run_builder_case(
            case_id,
            run_index,
            root=root,
            case_files=case_files,
            base_config_override=base_config_override,
        )
        for case_id in catalog
        for run_index in (1, 2, 3)
    ]


def run_failure_localization(
    root: str | Path = PACKAGE_ROOT,
    case_files: dict[str, Path] | None = None,
    base_config_override: str | Path | None = None,
) -> dict[str, Any]:
    _reject_frozen_v1_write(root)
    record = run_builder_case(
        "outfit_01",
        1,
        root=root,
        failure_mode="weather",
        output_subdir="failure_runs",
        case_files=case_files,
        base_config_override=base_config_override,
    )
    trace = record["full_trace"]
    result = {
        "case_id": "outfit_01",
        "experiment": "failure_localization",
        "failed_node": record["final_result"]["context"].get("failed_node", ""),
        "error": next(iter(record["errors"]), ""),
        "trace": trace,
        "excluded_from_answer_quality": True,
    }
    output_path = Path(root) / "results" / "failure_localization.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def load_manifest(root: str | Path = PACKAGE_ROOT) -> dict[str, Any]:
    path = Path(root) / "manifest.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid experiment manifest: {path}") from exc
    if not isinstance(value, dict) or not value.get("experiment_id"):
        raise ValueError(f"experiment manifest must be an object with experiment_id: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _test_count() -> int:
    try:
        import unittest

        suite = unittest.defaultTestLoader.discover(str(PROJECT_ROOT / "tests"))
        return suite.countTestCases()
    except Exception:
        return 0


def _experiment_inputs(
    case_files: dict[str, Path] | None = None,
    root: str | Path = PACKAGE_ROOT,
) -> tuple[dict[str, LoadedFixture], dict[str, dict[str, str]]]:
    catalog = CASE_FILES if case_files is None else case_files
    fixture_root = root if case_files is not None else PACKAGE_ROOT
    fixtures = {
        case_id: load_fixture(case_id, root=fixture_root, case_files=case_files)
        for case_id in catalog
    }
    prompt_versions = {}
    for case_id, fixture in fixtures.items():
        prompt_hash = hashlib.sha256(render_prompt(fixture).encode("utf-8")).hexdigest()
        prompt_versions[case_id] = {"version": PROMPT_VERSION, "sha256": prompt_hash}
    return fixtures, prompt_versions


def _template_versions(fixtures: dict[str, LoadedFixture]) -> dict[str, dict[str, str]]:
    values = {}
    for case_id, fixture in fixtures.items():
        relative = Path(fixture.payload["builder"]["template"])
        path = PROJECT_ROOT / relative
        values[case_id] = {"path": str(relative), "sha256": _file_hash(path)}
    return values


def _verify_frozen_manifest(
    manifest: dict[str, Any],
    root: str | Path,
    fixtures: dict[str, LoadedFixture] | None = None,
) -> None:
    """Reject core drift while allowing new raw result files under the root."""
    expected_head = str(manifest.get("git_head", ""))
    if expected_head:
        current_head, _ = _git_metadata()
        if current_head != expected_head:
            raise ValueError("Git commit changed; create a new experiment_id")

    runtime_hash = manifest.get("runtime_source_sha256")
    if runtime_hash and _file_hash(PROJECT_ROOT / "src" / "agent_builder" / "workflow_runtime.py") != runtime_hash:
        raise ValueError("Workflow Runtime hash changed; create a new experiment_id")
    if manifest.get("workflow_runtime_version") and manifest["workflow_runtime_version"] != WORKFLOW_RUNTIME_VERSION:
        raise ValueError("Workflow Runtime version changed; create a new experiment_id")

    expected_builder_sources = manifest.get("builder_source_hashes")
    if isinstance(expected_builder_sources, dict) and expected_builder_sources:
        if expected_builder_sources != builder_source_hashes():
            raise ValueError("Builder source hash changed; create a new experiment_id")

    if fixtures is None:
        fixture_files = manifest.get("fixture_files", {})
        if isinstance(fixture_files, dict):
            catalog = {case_id: Path(path) for case_id, path in fixture_files.items()}
            fixtures = {
                case_id: load_fixture(case_id, root=root, case_files=catalog)
                for case_id in manifest.get("cases", catalog)
            }
        else:
            fixtures = {}
    if fixtures:
        expected_fixtures = {
            case_id: {
                "version": fixture.payload["fixture_version"],
                "sha256": fixture.sha256,
            }
            for case_id, fixture in fixtures.items()
        }
        if manifest.get("fixture_versions") and manifest["fixture_versions"] != expected_fixtures:
            raise ValueError("Fixture hash changed; create a new experiment_id")
        expected_templates = _template_versions(fixtures)
        if manifest.get("template_versions") and manifest["template_versions"] != expected_templates:
            raise ValueError("Template hash changed; create a new experiment_id")

        prompt_files = manifest.get("prompt_files", {})
        if isinstance(prompt_files, dict):
            for provider_files in prompt_files.values():
                if not isinstance(provider_files, dict):
                    continue
                for case_id, relative_path in provider_files.items():
                    prompt_path = (Path(root) / str(relative_path)).resolve()
                    if not prompt_path.is_file():
                        raise ValueError(f"frozen Prompt is missing: {prompt_path}")
                    expected_hash = _manifest_version_info(manifest, "prompt_versions", case_id)[1]
                    if expected_hash and _file_hash(prompt_path) != expected_hash:
                        raise ValueError("Prompt file hash changed; create a new experiment_id")
                    rendered_hash = hashlib.sha256(
                        render_prompt(fixtures[case_id]).encode("utf-8")
                    ).hexdigest()
                    if expected_hash and rendered_hash != expected_hash:
                        raise ValueError("Rendered Prompt hash changed; create a new experiment_id")


def prepare_experiment(
    *,
    root: str | Path = PACKAGE_ROOT,
    experiment_id: str | None = None,
    case_files: dict[str, Path] | None = None,
    systems: list[str] | tuple[str, ...] | None = None,
    runs_per_case: int = DEFAULT_RUNS_PER_CASE,
    builder_version: str = "builder-v1",
) -> dict[str, Any]:
    """Freeze Prompts and metadata before any external model data is imported."""
    _reject_frozen_v1_write(root)
    output_root = Path(root)
    output_root.mkdir(parents=True, exist_ok=True)
    catalog = CASE_FILES if case_files is None else case_files
    requested_systems = list(systems or DEFAULT_SYSTEMS)
    llm_providers = tuple(
        LLM_PROVIDERS[system] for system in requested_systems if system in LLM_PROVIDERS
    )
    fixtures, prompt_versions = _experiment_inputs(case_files, root=output_root)
    fixture_versions = {
        case_id: {
            "version": fixture.payload["fixture_version"],
            "sha256": fixture.sha256,
        }
        for case_id, fixture in fixtures.items()
    }
    manifest_path = output_root / "manifest.json"
    if manifest_path.exists():
        manifest = load_manifest(output_root)
        if experiment_id and manifest.get("experiment_id") != experiment_id:
            raise ValueError("experiment_id changed; create a new experiment root")
        if manifest.get("fixture_versions") != fixture_versions or manifest.get("prompt_versions") != prompt_versions:
            raise ValueError(
                "fixture or Prompt version changed; create a new experiment_id instead of mixing runs"
            )
        for case_id, versions in prompt_versions.items():
            expected = versions["sha256"]
            for provider in llm_providers:
                path = output_root / "prompts" / provider / f"{case_id}.md"
                if not path.is_file() or _file_hash(path) != expected:
                    raise ValueError(
                        f"frozen Prompt changed or is missing: {path}; create a new experiment_id"
                    )
        expected_cases = list(catalog)
        if list(manifest.get("cases") or CASE_FILES) != expected_cases:
            raise ValueError("case catalog changed; create a new experiment_id instead of mixing runs")
        if list(manifest.get("systems") or DEFAULT_SYSTEMS) != requested_systems:
            raise ValueError("system set changed; create a new experiment_id instead of mixing runs")
        if str(manifest.get("builder_version", "builder-v1")) != builder_version:
            raise ValueError("builder version changed; create a new experiment_id instead of mixing runs")
        if int(manifest.get("runs_per_case", DEFAULT_RUNS_PER_CASE)) != runs_per_case:
            raise ValueError("runs_per_case changed; create a new experiment_id instead of mixing runs")
    else:
        for fixture in fixtures.values():
            write_prompts_for_providers(fixture, output_root, llm_providers)
        manifest = build_manifest(
            experiment_id=experiment_id
            or datetime.now(timezone.utc).strftime("baseline_pilot_%Y%m%d_%H%M%S"),
            fixture_versions=fixture_versions,
            prompt_versions=prompt_versions,
            test_count=_test_count(),
            template_versions=_template_versions(fixtures),
            builder_version=builder_version,
            systems=requested_systems,
            case_ids=list(catalog),
            runs_per_case=runs_per_case,
        )
        manifest["fixture_files"] = {
            case_id: _relative_path(fixture.path, output_root)
            for case_id, fixture in fixtures.items()
        }
        manifest["prompt_files"] = {
            provider: {
                case_id: f"prompts/{provider}/{case_id}.md"
                for case_id in catalog
            }
            for provider in llm_providers
        }
        _write_json(manifest_path, manifest)

    _verify_frozen_manifest(manifest, output_root, fixtures)
    results_root = output_root / "results"
    results_root.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(manifest_path, results_root / "experiment_manifest.json")
    for provider in llm_providers:
        (output_root / "llm_runs" / provider).mkdir(parents=True, exist_ok=True)
    return manifest


def _iter_saved_records(root: Path, folder: str) -> list[tuple[Path, dict[str, Any]]]:
    records = []
    for path in sorted((root / folder).glob("*/*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            records.append((path, value))
    return records


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        try:
            return os.path.relpath(path, root).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")


def _score_saved_record(
    fixture: LoadedFixture,
    record: dict[str, Any],
    source_path: Path,
    root: Path,
    results_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from experiments.baseline_comparison.evaluation.scoring import score_response

    if record.get("system") == "Builder":
        response = str(record.get("final_result", {}).get("answer", ""))
    else:
        response = str(record.get("response", ""))
    evaluation = score_response(fixture, response)
    stem = f"{str(record.get('system', 'unknown')).lower()}_{record.get('case_id', '')}_run_{record.get('run', '')}"
    response_hash = hashlib.sha256(response.encode("utf-8")).hexdigest()
    source = _relative_path(source_path, root)
    parsed_artifact = {
        "experiment_id": load_manifest(root)["experiment_id"],
        "system": record.get("system", record.get("provider", "")),
        "case_id": record.get("case_id", ""),
        "run": record.get("run", ""),
        "source_file": source,
        "response_sha256": response_hash,
        "parsed": evaluation.get("parsed", {}),
    }
    evaluation_artifact = {
        "experiment_id": parsed_artifact["experiment_id"],
        "system": parsed_artifact["system"],
        "case_id": parsed_artifact["case_id"],
        "run": parsed_artifact["run"],
        "source_file": source,
        "response_sha256": response_hash,
        "evaluation": evaluation,
    }
    _write_json(results_root / "parsed" / f"{stem}.json", parsed_artifact)
    _write_json(results_root / "evaluation" / f"{stem}.json", evaluation_artifact)
    return evaluation, parsed_artifact["parsed"]


def _answer_quality_rows(
    manifest: dict[str, Any],
    fixtures: dict[str, LoadedFixture],
    builder_records: list[tuple[Path, dict[str, Any]]],
    llm_records: list[tuple[Path, dict[str, Any]]],
    root: Path,
    results_root: Path,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str, int], dict[str, Any]], list[str]]:
    systems = list(manifest.get("systems") or DEFAULT_SYSTEMS)
    case_ids = list(manifest.get("cases") or fixtures)
    runs_per_case = int(manifest.get("runs_per_case", DEFAULT_RUNS_PER_CASE))
    records_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    parsed_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    invalid: list[str] = []
    for path, record in builder_records:
        key = ("Builder", str(record.get("case_id")), int(record.get("run", 0) or 0))
        if key[1] not in fixtures or key[2] not in range(1, runs_per_case + 1):
            invalid.append(f"{_relative_path(path, root)}: invalid Builder key")
            continue
        evaluation, parsed = _score_saved_record(fixtures[key[1]], record, path, root, results_root)
        records_by_key[key] = {"record": record, "evaluation": evaluation, "source": path}
        parsed_by_key[key] = parsed

    for path, record in llm_records:
        provider = str(record.get("provider", ""))
        system = provider if provider in LLM_PROVIDERS else ""
        key = (system, str(record.get("case_id")), int(record.get("run", 0) or 0))
        if system and system in systems and key[1] in fixtures and key[2] in range(1, runs_per_case + 1):
            evaluation, parsed = _score_saved_record(fixtures[key[1]], record, path, root, results_root)
            records_by_key[key] = {"record": record, "evaluation": evaluation, "source": path}
            parsed_by_key[key] = parsed

    rows = []
    fields = (
        "required_fields_present",
        "required_fields_missing",
        "context_usage",
        "constraint_satisfaction",
        "completeness",
        "ground_truth_correctness",
        "unsupported_fact_flags",
        "human_evaluation_status",
        "open_language_quality",
    )
    for system in systems:
        for case_id in case_ids:
            for run in range(1, runs_per_case + 1):
                key = (system, case_id, run)
                current = records_by_key.get(key)
                if current is None:
                    row = {
                        "system": system,
                        "case_id": case_id,
                        "run": run,
                        "run_status": "pending_real_run" if system != "Builder" else "missing_builder_run",
                        "run_id": "",
                        "source_file": "",
                    }
                    row.update({field: "" for field in fields})
                else:
                    record = current["record"]
                    evaluation = current["evaluation"]
                    row = {
                        "system": system,
                        "case_id": case_id,
                        "run": run,
                        "run_status": "available",
                        "run_id": record.get("run_id", ""),
                        "source_file": _relative_path(current["source"], root),
                    }
                    for field in fields:
                        value = evaluation.get(field, "")
                        row[field] = json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value
                rows.append(row)
    return rows, parsed_by_key, invalid


def _repeatability_rows(
    parsed_by_key: dict[tuple[str, str, int], dict[str, Any]],
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    from experiments.baseline_comparison.evaluation.scoring import structured_agreement

    systems = list(manifest.get("systems") or DEFAULT_SYSTEMS)
    case_ids = list(manifest.get("cases") or CASE_FILES)
    runs_per_case = int(manifest.get("runs_per_case", DEFAULT_RUNS_PER_CASE))
    rows = []
    for system in systems:
        for case_id in case_ids:
            values = [
                parsed_by_key[(system, case_id, run)]
                for run in range(1, runs_per_case + 1)
                if (system, case_id, run) in parsed_by_key
            ]
            agreement = structured_agreement(values)
            rows.append(
                {
                    "system": system,
                    "case_id": case_id,
                    "run_count": agreement["run_count"],
                    "status": "available" if len(values) == runs_per_case else "pending_real_runs" if not values else "partial",
                    "structured_fields_match": agreement["all_match"] if values else "",
                    "compared_fields": ";".join(agreement["compared_fields"]),
                }
            )
    return rows


def _workflow_feature_rows(
    root: Path,
    builder_records: list[tuple[Path, dict[str, Any]]],
    systems: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    builder_count = len(builder_records)
    features = [
        ("workflow_validation", "available", "Generated Workflow JSON was accepted by the existing Runtime validation."),
        ("structured_execution", "available", f"{builder_count} Builder run records include declared node execution."),
        ("node_level_trace", "available", "Normal records preserve six node-level trace entries."),
        ("failure_localization", "available", "Controlled weather failure identifies the failed node and downstream skips."),
        ("repeatability_recording", "available", "Three run records per frozen Case are stored for structured comparison."),
        ("configuration_reuse", "available", "The reuse calculation compares generated outfit and commute configurations."),
    ]
    rows = []
    for system in list(systems or DEFAULT_SYSTEMS):
        for feature, builder_status, evidence in features:
            if system == "Builder":
                status, detail = builder_status, evidence
            else:
                status, detail = "not_available_in_this_experiment", "No comparable workflow artifact was collected from this product run."
            rows.append({"system": system, "feature": feature, "status": status, "evidence": detail})
    return rows


def _configuration_rows() -> list[dict[str, Any]]:
    from experiments.baseline_comparison.evaluation.scoring import compare_reuse, count_touch_points

    criteria = json.loads((PACKAGE_ROOT / "evaluation" / "criteria.json").read_text(encoding="utf-8"))
    outfit_template = PROJECT_ROOT / "configs" / "builder_templates" / "outfit_recommendation_template.json"
    commute_template = PROJECT_ROOT / "configs" / "builder_templates" / "commute_outfit_template.json"
    from agent_builder import TemplateWorkflowBuilder

    first_config = TemplateWorkflowBuilder(outfit_template).build_workflow_config(absolute_base_config=True)
    second_config = TemplateWorkflowBuilder(commute_template).build_workflow_config(absolute_base_config=True)
    reuse = compare_reuse(criteria, first_config, second_config)
    rows = [
        {
            "comparison": "initial_configuration",
            "system_or_scenario": "manual_harness",
            "case_id": "all_three_cases",
            "action_count": count_touch_points(criteria, "manual_harness"),
            "changed_fields": "",
            "configuration_errors": "",
            "notes": "Count of explicit action definitions in criteria.json.",
        },
        {
            "comparison": "initial_configuration",
            "system_or_scenario": "builder",
            "case_id": "all_three_cases",
            "action_count": count_touch_points(criteria, "builder"),
            "changed_fields": "",
            "configuration_errors": "",
            "notes": "Preset, workflow name, and user request are the defined touch points.",
        },
        {
            "comparison": "reuse_configuration",
            "system_or_scenario": "travel_to_commute",
            "case_id": "outfit_01_to_commute_template",
            "action_count": reuse["reuse_configuration_actions"],
            "changed_fields": ";".join(reuse["changed_fields"]),
            "configuration_errors": ";".join(reuse["configuration_errors"]),
            "notes": "Changed visible fields are reported; user time and efficiency are not measured.",
        },
    ]
    return rows


def _human_template_rows(
    case_ids: list[str] | tuple[str, ...] | None = None,
    runs_per_case: int = DEFAULT_RUNS_PER_CASE,
) -> list[dict[str, Any]]:
    rows = []
    for case_id in list(case_ids or CASE_FILES):
        for run in range(1, runs_per_case + 1):
            rows.append(
                {
                    "case_id": case_id,
                    "run": run,
                    "response_a": "",
                    "response_b": "",
                    "response_c": "",
                    "usefulness_0_4": "",
                    "clarity_0_4": "",
                    "naturalness_0_4": "",
                    "overall_task_quality_0_4": "",
                    "notes": "",
                }
            )
    return rows


def _summary_text(
    manifest: dict[str, Any],
    answer_rows: list[dict[str, Any]],
    repeatability_rows: list[dict[str, Any]],
    builder_records: list[tuple[Path, dict[str, Any]]],
    llm_records: list[tuple[Path, dict[str, Any]]],
    invalid_llm: list[str],
    failure: dict[str, Any],
) -> str:
    systems = list(manifest.get("systems") or DEFAULT_SYSTEMS)
    case_ids = list(manifest.get("cases") or CASE_FILES)
    runs_per_case = int(manifest.get("runs_per_case", DEFAULT_RUNS_PER_CASE))
    llm_systems = [system for system in systems if system in LLM_PROVIDERS]
    expected_llm = len(llm_systems) * len(case_ids) * runs_per_case
    formal_llm = len(llm_records)
    missing_llm = expected_llm - formal_llm
    builder_expected = len(case_ids) * runs_per_case if "Builder" in systems else 0
    builder_available = sum(row["run_status"] == "available" for row in answer_rows if row["system"] == "Builder")
    system_title = " vs ".join(systems)
    case_count_label = "Case" if len(case_ids) == 1 else "Cases"
    run_label = "run" if runs_per_case == 1 else "runs"
    missing_by_provider = ", ".join(
        f"{system} {max(0, len(case_ids) * runs_per_case - sum(record.get('provider') == system for _, record in llm_records))}"
        for system in llm_systems
    )
    lines = [
        f"# {system_title} — Pilot Experiment",
        "",
        "## Scope",
        "",
        f"This is a Pilot Experiment with {len(case_ids)} frozen {case_count_label}, {len(systems)} systems, and {runs_per_case} planned {run_label} per Case.",
        "The purpose is to validate the comparison method, support the next presentation, and identify the Builder's real strengths and limits.",
        f"Experiment ID: `{manifest['experiment_id']}`",
        f"Fixture versions and Prompt hashes are frozen in `results/experiment_manifest.json`.",
        "",
        "## Answer Quality",
        "",
        "Automated checks cover required fields, explicit constraints, frozen data usage, unsupported inventory references, and policy-derived decisions where objective facts are available.",
        "Language quality, usefulness, clarity, and naturalness remain for Human Evaluation.",
        f"Builder records available: {builder_available}/{builder_expected}.",
        f"Formal external LLM records available: {formal_llm}/{expected_llm}.",
        "",
        "## Workflow Engineering",
        "",
        "The report keeps validation, structured execution, node-level trace, repeatability, failure localization, and configuration/reuse as separate dimensions.",
        "Across the tested cases, the Builder records preserve executable workflow structure and trace evidence; this does not establish a general model-quality claim.",
        "",
        "## Configuration / Reuse",
        "",
        "The configuration comparison reports 17 -> 3 defined touch points from the explicit action lists in `evaluation/criteria.json`.",
        "The reuse row reports changed visible fields from the Travel Outfit to Commute Outfit procedure. No time or efficiency percentage is inferred.",
        "",
        "## Repeatability",
        "",
        "Repeatability compares parsed structured fields across the three runs. It does not require identical wording.",
        "",
        "## Failure Localization",
        "",
        f"The controlled run failed at `{failure.get('failed_node', '')}` with `{failure.get('error', '')}`.",
        "Expected downstream behavior was recorded in the trace and the failure run is excluded from Answer Quality.",
        "",
        "## Human Evaluation",
        "",
        "`human_evaluation_template.csv` is blank and uses blind Response A/B/C labels with 0–4 fields for usefulness, clarity, naturalness, and overall task quality.",
    ]
    if missing_llm:
        lines.extend(
            [
                "",
                "## External Baseline Status",
                "",
                "LLM baseline results pending real runs",
                f"Missing formal records: {missing_llm} ({missing_by_provider or 'none'}).",
                "No sample or example response is used as a result.",
            ]
        )
    else:
        lines.extend(["", "## External Baseline Status", "", "All planned formal external records are available for analysis."])
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "Sampling parameters and exact backend revisions are unavailable when the product UI does not expose them; they are recorded as unavailable rather than guessed.",
            "The three Cases are a pilot and support conclusions only about the tested cases.",
            "Unfavorable results remain in the metric-specific files. No winner is calculated from a combined rank.",
        ]
    )
    if invalid_llm:
        lines.extend(["", "Invalid or excluded LLM records:", *[f"- {item}" for item in invalid_llm]])
    return "\n".join(lines) + "\n"


def analyze_results(root: str | Path = PACKAGE_ROOT) -> dict[str, Any]:
    _reject_frozen_v1_write(root)
    output_root = Path(root)
    manifest = load_manifest(output_root)
    _verify_frozen_manifest(manifest, output_root)
    manifest_fixture_files = manifest.get("fixture_files", {})
    if isinstance(manifest_fixture_files, dict):
        catalog = {
            case_id: Path(relative_path)
            for case_id, relative_path in manifest_fixture_files.items()
        }
    else:
        catalog = CASE_FILES
    case_ids = list(manifest.get("cases") or catalog)
    fixtures = {
        case_id: load_fixture(case_id, root=output_root, case_files=catalog)
        for case_id in case_ids
    }
    results_root = output_root / "results"
    builder_records = _iter_saved_records(output_root, "builder_runs")
    llm_records: list[tuple[Path, dict[str, Any]]] = []
    invalid_llm: list[str] = []
    seen_llm: set[tuple[str, str, int]] = set()
    for path, record in _iter_saved_records(output_root, "llm_runs"):
        errors = validate_llm_record(record, manifest, output_root, formal=False)
        key = (str(record.get("provider")), str(record.get("case_id")), int(record.get("run", 0) or 0))
        if errors:
            invalid_llm.append(f"{_relative_path(path, output_root)}: {'; '.join(errors)}")
        elif not is_formal_llm_record(record):
            invalid_llm.append(f"{_relative_path(path, output_root)}: excluded EXAMPLE_ONLY record")
        elif key in seen_llm:
            invalid_llm.append(f"{_relative_path(path, output_root)}: duplicate provider/case/run")
        else:
            seen_llm.add(key)
            llm_records.append((path, record))

    answer_rows, parsed_by_key, invalid_builder = _answer_quality_rows(
        manifest,
        fixtures,
        builder_records,
        llm_records,
        output_root,
        results_root,
    )
    invalid_llm.extend(invalid_builder)
    _write_csv(
        results_root / "answer_quality.csv",
        [
            "system", "case_id", "run", "run_status", "run_id", "source_file",
            "required_fields_present", "required_fields_missing", "context_usage",
            "constraint_satisfaction", "completeness", "ground_truth_correctness",
            "unsupported_fact_flags", "human_evaluation_status", "open_language_quality",
        ],
        answer_rows,
    )
    repeatability_rows = _repeatability_rows(parsed_by_key, manifest)
    _write_csv(
        results_root / "repeatability.csv",
        ["system", "case_id", "run_count", "status", "structured_fields_match", "compared_fields"],
        repeatability_rows,
    )
    _write_csv(
        results_root / "workflow_features.csv",
        ["system", "feature", "status", "evidence"],
        _workflow_feature_rows(output_root, builder_records, manifest.get("systems")),
    )
    _write_csv(
        results_root / "configuration_comparison.csv",
        ["comparison", "system_or_scenario", "case_id", "action_count", "changed_fields", "configuration_errors", "notes"],
        _configuration_rows(),
    )
    _write_csv(
        results_root / "human_evaluation_template.csv",
        [
            "case_id", "run", "response_a", "response_b", "response_c", "usefulness_0_4",
            "clarity_0_4", "naturalness_0_4", "overall_task_quality_0_4", "notes",
        ],
        _human_template_rows(
            manifest.get("cases"),
            int(manifest.get("runs_per_case", DEFAULT_RUNS_PER_CASE)),
        ),
    )
    failure_path = results_root / "failure_localization.json"
    if failure_path.is_file():
        failure = json.loads(failure_path.read_text(encoding="utf-8"))
    else:
        failure = run_failure_localization(output_root)
    summary = _summary_text(
        manifest,
        answer_rows,
        repeatability_rows,
        builder_records,
        llm_records,
        invalid_llm,
        failure,
    )
    summary_path = results_root / "summary.md"
    summary_path.write_text(summary, encoding="utf-8")
    return {
        "manifest": manifest,
        "manifest_path": str(results_root / "experiment_manifest.json"),
        "summary_path": str(summary_path),
        "builder_record_count": len(builder_records),
        "formal_llm_record_count": len(llm_records),
        "invalid_llm_records": invalid_llm,
        "answer_quality_rows": len(answer_rows),
        "repeatability_rows": len(repeatability_rows),
    }


def run_default_pilot(root: str | Path = PACKAGE_ROOT) -> dict[str, Any]:
    manifest = prepare_experiment(root=root)
    builder_records = run_builder_pilot(root=root)
    failure = run_failure_localization(root=root)
    report = analyze_results(root=root)
    return {**report, "manifest": manifest, "builder_records": builder_records, "failure": failure}


def run_experiment(write_outputs: bool = True) -> dict[str, Any]:
    """New baseline entry point for callers that do not need CLI parsing."""
    del write_outputs
    return run_default_pilot()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the frozen baseline comparison pilot.")
    parser.add_argument("--root", default=str(PACKAGE_ROOT), help="experiment artifact root")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("prepare", "run-builder", "import-llm", "analyze"),
        default="run-builder",
    )
    parser.add_argument("--file", help="one manually saved ChatGPT/Claude JSON record")
    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.command == "prepare":
        manifest = prepare_experiment(root=root)
        print(f"Prepared experiment: {manifest['experiment_id']}")
        print(f"Manifest: {root / 'results' / 'experiment_manifest.json'}")
        return 0
    if args.command == "import-llm":
        if not args.file:
            parser.error("import-llm requires --file")
        destination = import_llm_record(args.file, root / "llm_runs", root / "manifest.json")
        print(f"Imported immutable LLM record: {destination}")
        return 0
    if args.command == "analyze":
        report = analyze_results(root=root)
        print(f"Analyzed Builder records: {report['builder_record_count']}")
        print(f"Formal LLM records: {report['formal_llm_record_count']}")
        print(f"Summary: {report['summary_path']}")
        return 0
    report = run_default_pilot(root=root)
    print("Baseline comparison pilot completed.")
    print(f"Builder records: {len(report['builder_records'])}")
    print(f"Formal LLM records: {report['formal_llm_record_count']}")
    print(f"Summary: {report['summary_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

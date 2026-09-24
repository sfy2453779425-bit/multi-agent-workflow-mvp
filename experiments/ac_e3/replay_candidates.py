"""Replay frozen E2 raw responses through a selected contract validator."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from experiments.ac_formal_v2.common import (  # noqa: E402
    EXPERIMENT_ID,
    frozen_policy,
    frozen_workflow_path,
    prompt_for,
    read_jsonl,
    runtime_result_fields,
    sha256_text,
)
from experiments.authoritative_contract.pilot import pilot as core  # noqa: E402
from agent_builder.generative_provider import RawGenerationResult, parse_candidate  # noqa: E402
from agent_builder.workflow_runtime import (  # noqa: E402
    CONSISTENCY_VALIDATOR_V1_1,
    CONSISTENCY_VALIDATOR_V1_2,
    WorkflowRuntime,
)


E2_RAW = ROOT / "experiments/ac_formal_v2/raw" / EXPERIMENT_ID / "calls.jsonl"
E2_REPLAY = ROOT / "experiments/ac_formal_v2/derived" / EXPERIMENT_ID / "replay.jsonl"
DEV_ROOT = ROOT / "experiments/ac_e3/dev"


class _RecordedProvider:
    provider = "recorded-e2"

    def __init__(self, model: str, raw_text: str):
        self.model = model
        self.raw_text = raw_text

    def generate(self, grounding_projection, generation_contract, request_context):
        candidate, status = parse_candidate(self.raw_text)
        return RawGenerationResult(
            provider=self.provider,
            model=self.model,
            raw_response=self.raw_text,
            parsed_candidate=candidate,
            parse_status=status,
            metadata={"offline_replay": True},
        )


def _replay_one(record: dict[str, Any], validator_version: str) -> dict[str, Any]:
    prompt = prompt_for(record["case_id"])
    if prompt["case_hash"] != record.get("case_hash"):
        raise ValueError(f"{record['case_id']}: frozen case hash mismatch")
    raw_text = record.get("raw_model_text")
    if not isinstance(raw_text, str):
        raise ValueError(f"{record['case_id']} run {record['run_id']}: raw text missing")
    case = deepcopy(prompt["case"])
    policy = frozen_policy()
    core.WORKFLOW_PATH = frozen_workflow_path()
    provider = _RecordedProvider(
        str(record.get("model_returned") or record.get("model_requested") or "not_available"),
        raw_text,
    )
    base_runtime = core._build_runtime(case, policy, provider)
    runtime = WorkflowRuntime(
        base_runtime.workflow_config,
        base_runtime.registry,
        validator_version=validator_version,
    )
    result = runtime.run(
        {
            "user_input": case["request"],
            "support_policy": policy,
            "prompt_policy_context": core._policy_context(
                policy, case["authoritative"]["ticket_category"]
            ),
        }
    )
    fields = runtime_result_fields(result.context)
    parse_status = result.context.get("raw_responses", {}).get("response_generation", {}).get(
        "parse_status"
    )
    final_output = fields["final_output"]
    live = record.get("live_runtime")
    live_matches = None
    if validator_version == CONSISTENCY_VALIDATOR_V1_1 and record.get("provider") == "deepseek":
        if isinstance(live, dict):
            live_matches = (
                live.get("decision") == fields["decision"]
                and live.get("final_output") == final_output
            )
    return {
        "experiment_id": record.get("experiment_id"),
        "case_id": record["case_id"],
        "run_id": record["run_id"],
        "provider": record.get("provider"),
        "model_requested": record.get("model_requested"),
        "model_returned": record.get("model_returned"),
        "raw_response_hash": record.get("raw_response_hash"),
        "parse_status": parse_status,
        "parse_error": None if parse_status == "PARSE_OK" else "existing parser did not produce a valid candidate",
        "candidate": fields["candidate"] if parse_status == "PARSE_OK" else None,
        "runtime_decision": fields["decision"],
        "reject_reason_codes": (
            result.context.get("reject_reason_codes", [])
            if validator_version == CONSISTENCY_VALIDATOR_V1_2
            else fields["reject_reason_codes"]
        ),
        "fallback_used": fields["fallback_used"],
        "fallback_reason": fields["fallback_reason"],
        "final_output": final_output,
        "final_output_hash": sha256_text(final_output) if isinstance(final_output, str) else None,
        "consistency_results": result.context.get("consistency_results", {}).get(
            "response_generation"
        ),
        "live_matches_replay": live_matches,
        "runtime_version": runtime.runtime_version,
        "validator_version": runtime.validator_version,
        "replay_version": "ac-e3-candidate-replay-v1",
        "runtime_error": result.error or None,
    }


def replay(version: str, output: Path | None = None) -> list[dict[str, Any]]:
    validator = {
        "v1.1": CONSISTENCY_VALIDATOR_V1_1,
        "v1.2": CONSISTENCY_VALIDATOR_V1_2,
    }[version]
    raw_rows = read_jsonl(E2_RAW)
    old_rows = read_jsonl(E2_REPLAY)
    if len(raw_rows) != 54 or len(old_rows) != 54:
        raise ValueError("E2 development set must contain exactly 54 raw and replay rows")
    key = lambda row: (row.get("case_id"), row.get("provider"), row.get("run_id"))
    raw_keys = [key(row) for row in raw_rows]
    if len(set(raw_keys)) != 54:
        raise ValueError("duplicate E2 case/provider/run key")
    old_by_key = {key(row): row for row in old_rows}
    if len(old_by_key) != 54 or set(raw_keys) != set(old_by_key):
        raise ValueError("E2 raw and recorded replay keys do not match")
    rows = [_replay_one(record, validator) for record in raw_rows]
    for row in rows:
        old = old_by_key[key(row)]
        if row["raw_response_hash"] != old.get("raw_response_hash"):
            raise ValueError(f"raw response hash mismatch: {key(row)}")
        if row["parse_status"] != old.get("parse_status") or row["candidate"] != old.get("candidate"):
            raise ValueError(f"candidate parser mismatch: {key(row)}")
    if version == "v1.1":
        for row in rows:
            old = old_by_key[key(row)]
            if row["runtime_decision"] != old.get("runtime_decision"):
                raise ValueError(f"v1.1 decision mismatch: {key(row)}")
            if row["final_output"] != old.get("final_output"):
                raise ValueError(f"v1.1 final output mismatch: {key(row)}")
    target = output or DEV_ROOT / f"e2_{version.replace('.', '_')}_replay.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
        for row in rows
    )
    target.write_text(text, encoding="utf-8", newline="\n")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, choices=("v1.1", "v1.2"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = replay(args.version, args.output)
    print(json.dumps({"version": args.version, "rows": len(rows), "output": str(args.output or DEV_ROOT / f"e2_{args.version.replace('.', '_')}_replay.jsonl")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

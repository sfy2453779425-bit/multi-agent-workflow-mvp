from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any

from experiments.ac_formal_v2.common import (
    BASE,
    EXPERIMENT_ID,
    append_jsonl,
    core,
    frozen_policy,
    frozen_workflow_path,
    load_json,
    prompt_for,
    read_jsonl,
    runtime_result_fields,
    sha256_text,
)
from agent_builder.generative_provider import RawGenerationResult, parse_candidate


REPLAY_VERSION = "ac-formal-replay-v1"


class _RecordedProvider:
    def __init__(self, provider: str, model: str, raw_text: str | None):
        self.provider = provider
        self.model = model
        self.raw_text = raw_text or ""

    def generate(self, grounding_projection, generation_contract, request_context):
        candidate, status = parse_candidate(self.raw_text)
        return RawGenerationResult(
            provider=self.provider,
            model=self.model,
            raw_response=self.raw_text,
            parsed_candidate=candidate,
            parse_status=status,
            metadata={"replay": True, "sampling_parameters": "unavailable", "exact_backend_revision": "unavailable"},
        )


def replay_one(record: dict[str, Any]) -> dict[str, Any]:
    prompt = prompt_for(record["case_id"])
    policy = frozen_policy()
    core.WORKFLOW_PATH = frozen_workflow_path()
    case = deepcopy(prompt["case"])
    provider = _RecordedProvider(record["provider"], str(record.get("model_returned") or record["model_requested"]), record.get("raw_text"))
    runtime = core._build_runtime(case, policy, provider)
    result = runtime.run({
        "user_input": case["request"],
        "support_policy": policy,
        "prompt_policy_context": core._policy_context(policy, case["authoritative"]["ticket_category"]),
    })
    runtime_fields = runtime_result_fields(result.context)
    parse_status = result.context.get("raw_responses", {}).get("response_generation", {}).get("parse_status")
    final_output = runtime_fields["final_output"]
    runtime_decision = runtime_fields["decision"]
    live = record.get("live_runtime")
    live_matches = None
    if record.get("provider") == "deepseek" and isinstance(live, dict):
        live_matches = (
            live.get("decision") == runtime_decision
            and live.get("final_output") == final_output
        )
    return {
        "experiment_id": record["experiment_id"],
        "case_id": record["case_id"],
        "run_id": record["run_id"],
        "provider": record["provider"],
        "model_requested": record["model_requested"],
        "model_returned": record.get("model_returned"),
        "raw_response_hash": record.get("raw_response_hash"),
        "parse_status": parse_status,
        "parse_error": None if parse_status == "PARSE_OK" else "existing parser did not produce a valid candidate",
        "candidate": runtime_fields["candidate"] if parse_status == "PARSE_OK" else None,
        "runtime_decision": runtime_decision,
        "reject_reason_codes": runtime_fields["reject_reason_codes"],
        "fallback_used": runtime_fields["fallback_used"],
        "fallback_reason": runtime_fields["fallback_reason"],
        "final_output": final_output,
        "final_output_hash": sha256_text(final_output) if isinstance(final_output, str) else None,
        "live_matches_replay": live_matches,
        "runtime_version": "authoritative-contract-v1.1",
        "validator_version": "consistency-validator-v1.1",
        "replay_version": REPLAY_VERSION,
        "runtime_error": result.error or None,
    }


def run(smoke: bool) -> list[dict[str, Any]]:
    if smoke:
        source = BASE / "smoke" / "calls.jsonl"
        target = BASE / "smoke" / "replay.jsonl"
    else:
        source = BASE / "raw" / EXPERIMENT_ID / "calls.jsonl"
        target = BASE / "derived" / EXPERIMENT_ID / "replay.jsonl"
    raw_rows = read_jsonl(source)
    existing = read_jsonl(target)
    done = {(item.get("case_id"), item.get("provider"), item.get("run_id")) for item in existing}
    new_rows = []
    for record in raw_rows:
        key = (record.get("case_id"), record.get("provider"), record.get("run_id"))
        if key in done:
            continue
        replayed = replay_one(record)
        append_jsonl(target, replayed)
        new_rows.append(replayed)
        done.add(key)
    return existing + new_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args.smoke)
    except Exception as exc:
        print(str(exc))
        return 2
    if args.smoke:
        print(json.dumps([
            {"provider": row["provider"], "parse_status": row["parse_status"], "runtime_decision": row["runtime_decision"], "live_matches_replay": row["live_matches_replay"]}
            for row in result
        ], ensure_ascii=False))
    else:
        print(json.dumps({"replay_rows": len(result), "experiment_id": EXPERIMENT_ID}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Deterministic evaluator for the frozen AC Formal V2 comparison."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[1]
EVALUATOR_VERSION = "ac-eval-v1.0.1"
CASE_SOURCE = REPO_ROOT / "experiments" / "authoritative_contract" / "pilot_v4" / "cases_v1.json"
CASE_SOURCE_SHA256 = hashlib.sha256(CASE_SOURCE.read_bytes()).hexdigest()
EXPECTED_CASE_SOURCE_SHA256 = "893bff0ca567c2fab8e54b865a16d41eb89f554c335b9afb12bede62910e1b1f"
if CASE_SOURCE_SHA256 != EXPECTED_CASE_SOURCE_SHA256:
    raise RuntimeError("frozen case source SHA-256 does not match the reviewed RULES.md input")
with CASE_SOURCE.open("r", encoding="utf-8-sig") as _frozen_file:
    _frozen_cases = json.load(_frozen_file)["cases"]
CASE_AUTHORITIES = {
    str(case["case_id"]): {key: case["authoritative"][key] for key in ("priority", "sla", "owner_team")}
    for case in _frozen_cases
}
EXPECTED_CASE_IDS = {"CS01", "CS04", "CS06", "CS08", "CS10", "CS12"}
if set(CASE_AUTHORITIES) != EXPECTED_CASE_IDS or len({tuple(v.items()) for v in CASE_AUTHORITIES.values()}) != 1:
    raise RuntimeError("frozen case authority mapping is incomplete or inconsistent")
AUTHORITY = CASE_AUTHORITIES["CS01"]

with (BASE_DIR / "field_map.json").open("r", encoding="utf-8-sig") as f:
    FIELD_MAP = json.load(f)
MESSAGE_FIELDS = [x.casefold() for x in FIELD_MAP["message_fields"]]
ALLOWED_FIELDS = {x.casefold() for x in FIELD_MAP["allowed_output_fields"]}
AUTHORITY_ALIASES = {k: [x.casefold() for x in v] for k, v in FIELD_MAP["authority_fields"].items()}
KNOWN_TEAMS = FIELD_MAP["team_names"]
TEAM_BASES = ["Logistics", "Billing", "Account", "Technical"]
TEAM_SUFFIXES = ["Support", "team", "department"]

NUMBER_WORDS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "twenty-one": 21, "twenty-two": 22,
    "twenty-three": 23, "twenty-four": 24,
}
_NUMBER_FORMS: list[str] = []
for _phrase in NUMBER_WORDS:
    _NUMBER_FORMS.append(re.escape(_phrase).replace(r"\-", r"[-\s]+"))
_NUMBER_PATTERN = "(?:" + "|".join(sorted(_NUMBER_FORMS, key=len, reverse=True)) + ")"
_NUMBER_RE = re.compile(rf"(?<![\w])(?P<number>\d+(?:\.\d+)?|{_NUMBER_PATTERN})(?![\w])", re.I)
_DURATION_RE = re.compile(
    rf"(?<![\w])(?P<number>\d+(?:\.\d+)?|{_NUMBER_PATTERN})\s*(?P<unit>business\s+days?|working\s+days?|hours?|hrs?\.?|h\b|minutes?|mins?\.?|m\b|days?)(?![\w])",
    re.I,
)
_COMMITMENT_RE = re.compile(
    r"\b(?:within|no\s+later\s+than|at\s+most|by|will\s+(?:reply|respond|answer|get\s+back\s+to\s+you)\s+in|we['’]ll\s+(?:reply|respond|answer)\s+in)\b",
    re.I,
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|[;\r\n]+")
_PRIORITY_RE = re.compile(r"(?<![A-Z0-9])P[0-4](?![A-Z0-9])", re.I)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: each JSONL record must be an object")
            rows.append(row)
    return rows


def json_object(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None
    return value


def walk_fields(value: Any, path: str = "$", parents: tuple[str, ...] = ()) -> Iterable[tuple[str, str, Any, tuple[str, ...]]]:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            yield key_text, child_path, child, parents
            yield from walk_fields(child, child_path, parents + (key_text,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_fields(child, f"{path}[{index}]", parents)


def find_message(value: Any) -> tuple[str | None, str | None, Any]:
    for key, path, child, _parents in walk_fields(value):
        if key.casefold() in MESSAGE_FIELDS:
            return key, path, child
    return None, None, None


def has_exact_customer_message(value: Any) -> tuple[bool, Any, str | None]:
    for key, path, child, _parents in walk_fields(value):
        if key.casefold() == "customer_message":
            return child is not None, child, path
    return False, None, None


def parse_success(status: Any) -> bool:
    if isinstance(status, bool):
        return status
    if status is None:
        return False
    text = str(status).strip().casefold().replace("-", "_").replace(" ", "_")
    if any(word in text for word in ("fail", "error", "invalid", "unparsed")):
        return False
    return text in {"ok", "success", "parsed", "valid", "parse_success", "parse_ok", "ok_json", "parsed_json", "succeeded", "pass", "true"}


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().casefold() in {"true", "1", "yes", "y", "on", "used"}


def _number_value(text: str) -> float | None:
    normalized = text.strip().casefold().replace("-", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    if re.fullmatch(r"\d+(?:\.\d+)?", normalized):
        return float(normalized)
    lookup = normalized.replace(" ", "-")
    return float(NUMBER_WORDS[lookup]) if lookup in NUMBER_WORDS else None


def parse_duration(value: Any, key: str = "sla") -> tuple[float | str | None, str]:
    """Return minutes, or 'business_day' for a deliberately non-converted workday."""
    if isinstance(value, bool) or value is None or isinstance(value, (dict, list)):
        return None, "unparseable"
    key_norm = re.sub(r"[^a-z0-9]", "", key.casefold())
    if isinstance(value, (int, float)):
        if key_norm == "slaminutes":
            return float(value), "numeric_minutes"
        if key_norm == "slahours":
            return float(value) * 60, "numeric_hours"
        return None, "unparseable"
    text = str(value).strip().casefold()
    # A bare number is accepted only when the field name declares its unit.
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        if key_norm == "slaminutes":
            return float(text), "numeric_minutes"
        if key_norm == "slahours":
            return float(text) * 60, "numeric_hours"
        return None, "unparseable"
    match = _DURATION_RE.search(text)
    if not match:
        return None, "unparseable"
    amount = _number_value(match.group("number"))
    if amount is None:
        return None, "unparseable"
    unit = re.sub(r"[^a-z]", "", match.group("unit").casefold())
    if unit in {"businessday", "businessdays", "workingday", "workingdays"}:
        return "business_day", "business_day"
    if unit in {"hour", "hours", "hr", "hrs", "h"}:
        return amount * 60, "hours"
    if unit in {"minute", "minutes", "min", "mins", "m"}:
        return amount, "minutes"
    if unit in {"day", "days"}:
        return amount * 1440, "calendar_days"
    return None, "unparseable"


def normalize_priority(value: Any) -> str | None:
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return None
    text = re.sub(r"\s+", "", str(value)).upper()
    return text if re.fullmatch(r"P[0-4]", text) else None


def normalize_team(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def team_forms(base: str) -> list[str]:
    return [f"{base} {suffix}" for suffix in TEAM_SUFFIXES]


def accepted_authority_team_forms() -> set[str]:
    forms = ["Logistics Support", *team_forms("Logistics")]
    return {normalize_team(x) or "" for x in forms}


def field_matches(field: str, key: str, value: Any) -> tuple[bool, str]:
    expected = AUTHORITY[field]
    if field == "priority":
        actual = normalize_priority(value)
        return actual == expected, "unparseable" if actual is None else actual
    if field == "sla":
        minutes, parse_kind = parse_duration(value, key)
        return isinstance(minutes, (int, float)) and abs(float(minutes) - 240) < 1e-9, parse_kind if minutes is None or isinstance(minutes, str) else f"{minutes:g} minutes"
    normalized = normalize_team(value)
    return normalized in accepted_authority_team_forms(), "unparseable" if normalized is None else normalized


def _authority_occurrences(value: Any, field: str) -> list[tuple[str, Any]]:
    alias_set = set(AUTHORITY_ALIASES[field])
    return [(path, child) for key, path, child, _parents in walk_fields(value) if key.casefold() in alias_set]


def _candidate_occurrences(value: Any, field: str) -> list[tuple[str, Any]]:
    # The three scored authority fields are forbidden in C, so any occurrence is unauthorized.
    return _authority_occurrences(value, field)


def unauthorized_fields(value: Any) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for key, path, _child, _parents in walk_fields(value):
        if key.casefold() not in ALLOWED_FIELDS:
            found.append({"path": path, "field": key})
    return found


def unknown_authority_like_fields(value: Any) -> list[dict[str, str]]:
    known = {alias for aliases in AUTHORITY_ALIASES.values() for alias in aliases}
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for key, path, _child, _parents in walk_fields(value):
        compact = re.sub(r"[^a-z0-9]", "", key.casefold())
        if key.casefold() in known:
            continue
        if any(marker in compact for marker in ("priority", "prio", "sla", "owner", "team", "assignee")):
            item = (path, key)
            if item not in seen:
                result.append({"path": path, "field": key})
                seen.add(item)
    return result


def _text_leaves(value: Any, path: str) -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, list):
        out: list[tuple[str, str]] = []
        for i, child in enumerate(value):
            out.extend(_text_leaves(child, f"{path}[{i}]"))
        return out
    if isinstance(value, dict):
        out = []
        for key, child in value.items():
            out.extend(_text_leaves(child, f"{path}.{key}"))
        return out
    return []


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _team_pattern(team: str) -> re.Pattern[str]:
    parts = [re.escape(x) for x in team.split()]
    return re.compile(r"(?<!\w)" + r"[\s\W_]+".join(parts) + r"(?!\w)", re.I)


OTHER_TEAM_FORMS = [form for base in ("Billing", "Account", "Technical") for form in team_forms(base)]
AUTHORITY_TEAM_FORMS = team_forms("Logistics")
_OTHER_TEAM_PATTERNS = [(form, _team_pattern(form)) for form in OTHER_TEAM_FORMS]
_AUTH_TEAM_PATTERNS = [_team_pattern(form) for form in AUTHORITY_TEAM_FORMS]
_TEAM_VERB_RE = re.compile(r"\b(?:handles?|handled|handling|assigns?|assigned|assigning|routes?|routed|routing|transfers?|transferred|transferring|forwards?|forwarded|forwarding|escalates?\s+to)\b", re.I)


def scan_text(text: str, path: str, view: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for sentence in split_sentences(text):
        priorities = {x.upper() for x in _PRIORITY_RE.findall(sentence)}
        if any(priority != AUTHORITY["priority"] for priority in priorities) and AUTHORITY["priority"] not in priorities:
            hits.append({"rule": "T1", "path": path, "snippet": sentence, "matched": sorted(priorities)})

        duration_matches: list[tuple[str, float | str | None]] = []
        for match in _DURATION_RE.finditer(sentence):
            amount = _number_value(match.group("number"))
            if amount is None:
                continue
            unit = re.sub(r"[^a-z]", "", match.group("unit").casefold())
            if unit.startswith("business") or unit.startswith("working"):
                minutes: float | str = "business_day"
            elif unit in {"hour", "hours", "hr", "hrs", "h"}:
                minutes = amount * 60
            elif unit in {"minute", "minutes", "min", "mins", "m"}:
                minutes = amount
            else:
                minutes = amount * 1440
            duration_matches.append((match.group(0), minutes))
        if duration_matches and _COMMITMENT_RE.search(sentence):
            has_authoritative_duration = any(isinstance(minutes, (int, float)) and abs(float(minutes) - 240) < 1e-9 for _raw, minutes in duration_matches)
            conflicting = [(raw, minutes) for raw, minutes in duration_matches if minutes == "business_day" or isinstance(minutes, (int, float)) and abs(float(minutes) - 240) >= 1e-9]
            if conflicting and not has_authoritative_duration:
                hits.append({"rule": "T2", "path": path, "snippet": sentence, "matched": [raw for raw, _minutes in conflicting]})

        other_teams = [form for form, pattern in _OTHER_TEAM_PATTERNS if pattern.search(sentence)]
        authority_team_present = any(pattern.search(sentence) for pattern in _AUTH_TEAM_PATTERNS)
        if other_teams and _TEAM_VERB_RE.search(sentence) and not authority_team_present:
            hits.append({"rule": "T3", "path": path, "snippet": sentence, "matched": sorted(set(other_teams))})
    return hits


def score_view(name: str, value: Any, available: bool, candidate_mode: bool = False) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for field in ("priority", "sla", "owner_team"):
        occurrences = _candidate_occurrences(value, field) if candidate_mode else _authority_occurrences(value, field)
        if not occurrences:
            fields[field] = {"status": "missing", "occurrences": []}
            continue
        details = []
        for path, raw in occurrences:
            matches, normalized = field_matches(field, path.rsplit(".", 1)[-1].split("[")[0], raw)
            details.append({"path": path, "value": raw, "normalized": normalized, "matches_authority": matches})
        fields[field] = {"status": "consistent" if all(x["matches_authority"] for x in details) else "conflict", "occurrences": details}

    message_key, message_path, message_value = find_message(value)
    text_hits: list[dict[str, Any]] = []
    if message_key is not None:
        for leaf_path, text in _text_leaves(message_value, message_path or "$"):
            text_hits.extend(scan_text(text, leaf_path, name))
    fields_conflict = any(fields[k]["status"] == "conflict" for k in fields)
    text_conflict = bool(text_hits)
    extra = unauthorized_fields(value) if candidate_mode and value is not None else []
    unknown_aliases = unknown_authority_like_fields(value) if candidate_mode and value is not None else []
    return {
        "field_status": fields,
        "unauthorized_fields": extra,
        "unauthorized_field_count": len(extra),
        "unknown_authority_like_fields": unknown_aliases,
        "text_field": {"key": message_key, "path": message_path},
        "text_hits": text_hits,
        "field_conflict": fields_conflict,
        "text_conflict": text_conflict,
        "has_conflict": fields_conflict or text_conflict,
        "has_violation": fields_conflict or text_conflict or bool(extra),
        "no_usable_output": not available,
    }


def make_o_view(candidate: Any) -> Any:
    if candidate is None:
        return None
    _key, _path, message = find_message(candidate)
    repaired: dict[str, Any] = {}
    if _key is not None:
        repaired["customer_message"] = copy.deepcopy(message)
    repaired.update(AUTHORITY)
    return repaired


def _find_call(replay: dict[str, Any], calls: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    keys = ("experiment_id", "case_id", "run_id")
    candidates = [c for c in calls if all(c.get(k) == replay.get(k) for k in keys)]
    for field in ("provider", "model_requested"):
        value = replay.get(field)
        if value is not None:
            candidates = [c for c in candidates if c.get(field) == value]
    if len(candidates) == 1:
        return candidates[0], "matched"
    return None, "missing" if not candidates else "ambiguous"


def model_family(row: dict[str, Any]) -> str:
    text = " ".join(str(row.get(k, "")) for k in ("model_requested", "model_returned", "provider")).casefold()
    if "deepseek" in text:
        return "DeepSeek"
    if "claude" in text or "anthropic" in text:
        return "Claude"
    if "gpt" in text or "openai" in text:
        return "GPT"
    return str(row.get("model_requested") or row.get("provider") or "Unknown")


def _call_metadata(call: dict[str, Any] | None) -> dict[str, Any]:
    if call is None:
        return {}
    fields = (
        "provider", "model_requested", "model_returned", "timestamp_start_utc", "timestamp_end_utc",
        "latency_ms", "prompt_text_hash", "params_sent", "params_unsupported", "finish_reason",
        "transport_failure", "live_runtime", "runtime_version", "validator_version",
        "response_id", "call_path", "live_matches_replay",
    )
    return {key: call.get(key) for key in fields if key in call}


def evaluate_rows(replay_rows: list[dict[str, Any]], calls_rows: list[dict[str, Any]], replay_sha: str, calls_sha: str) -> list[dict[str, Any]]:
    evaluated: list[dict[str, Any]] = []
    for replay in replay_rows:
        call, join_status = _find_call(replay, calls_rows)
        candidate_raw = json_object(replay.get("candidate"))
        candidate_parse_ok = parse_success(replay.get("parse_status"))
        exact_message_present, exact_message, _exact_path = has_exact_customer_message(candidate_raw)
        candidate_available = candidate_parse_ok and candidate_raw is not None and exact_message_present
        candidate_scoring_value = candidate_raw if candidate_parse_ok else None
        c_view = score_view("C", candidate_scoring_value, candidate_available, candidate_mode=True)

        o_value = make_o_view(candidate_scoring_value) if candidate_scoring_value is not None else None
        o_available = candidate_available and o_value is not None
        o_view = score_view("O", o_value, o_available)

        final_output = replay.get("final_output")
        if isinstance(final_output, str):
            # Replay stores the runtime's final customer message as a plain string.
            # Wrap it only for D-view message extraction; no structured authority
            # fields are introduced, so all three field statuses remain missing.
            final_value = {"customer_message": final_output}
            d_available = True
        else:
            final_value = json_object(final_output)
            final_message_key, _final_message_path, final_message = find_message(final_value)
            d_available = final_value is not None and final_message_key is not None and final_message is not None
        d_view = score_view("D", final_value, d_available)

        decision = str(replay.get("runtime_decision", "")).upper()
        fallback = truthy(replay.get("fallback_used"))
        candidate_conflict = c_view["has_conflict"]
        final_conflict = d_view["has_conflict"]
        candidate_parsed = candidate_parse_ok and candidate_raw is not None
        classification = {
            "intercept": candidate_conflict and not final_conflict,
            "leak": candidate_conflict and final_conflict,
            "false_reject": candidate_parsed and not candidate_conflict and (decision == "REJECT" or fallback),
            "normal_pass": candidate_parsed and not candidate_conflict and decision == "ACCEPT",
            "parse_failure_fallback": not candidate_parse_ok and fallback,
        }
        row = {
            "experiment_id": replay.get("experiment_id"),
            "case_id": replay.get("case_id"),
            "run_id": replay.get("run_id"),
            "provider": replay.get("provider"),
            "model_requested": replay.get("model_requested") or (call or {}).get("model_requested"),
            "model_returned": replay.get("model_returned") or (call or {}).get("model_returned"),
            "model": model_family({**replay, **(call or {})}),
            "parse_status": replay.get("parse_status"),
            "parse_success": candidate_parse_ok,
            "candidate_parsed": candidate_parsed,
            "runtime_decision": decision,
            "fallback_used": fallback,
            "reject_reason_codes": replay.get("reject_reason_codes"),
            "call_join_status": join_status,
            "evaluator_version": EVALUATOR_VERSION,
            "input_sha256": {"replay": replay_sha, "calls": calls_sha},
            "authority_source_sha256": CASE_SOURCE_SHA256,
            "views": {"C": c_view, "O": o_view, "D": d_view},
            "classification": classification,
            "call_metadata": _call_metadata(call),
            "live_matches_replay": replay.get("live_matches_replay") if replay.get("live_matches_replay") is not None else (call or {}).get("live_matches_replay"),
            "runtime_version": replay.get("runtime_version") or (call or {}).get("runtime_version"),
            "validator_version": replay.get("validator_version") or (call or {}).get("validator_version"),
        }
        evaluated.append(row)
    return evaluated


def infer_experiment_id(rows: list[dict[str, Any]]) -> str:
    values = {str(r.get("experiment_id") or "unknown") for r in rows}
    if len(values) > 1:
        raise ValueError(f"expected one experiment_id, found {sorted(values)}")
    return next(iter(values), "unknown")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", required=True, type=Path, help="replay.jsonl input")
    parser.add_argument("--calls", required=True, type=Path, help="calls.jsonl input")
    parser.add_argument("--output", type=Path, help="output JSONL path (default: out/<EXPERIMENT_ID>/evaluation.jsonl)")
    args = parser.parse_args(argv)
    try:
        replay_rows = read_jsonl(args.replay)
        calls_rows = read_jsonl(args.calls)
        rows = evaluate_rows(replay_rows, calls_rows, sha256_file(args.replay), sha256_file(args.calls))
        exp_id = infer_experiment_id(rows)
        output = args.output or (BASE_DIR / "out" / exp_id / "evaluation.jsonl")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="\n") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        print(f"Wrote {len(rows)} evaluated rows to {output}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"evaluate.py: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

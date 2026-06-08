#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen2.5-1.5B-Instruct}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-9100}"
DEVICE="${DEVICE:-cuda:0}"
ADAPTER_PATH="${ADAPTER_PATH:-}"

source .venv/bin/activate

ARGS=(
  --host "$HOST"
  --port "$PORT"
  --model "$MODEL"
  --device "$DEVICE"
)

if [ -n "$ADAPTER_PATH" ]; then
  ARGS+=(--adapter-path "$ADAPTER_PATH")
fi

python local_llm_api_server.py "${ARGS[@]}"

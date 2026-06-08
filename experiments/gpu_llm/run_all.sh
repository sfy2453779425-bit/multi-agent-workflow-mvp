#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen2.5-1.5B-Instruct}"

bash check_env.sh
bash setup_env.sh
source .venv/bin/activate
python run_qwen_test.py --model "$MODEL"
python benchmark_llm.py --model "$MODEL"

echo "Done. Check the results/ directory."


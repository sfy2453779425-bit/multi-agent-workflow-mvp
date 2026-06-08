#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen2.5-1.5B-Instruct}"
EPOCHS="${EPOCHS:-2}"
OUTPUT_DIR="${OUTPUT_DIR:-lora_outputs/$(echo "$MODEL" | tr '/:' '__')_workflow_builder}"

bash setup_env.sh
source .venv/bin/activate

python prepare_sft_dataset.py --output data/workflow_builder_sft.jsonl --repeat 8

python finetune_qwen_lora.py \
  --model "$MODEL" \
  --train-file data/workflow_builder_sft.jsonl \
  --output-dir "$OUTPUT_DIR" \
  --epochs "$EPOCHS"

python eval_lora_adapter.py \
  --model "$MODEL" \
  --adapter "$OUTPUT_DIR/final_adapter" \
  --output "$OUTPUT_DIR/adapter_eval.json"

echo
echo "Training complete."
echo "Adapter: $OUTPUT_DIR/final_adapter"
echo "Evaluation: $OUTPUT_DIR/adapter_eval.json"


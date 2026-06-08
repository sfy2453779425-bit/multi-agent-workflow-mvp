#!/usr/bin/env bash
set -euo pipefail

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

MODEL="${MODEL:-Qwen/Qwen2.5-1.5B-Instruct}"
EPOCHS="${EPOCHS:-2}"
TARGET_COUNT="${TARGET_COUNT:-160}"
OUTPUT_DIR="${OUTPUT_DIR:-lora_outputs/$(echo "$MODEL" | tr '/:' '__')_workflow_builder_v2}"
TRAIN_FILE="${TRAIN_FILE:-data/workflow_builder_sft_v2.jsonl}"
SUMMARY_FILE="${SUMMARY_FILE:-data/workflow_builder_sft_v2_summary.json}"

bash setup_env.sh
source .venv/bin/activate

python prepare_sft_dataset.py \
  --output "$TRAIN_FILE" \
  --target-count "$TARGET_COUNT" \
  --summary "$SUMMARY_FILE"

python finetune_qwen_lora.py \
  --model "$MODEL" \
  --train-file "$TRAIN_FILE" \
  --output-dir "$OUTPUT_DIR" \
  --epochs "$EPOCHS"

python eval_lora_adapter.py \
  --model "$MODEL" \
  --adapter "$OUTPUT_DIR/final_adapter" \
  --output "$OUTPUT_DIR/adapter_eval.json"

echo
echo "V2 training complete."
echo "Dataset: $TRAIN_FILE"
echo "Dataset summary: $SUMMARY_FILE"
echo "Adapter: $OUTPUT_DIR/final_adapter"
echo "Evaluation: $OUTPUT_DIR/adapter_eval.json"

#!/usr/bin/env bash
set -euo pipefail

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

MODEL="${MODEL:-Qwen/Qwen2.5-1.5B-Instruct}"
OLD_ADAPTER="${OLD_ADAPTER:-lora_outputs/Qwen_Qwen2.5-1.5B-Instruct_workflow_builder/final_adapter}"
NEW_ADAPTER="${NEW_ADAPTER:-lora_outputs/Qwen_Qwen2.5-1.5B-Instruct_workflow_builder_v2/final_adapter}"
PROMPTS="${PROMPTS:-eval_prompts.json}"
OUTPUT_DIR="${OUTPUT_DIR:-results/v2_lora_comparison}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-260}"

mkdir -p "$OUTPUT_DIR"

echo "== V2 LoRA comparison =="
echo "MODEL=$MODEL"
echo "OLD_ADAPTER=$OLD_ADAPTER"
echo "NEW_ADAPTER=$NEW_ADAPTER"
echo "PROMPTS=$PROMPTS"
echo "OUTPUT_DIR=$OUTPUT_DIR"

python compare_base_lora.py \
  --model "$MODEL" \
  --prompts "$PROMPTS" \
  --output-dir "$OUTPUT_DIR" \
  --max-new-tokens "$MAX_NEW_TOKENS"

if [ -d "$OLD_ADAPTER" ]; then
  python compare_base_lora.py \
    --model "$MODEL" \
    --adapter "$OLD_ADAPTER" \
    --prompts "$PROMPTS" \
    --output-dir "$OUTPUT_DIR" \
    --max-new-tokens "$MAX_NEW_TOKENS"
else
  echo "Skip old LoRA: adapter not found at $OLD_ADAPTER"
fi

if [ -d "$NEW_ADAPTER" ]; then
  python compare_base_lora.py \
    --model "$MODEL" \
    --adapter "$NEW_ADAPTER" \
    --prompts "$PROMPTS" \
    --output-dir "$OUTPUT_DIR" \
    --max-new-tokens "$MAX_NEW_TOKENS"
else
  echo "Skip new LoRA: adapter not found at $NEW_ADAPTER"
fi

python aggregate_base_lora_results.py \
  --input-dir "$OUTPUT_DIR" \
  --output "$OUTPUT_DIR/v2_lora_summary.md"

echo "== Done =="
echo "Summary: $OUTPUT_DIR/v2_lora_summary.md"

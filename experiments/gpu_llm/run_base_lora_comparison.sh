#!/usr/bin/env bash
set -euo pipefail

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

MODEL_15B="${MODEL_15B:-Qwen/Qwen2.5-1.5B-Instruct}"
MODEL_7B="${MODEL_7B:-Qwen/Qwen2.5-7B-Instruct}"
ADAPTER_15B="${ADAPTER_15B:-lora_outputs/Qwen_Qwen2.5-1.5B-Instruct_workflow_builder/final_adapter}"
ADAPTER_7B="${ADAPTER_7B:-lora_outputs/qwen25_7b_workflow_builder/final_adapter}"
PROMPTS="${PROMPTS:-eval_prompts.json}"
OUTPUT_DIR="${OUTPUT_DIR:-results/base_lora_comparison}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-260}"

mkdir -p "$OUTPUT_DIR"

echo "== Base vs LoRA comparison =="
echo "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"
echo "PROMPTS=$PROMPTS"
echo "OUTPUT_DIR=$OUTPUT_DIR"

python compare_base_lora.py \
  --model "$MODEL_15B" \
  --prompts "$PROMPTS" \
  --output-dir "$OUTPUT_DIR" \
  --max-new-tokens "$MAX_NEW_TOKENS"

if [ -d "$ADAPTER_15B" ]; then
  python compare_base_lora.py \
    --model "$MODEL_15B" \
    --adapter "$ADAPTER_15B" \
    --prompts "$PROMPTS" \
    --output-dir "$OUTPUT_DIR" \
    --max-new-tokens "$MAX_NEW_TOKENS"
else
  echo "Skip 1.5B LoRA: adapter not found at $ADAPTER_15B"
fi

python compare_base_lora.py \
  --model "$MODEL_7B" \
  --prompts "$PROMPTS" \
  --output-dir "$OUTPUT_DIR" \
  --max-new-tokens "$MAX_NEW_TOKENS"

if [ -d "$ADAPTER_7B" ]; then
  python compare_base_lora.py \
    --model "$MODEL_7B" \
    --adapter "$ADAPTER_7B" \
    --prompts "$PROMPTS" \
    --output-dir "$OUTPUT_DIR" \
    --max-new-tokens "$MAX_NEW_TOKENS"
else
  echo "Skip 7B LoRA: adapter not found at $ADAPTER_7B"
fi

python aggregate_base_lora_results.py \
  --input-dir "$OUTPUT_DIR" \
  --output "$OUTPUT_DIR/base_lora_summary.md"

echo "== Done =="
echo "Summary: $OUTPUT_DIR/base_lora_summary.md"

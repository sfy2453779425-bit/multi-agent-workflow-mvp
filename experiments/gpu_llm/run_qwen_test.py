import argparse
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


DEFAULT_PROMPT = (
    "I will travel to Qingdao next week. "
    "Recommend an outfit using weather, shopping history, and style preference. "
    "Answer in Korean with concise reasoning and a ranked list."
)


def gpu_snapshot() -> dict:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        ).strip()
        if not output:
            return {}
        first = output.splitlines()[0]
        index, name, mem_total, mem_used, util = [part.strip() for part in first.split(",")]
        return {
            "index": index,
            "name": name,
            "memory_total_mb": int(mem_total),
            "memory_used_mb": int(mem_used),
            "gpu_utilization_percent": int(util),
        }
    except Exception as exc:
        return {"error": str(exc)}


def pick_dtype(name: str):
    if name == "float16":
        return torch.float16
    if name == "bfloat16":
        return torch.bfloat16
    if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    return torch.float16 if torch.cuda.is_available() else torch.float32


def build_prompt(tokenizer, user_prompt: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a local LLM compose node for a multi-agent workflow. "
                "Use the provided request to produce a practical recommendation."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return f"System: {messages[0]['content']}\nUser: {user_prompt}\nAssistant:"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one local Qwen inference test.")
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--max-new-tokens", type=int, default=220)
    parser.add_argument("--dtype", choices=["auto", "float16", "bfloat16"], default="auto")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        print("ERROR: CUDA is not available. Run check_env.sh first.")
        return 1

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    dtype = pick_dtype(args.dtype)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Model: {args.model}")
    print(f"dtype: {dtype}")
    print("GPU before load:", gpu_snapshot())

    load_start = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(
        args.model,
        trust_remote_code=True,
        local_files_only=args.local_files_only,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=dtype,
        device_map="auto",
        trust_remote_code=True,
        local_files_only=args.local_files_only,
    )
    if hasattr(model, "eval"):
        model.eval()
    load_seconds = time.perf_counter() - load_start

    prompt_text = build_prompt(tokenizer, args.prompt)
    inputs = tokenizer(prompt_text, return_tensors="pt")
    device = next(model.parameters()).device
    inputs = {key: value.to(device) for key, value in inputs.items()}

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()

    infer_start = time.perf_counter()
    with torch.no_grad():
        generated = model.generate(
            **inputs,
            max_new_tokens=args.max_new_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
            pad_token_id=tokenizer.eos_token_id,
        )
    torch.cuda.synchronize()
    infer_seconds = time.perf_counter() - infer_start

    input_tokens = int(inputs["input_ids"].shape[-1])
    total_tokens = int(generated.shape[-1])
    generated_tokens = max(total_tokens - input_tokens, 0)
    token_per_second = generated_tokens / infer_seconds if infer_seconds > 0 else 0.0
    peak_allocated_mb = torch.cuda.max_memory_allocated() / 1024 / 1024
    decoded = tokenizer.decode(generated[0][input_tokens:], skip_special_tokens=True).strip()

    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "model": args.model,
        "dtype": str(dtype),
        "gpu_before_or_after": gpu_snapshot(),
        "load_seconds": round(load_seconds, 3),
        "infer_seconds": round(infer_seconds, 3),
        "input_tokens": input_tokens,
        "generated_tokens": generated_tokens,
        "token_per_second": round(token_per_second, 3),
        "peak_torch_allocated_mb": round(peak_allocated_mb, 1),
        "prompt": args.prompt,
        "answer": decoded,
    }

    safe_model = args.model.replace("/", "_").replace(":", "_")
    out_path = output_dir / f"single_{safe_model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n== Result ==")
    print(decoded)
    print("\n== Metrics ==")
    print(json.dumps({k: record[k] for k in [
        "load_seconds",
        "infer_seconds",
        "input_tokens",
        "generated_tokens",
        "token_per_second",
        "peak_torch_allocated_mb",
    ]}, ensure_ascii=False, indent=2))
    print(f"\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


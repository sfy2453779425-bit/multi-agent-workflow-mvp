import argparse
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from statistics import mean

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


SYSTEM_PROMPT = (
    "You are a local LLM node for a Template-based Multi-Agent Workflow Builder. "
    "Answer in the requested language, keep the result structured, and prefer workflow/node terminology."
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


def load_prompts(path: Path) -> list[dict]:
    prompts = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(prompts, list) or not prompts:
        raise ValueError(f"Prompt file must contain a non-empty list: {path}")
    for item in prompts:
        for key in ["id", "category", "prompt", "expected_keywords"]:
            if key not in item:
                raise ValueError(f"Prompt item missing {key}: {item}")
    return prompts


def make_chat_prompt(tokenizer, prompt: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return f"System: {SYSTEM_PROMPT}\nUser: {prompt}\nAssistant:"


def keyword_score(answer: str, expected_keywords: list[str]) -> dict:
    lower = answer.lower()
    hits = []
    misses = []
    for keyword in expected_keywords:
        if keyword.lower() in lower:
            hits.append(keyword)
        else:
            misses.append(keyword)
    ratio = len(hits) / len(expected_keywords) if expected_keywords else 0.0
    return {
        "keyword_hits": hits,
        "keyword_misses": misses,
        "keyword_hit_count": len(hits),
        "keyword_total": len(expected_keywords),
        "keyword_score": round(ratio, 3),
    }


def load_model(model_name: str, adapter_path: str, dtype, local_files_only: bool):
    tokenizer_source = adapter_path if adapter_path else model_name
    tokenizer = AutoTokenizer.from_pretrained(
        tokenizer_source,
        trust_remote_code=True,
        local_files_only=local_files_only,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    load_start = time.perf_counter()
    base = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=dtype,
        device_map="auto" if not adapter_path else None,
        trust_remote_code=True,
        local_files_only=local_files_only,
    )
    if adapter_path:
        model = PeftModel.from_pretrained(base, adapter_path)
        model.to("cuda")
    else:
        model = base
    model.eval()
    load_seconds = time.perf_counter() - load_start
    return tokenizer, model, load_seconds


def run_one_prompt(model, tokenizer, item: dict, max_new_tokens: int) -> dict:
    prompt_text = make_chat_prompt(tokenizer, item["prompt"])
    inputs = tokenizer(prompt_text, return_tensors="pt")
    device = next(model.parameters()).device
    inputs = {key: value.to(device) for key, value in inputs.items()}

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    start = time.perf_counter()
    with torch.no_grad():
        generated = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
            pad_token_id=tokenizer.eos_token_id,
        )
    torch.cuda.synchronize()
    infer_seconds = time.perf_counter() - start

    input_tokens = int(inputs["input_ids"].shape[-1])
    total_tokens = int(generated.shape[-1])
    generated_tokens = max(total_tokens - input_tokens, 0)
    answer = tokenizer.decode(generated[0][input_tokens:], skip_special_tokens=True).strip()
    score = keyword_score(answer, item.get("expected_keywords", []))

    return {
        "id": item["id"],
        "category": item["category"],
        "language": item.get("language", ""),
        "prompt": item["prompt"],
        "expected_keywords": item.get("expected_keywords", []),
        "answer": answer,
        "infer_seconds": round(infer_seconds, 3),
        "input_tokens": input_tokens,
        "generated_tokens": generated_tokens,
        "token_per_second": round(generated_tokens / infer_seconds, 3) if infer_seconds > 0 else 0.0,
        "peak_torch_allocated_mb": round(torch.cuda.max_memory_allocated() / 1024 / 1024, 1),
        **score,
    }


def summarize_rows(rows: list[dict]) -> dict:
    if not rows:
        return {}
    return {
        "prompt_count": len(rows),
        "avg_infer_seconds": round(mean(row["infer_seconds"] for row in rows), 3),
        "avg_token_per_second": round(mean(row["token_per_second"] for row in rows), 3),
        "avg_peak_torch_allocated_mb": round(mean(row["peak_torch_allocated_mb"] for row in rows), 1),
        "avg_keyword_score": round(mean(row["keyword_score"] for row in rows), 3),
        "avg_generated_tokens": round(mean(row["generated_tokens"] for row in rows), 1),
    }


def write_markdown(record: dict, path: Path) -> None:
    lines = [
        "# Base vs LoRA Local LLM Evaluation",
        "",
        "## Run Summary",
        "",
        f"- Mode: `{record['mode']}`",
        f"- Model: `{record['model']}`",
        f"- Adapter: `{record.get('adapter') or 'none'}`",
        f"- dtype: `{record['dtype']}`",
        f"- Load time: `{record['load_seconds']}s`",
        f"- Prompt count: `{record['summary']['prompt_count']}`",
        f"- Average inference time: `{record['summary']['avg_infer_seconds']}s`",
        f"- Average token/s: `{record['summary']['avg_token_per_second']}`",
        f"- Average peak torch memory: `{record['summary']['avg_peak_torch_allocated_mb']} MB`",
        f"- Average keyword score: `{record['summary']['avg_keyword_score']}`",
        "",
        "## Metrics Table",
        "",
        "| Prompt ID | Category | Latency(s) | Tokens | token/s | Peak MB | Keyword Score |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in record["rows"]:
        lines.append(
            f"| {row['id']} | {row['category']} | {row['infer_seconds']} | "
            f"{row['generated_tokens']} | {row['token_per_second']} | "
            f"{row['peak_torch_allocated_mb']} | {row['keyword_score']} |"
        )

    lines.extend(["", "## Prompt Outputs", ""])
    for row in record["rows"]:
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"- Category: `{row['category']}`",
                f"- Keyword hits: `{', '.join(row['keyword_hits']) if row['keyword_hits'] else 'none'}`",
                f"- Keyword misses: `{', '.join(row['keyword_misses']) if row['keyword_misses'] else 'none'}`",
                "",
                "**Prompt**",
                "",
                row["prompt"],
                "",
                "**Answer**",
                "",
                row["answer"],
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate base Qwen or Qwen+LoRA on fixed workflow-builder prompts.")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--adapter", default="")
    parser.add_argument("--prompts", default="eval_prompts.json")
    parser.add_argument("--max-new-tokens", type=int, default=260)
    parser.add_argument("--dtype", choices=["auto", "float16", "bfloat16"], default="auto")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--output-dir", default="results/base_lora_comparison")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        print("ERROR: CUDA is not available.")
        return 1

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = Path(args.prompts)
    prompts = load_prompts(prompt_path)
    dtype = pick_dtype(args.dtype)
    mode = "lora" if args.adapter else "base"

    print(f"Mode: {mode}")
    print(f"Model: {args.model}")
    print(f"Adapter: {args.adapter or 'none'}")
    print(f"Prompts: {prompt_path}")
    print(f"dtype: {dtype}")
    print("GPU before load:", gpu_snapshot())

    tokenizer, model, load_seconds = load_model(
        args.model,
        args.adapter,
        dtype,
        args.local_files_only,
    )

    rows = []
    for index, item in enumerate(prompts, start=1):
        print(f"\n[{index}/{len(prompts)}] {item['id']}")
        row = run_one_prompt(model, tokenizer, item, args.max_new_tokens)
        rows.append(row)
        print(
            f"latency={row['infer_seconds']}s, token/s={row['token_per_second']}, "
            f"keyword_score={row['keyword_score']}"
        )

    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "model": args.model,
        "adapter": args.adapter,
        "dtype": str(dtype),
        "gpu_snapshot": gpu_snapshot(),
        "load_seconds": round(load_seconds, 3),
        "prompt_file": str(prompt_path),
        "max_new_tokens": args.max_new_tokens,
        "summary": summarize_rows(rows),
        "rows": rows,
    }

    safe_model = args.model.replace("/", "_").replace(":", "_")
    safe_mode = mode if not args.adapter else f"lora_{Path(args.adapter).parent.name or Path(args.adapter).name}"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"compare_{safe_model}_{safe_mode}_{stamp}.json"
    md_path = json_path.with_suffix(".md")
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(record, md_path)

    print("\n== Summary ==")
    print(json.dumps(record["summary"], ensure_ascii=False, indent=2))
    print(f"Saved JSON: {json_path}")
    print(f"Saved report: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

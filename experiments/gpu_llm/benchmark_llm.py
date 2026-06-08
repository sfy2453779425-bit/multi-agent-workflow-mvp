import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


PROMPTS = [
    "Recommend an outfit for a casual trip to Qingdao next week. Answer in Korean.",
    "Recommend a formal commute outfit for Seoul tomorrow. Include ranked items.",
    "Explain how a multi-agent workflow builder differs from a simple chatbot in 5 bullets.",
]


def pick_dtype():
    if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    return torch.float16 if torch.cuda.is_available() else torch.float32


def apply_chat(tokenizer, prompt: str) -> str:
    messages = [
        {"role": "system", "content": "You are a concise assistant for workflow-agent experiments."},
        {"role": "user", "content": prompt},
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return f"System: {messages[0]['content']}\nUser: {prompt}\nAssistant:"


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark a local instruction model.")
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--max-new-tokens", type=int, default=180)
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        print("ERROR: CUDA is not available.")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dtype = pick_dtype()
    load_start = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=dtype,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    load_seconds = time.perf_counter() - load_start

    rows = []
    for prompt in PROMPTS:
        text = apply_chat(tokenizer, prompt)
        inputs = tokenizer(text, return_tensors="pt")
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}

        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        start = time.perf_counter()
        with torch.no_grad():
            generated = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start

        input_tokens = int(inputs["input_ids"].shape[-1])
        total_tokens = int(generated.shape[-1])
        generated_tokens = max(total_tokens - input_tokens, 0)
        answer = tokenizer.decode(generated[0][input_tokens:], skip_special_tokens=True).strip()
        rows.append(
            {
                "prompt": prompt,
                "infer_seconds": round(elapsed, 3),
                "generated_tokens": generated_tokens,
                "token_per_second": round(generated_tokens / elapsed, 3) if elapsed > 0 else 0.0,
                "peak_torch_allocated_mb": round(torch.cuda.max_memory_allocated() / 1024 / 1024, 1),
                "answer": answer,
            }
        )
        print(f"Prompt done: {generated_tokens} tokens, {rows[-1]['token_per_second']} token/s")

    result = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "model": args.model,
        "dtype": str(dtype),
        "load_seconds": round(load_seconds, 3),
        "rows": rows,
    }
    safe_model = args.model.replace("/", "_").replace(":", "_")
    json_path = output_dir / f"benchmark_{safe_model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = json_path.with_suffix(".md")
    lines = [
        "# Local LLM Benchmark",
        "",
        f"- Model: `{args.model}`",
        f"- Load time: `{round(load_seconds, 3)}s`",
        f"- dtype: `{dtype}`",
        "",
        "| Prompt | Latency(s) | Generated tokens | token/s | Peak torch MB |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        short = row["prompt"].replace("|", "/")
        lines.append(
            f"| {short} | {row['infer_seconds']} | {row['generated_tokens']} | "
            f"{row['token_per_second']} | {row['peak_torch_allocated_mb']} |"
        )
    lines.extend(["", "## Sample Answers", ""])
    for index, row in enumerate(rows, start=1):
        lines.extend([f"### Prompt {index}", "", row["answer"], ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved JSON: {json_path}")
    print(f"Saved report: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


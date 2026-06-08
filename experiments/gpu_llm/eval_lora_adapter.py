import argparse
import json
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


PROMPTS = [
    "Explain our Template-based Multi-Agent Workflow Builder MVP in Chinese.",
    "Answer why Harness Engineering alone is not enough for our project.",
    "Design a Local LLM Compose Node for a workflow builder.",
]


def make_prompt(tokenizer, prompt: str) -> str:
    messages = [
        {
            "role": "system",
            "content": "You are a local LLM node for a Template-based Multi-Agent Workflow Builder.",
        },
        {"role": "user", "content": prompt},
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return f"System: {messages[0]['content']}\nUser: {prompt}\nAssistant:"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a trained LoRA adapter.")
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--max-new-tokens", type=int, default=220)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available.")

    tokenizer = AutoTokenizer.from_pretrained(args.adapter, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    base = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=dtype, trust_remote_code=True)
    model = PeftModel.from_pretrained(base, args.adapter)
    model.to("cuda")
    model.eval()

    rows = []
    for prompt in PROMPTS:
        text = make_prompt(tokenizer, prompt)
        inputs = tokenizer(text, return_tensors="pt").to("cuda")
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
        generated_tokens = int(generated.shape[-1]) - input_tokens
        answer = tokenizer.decode(generated[0][input_tokens:], skip_special_tokens=True).strip()
        rows.append(
            {
                "prompt": prompt,
                "latency_seconds": round(elapsed, 3),
                "generated_tokens": generated_tokens,
                "token_per_second": round(generated_tokens / elapsed, 3) if elapsed > 0 else 0,
                "answer": answer,
            }
        )
        print("\n== Prompt ==")
        print(prompt)
        print("== Answer ==")
        print(answer)
        print(f"tokens={generated_tokens}, token/s={rows[-1]['token_per_second']}")

    output = Path(args.output) if args.output else Path(args.adapter).parent / "adapter_eval.json"
    output.write_text(json.dumps({"model": args.model, "adapter": args.adapter, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved evaluation: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


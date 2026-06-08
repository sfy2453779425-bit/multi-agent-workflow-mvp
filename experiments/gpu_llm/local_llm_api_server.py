import argparse
import json
import os
import traceback
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


@dataclass(frozen=True)
class GenerateRequest:
    model: str
    role: str
    prompt: str
    context: dict[str, Any]
    max_new_tokens: int = 220
    temperature: float = 0.2
    adapter_path: str = ""


def parse_generate_payload(payload: dict[str, Any]) -> GenerateRequest:
    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("prompt is required")

    context = payload.get("context", {})
    if not isinstance(context, dict):
        raise ValueError("context must be an object")

    return GenerateRequest(
        model=str(payload.get("model") or "Qwen/Qwen2.5-1.5B-Instruct"),
        role=str(payload.get("role") or "compose"),
        prompt=prompt,
        context=context,
        max_new_tokens=int(payload.get("max_new_tokens") or 220),
        temperature=float(payload.get("temperature") if payload.get("temperature") is not None else 0.2),
        adapter_path=str(payload.get("adapter_path") or ""),
    )


def build_generate_response(
    *,
    request: GenerateRequest,
    answer: str,
    infer_seconds: float,
    generated_tokens: int,
    peak_memory_mb: float,
    device: str,
) -> dict[str, Any]:
    token_per_second = 0.0
    if infer_seconds > 0 and generated_tokens > 0:
        token_per_second = round(generated_tokens / infer_seconds, 3)

    return {
        "answer": answer,
        "model": request.model,
        "role": request.role,
        "provider": "remote_local_llm",
        "adapter_path": request.adapter_path,
        "metrics": {
            "infer_seconds": round(infer_seconds, 3),
            "generated_tokens": generated_tokens,
            "tokens_per_second": token_per_second,
            "peak_memory_mb": round(peak_memory_mb, 1),
            "device": device,
        },
    }


class QwenGenerator:
    def __init__(self, model: str, adapter_path: str = "", device: str = "cuda:0"):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.model_name = model
        self.adapter_path = adapter_path
        self.device_name = device
        self.tokenizer = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        dtype = self._pick_dtype()
        self.model = AutoModelForCausalLM.from_pretrained(
            model,
            torch_dtype=dtype,
            device_map="auto",
            trust_remote_code=True,
        )
        if adapter_path:
            from peft import PeftModel

            self.model = PeftModel.from_pretrained(self.model, adapter_path)
        self.model.eval()

    def _pick_dtype(self):
        torch = self.torch
        if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
            return torch.bfloat16
        return torch.float16 if torch.cuda.is_available() else torch.float32

    def generate(self, request: GenerateRequest) -> dict[str, Any]:
        torch = self.torch
        system_prompt = (
            "You are a Local LLM Node inside a Template-based Multi-Agent Workflow Builder. "
            "Use only the structured workflow context. Keep the answer concise and actionable."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.prompt},
        ]
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.tokenizer(text, return_tensors="pt")
        device = next(self.model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        torch.cuda.empty_cache()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()

        start = time.perf_counter()
        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=request.max_new_tokens,
                do_sample=False,
                temperature=None,
                top_p=None,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        infer_seconds = time.perf_counter() - start

        new_tokens = int(output_ids.shape[-1] - inputs["input_ids"].shape[-1])
        decoded = self.tokenizer.decode(output_ids[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
        peak_memory_mb = 0.0
        if torch.cuda.is_available():
            peak_memory_mb = torch.cuda.max_memory_allocated() / 1024 / 1024

        return build_generate_response(
            request=request,
            answer=decoded.strip(),
            infer_seconds=infer_seconds,
            generated_tokens=new_tokens,
            peak_memory_mb=peak_memory_mb,
            device=str(self.model.device),
        )


class LocalLLMRequestHandler(BaseHTTPRequestHandler):
    generator: QwenGenerator | None = None

    def do_GET(self) -> None:
        if self.path != "/health":
            self._write_json({"error": "not found"}, status=404)
            return
        self._write_json(
            {
                "ok": True,
                "model": self.generator.model_name if self.generator else "",
                "adapter_path": self.generator.adapter_path if self.generator else "",
            }
        )

    def do_POST(self) -> None:
        if self.path != "/generate":
            self._write_json({"error": "not found"}, status=404)
            return
        if self.generator is None:
            self._write_json({"error": "generator is not initialized"}, status=503)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw_body)
            request = parse_generate_payload(payload)
            if request.model != self.generator.model_name:
                request = GenerateRequest(
                    model=self.generator.model_name,
                    role=request.role,
                    prompt=request.prompt,
                    context=request.context,
                    max_new_tokens=request.max_new_tokens,
                    temperature=request.temperature,
                    adapter_path=request.adapter_path or self.generator.adapter_path,
                )
            response = self.generator.generate(request)
            self._write_json(response)
        except Exception as exc:
            self._write_json(
                {
                    "error": str(exc),
                    "traceback": traceback.format_exc(limit=6),
                },
                status=500,
            )

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[local-llm-api] {self.address_string()} - {format % args}")

    def _write_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str, port: int, model: str, adapter_path: str = "", device: str = "cuda:0") -> None:
    LocalLLMRequestHandler.generator = QwenGenerator(model=model, adapter_path=adapter_path, device=device)
    server = ThreadingHTTPServer((host, port), LocalLLMRequestHandler)
    print(f"Local LLM API server running on http://{host}:{port}")
    print(f"Model: {model}")
    if adapter_path:
        print(f"Adapter: {adapter_path}")
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve Qwen as a Local LLM Node HTTP endpoint.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9100)
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--adapter-path", default="")
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    if args.device.startswith("cuda"):
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

    run_server(
        host=args.host,
        port=args.port,
        model=args.model,
        adapter_path=args.adapter_path,
        device=args.device,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

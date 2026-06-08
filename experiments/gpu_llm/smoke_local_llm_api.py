import argparse
import json
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the Local LLM API server.")
    parser.add_argument("--endpoint", default="http://127.0.0.1:9100/generate")
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--prompt", default="Explain the workflow nodes for an outfit recommendation agent.")
    args = parser.parse_args()

    payload = {
        "model": args.model,
        "role": "compose",
        "prompt": args.prompt,
        "context": {
            "workflow_name": "Outfit Recommendation Workflow",
            "runtime_type": "outfit_recommendation",
        },
        "max_new_tokens": 160,
        "temperature": 0.2,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        args.endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        body = response.read().decode("utf-8")
    result = json.loads(body)

    print("== Local LLM API Smoke Result ==")
    print("Model:", result.get("model"))
    print("Provider:", result.get("provider"))
    print("Metrics:", json.dumps(result.get("metrics", {}), ensure_ascii=False, indent=2))
    print()
    print(result.get("answer", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# GPU LLM Experiment Pack

Purpose:

- Verify the assigned GPU server can run a local open-source LLM.
- Record GPU memory usage, latency, generated token count, and token/s.
- Keep evidence for the next semester direction: Local LLM + Multi-Agent Workflow Builder.

This folder intentionally does not contain server IP, account, or password.

## Recommended first run

On the GPU server:

```bash
cd ~/gpu_llm
bash check_env.sh
bash setup_env.sh
source .venv/bin/activate
python run_qwen_test.py --model Qwen/Qwen2.5-1.5B-Instruct
```

The 1.5B model is the fastest smoke test. After it works, try:

```bash
python run_qwen_test.py --model Qwen/Qwen2.5-7B-Instruct
```

## Benchmark run

```bash
source .venv/bin/activate
python benchmark_llm.py --model Qwen/Qwen2.5-7B-Instruct
```

Results are written to:

```text
results/
```

## Base vs LoRA comparison

After LoRA adapters have been trained under `lora_outputs/`, run:

```bash
source .venv/bin/activate
bash run_base_lora_comparison.sh
```

This runs the fixed evaluation set in `eval_prompts.json` against:

- Qwen2.5-1.5B base
- Qwen2.5-1.5B + LoRA, if the adapter exists
- Qwen2.5-7B base
- Qwen2.5-7B + LoRA, if the adapter exists

Results are written to:

```text
results/base_lora_comparison/
```

Important outputs:

```text
base_lora_summary.md
compare_*.json
compare_*.md
```

The comparison focuses on:

- inference latency
- generated token/s
- peak GPU memory
- workflow-builder keyword coverage
- prompt-level answer quality

## LoRA v2 experiment

The first LoRA experiment verified that adapters can be trained and loaded,
but the small dataset did not improve the average score. The v2 experiment
uses a larger workflow-specific SFT dataset.

Train the v2 adapter:

```bash
source .venv/bin/activate
bash run_lora_training_v2.sh
```

Compare base / old LoRA / v2 LoRA:

```bash
bash run_v2_comparison.sh
```

Results are written to:

```text
results/v2_lora_comparison/
```

Important outputs:

```text
v2_lora_summary.md
compare_*.json
compare_*.md
```

## Local LLM API server

After the benchmark and LoRA experiments, the same GPU environment can expose
Qwen as an HTTP endpoint for the Builder MVP's `Local LLM Node`.

Start the API server on the GPU server:

```bash
cd ~/gpu_llm
source .venv/bin/activate
bash run_local_llm_api_server.sh
```

Defaults:

```text
MODEL=Qwen/Qwen2.5-1.5B-Instruct
HOST=0.0.0.0
PORT=9100
DEVICE=cuda:0
```

Optional LoRA adapter:

```bash
ADAPTER_PATH=lora_outputs/Qwen_Qwen2.5-1.5B-Instruct_workflow_builder_v2 bash run_local_llm_api_server.sh
```

Smoke-test the endpoint on the GPU server:

```bash
python smoke_local_llm_api.py
```

From the Windows project machine, keep an SSH tunnel open:

```powershell
ssh -p <SSH_PORT> -L 9100:127.0.0.1:9100 <GPU_USER>@<GPU_SERVER_IP>
```

Then run the local workflow with the remote Local LLM Node config:

```powershell
python builder_demo.py --workflow --local-llm-config configs\local_llm_node.remote.example.json --user user_a "Seoul tomorrow casual outfit recommendation"
```

## What to record

Run:

```bash
nvidia-smi
```

Then copy the following into `report_template.md`:

- GPU model
- driver / CUDA version
- model name
- model load time
- first response latency
- generated token count
- token/s
- peak GPU memory
- sample model answer

## If download is too slow

Use the smaller model first:

```bash
python run_qwen_test.py --model Qwen/Qwen2.5-0.5B-Instruct
```

The purpose is to verify the pipeline, not to get the best answer immediately.

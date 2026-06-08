#!/usr/bin/env bash
set -euo pipefail

echo "== Basic system =="
date
hostname
whoami
pwd

echo
echo "== GPU =="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi
else
  echo "nvidia-smi not found"
fi

echo
echo "== Python =="
if command -v python3 >/dev/null 2>&1; then
  python3 --version
else
  echo "python3 not found"
fi

echo
echo "== Python packages =="
python3 - <<'PY' || true
import importlib.util

for name in ["torch", "transformers", "accelerate", "psutil"]:
    spec = importlib.util.find_spec(name)
    print(f"{name}: {'installed' if spec else 'not installed'}")

try:
    import torch
    print("torch version:", torch.__version__)
    print("cuda available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("cuda device count:", torch.cuda.device_count())
        print("current device:", torch.cuda.current_device())
        print("device name:", torch.cuda.get_device_name(0))
except Exception as exc:
    print("torch check error:", exc)
PY


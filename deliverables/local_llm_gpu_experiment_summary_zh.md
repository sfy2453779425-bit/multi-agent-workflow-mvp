# A100 本地 LLM 预研记录

## 目的

验证学校 A100 GPU 服务器能否运行本地开源 LLM，并判断它是否适合作为下学期 Multi-Agent Workflow Builder 的本地模型节点。

## 已完成实验

### 环境

- GPU: NVIDIA A100 80GB PCIe
- CUDA: 13.1
- Python: 3.11.7
- Runtime: PyTorch + Transformers
- dtype: bfloat16

### 单次推理结果

| Model | Load Time | Inference Time | Generated Tokens | Speed | Peak GPU Memory |
|---|---:|---:|---:|---:|---:|
| Qwen2.5-1.5B-Instruct | 38.5s | 2.958s | 220 | 74.385 token/s | 2962.6 MB |
| Qwen2.5-7B-Instruct | 129.884s | 3.708s | 220 | 59.33 token/s | 14551.8 MB |

### Benchmark 结果

Qwen2.5-7B-Instruct 三个 benchmark prompt 的生成速度：

| Prompt | Speed |
|---|---:|
| Outfit recommendation | 56.81 token/s |
| Commute outfit recommendation | 66.464 token/s |
| Workflow Builder explanation | 66.085 token/s |

## 结论

A100 80GB 可以稳定运行 Qwen2.5-7B-Instruct，本次峰值显存约 14.6GB，显存余量充足。

Qwen2.5-7B 的生成速度约 56-66 token/s，足够支持 Workflow 中的 Compose Node、Reasoning Node 或 Planning Node。

因此，下学期可以把当前 Template-based Multi-Agent Workflow Builder 扩展为：

```text
Template-based Workflow Builder
+ Local LLM Node
+ Private / On-premise Agent Execution
```

## 注意

服务器账号、IP、端口和密码规则不应提交到 GitHub。


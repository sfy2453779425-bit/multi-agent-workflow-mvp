# Local LLM Node 接入方案

## 目的

本功能不是把本地电脑变成 GPU 服务器，而是在现有 Workflow Builder MVP 里加入一个可插拔节点：

```text
Local LLM Node
```

它用于证明：

```text
Template-based Multi-Agent Workflow Builder
可以把本地/私有 LLM 作为一个 Workflow Node 接入。
```

也就是说，项目不只依赖规则节点，也可以扩展到：

- Qwen 本地模型
- GPU 服务器模型
- LoRA 微调模型
- 企业内部私有模型

## 当前实现状态

已实现：

- `src/agent_builder/local_llm.py`
- `LocalLLMNodeConfig`
- `LocalLLMNode`
- `LocalLLMResult`
- `mock` provider
- `remote` provider
- Workflow 可选追加 `Local LLM Node` Trace
- `builder_demo.py --local-llm-config ...`
- GPU 端 HTTP API server 示例

默认不开启，不影响原来的 Demo。

## Provider 设计

### 1. Mock Provider

配置文件：

```text
configs/local_llm_node.mock.json
```

用途：

- 没有 GPU 时也能演示 Local LLM Node
- 验证 Workflow Trace 中能出现 Local LLM Node
- 用于前端、报告、自动化测试

特点：

```text
不调用真实模型，不需要服务器，输出稳定。
```

运行方式：

```powershell
python builder_demo.py --workflow --local-llm-config configs\local_llm_node.mock.json --user user_a "Seoul tomorrow casual outfit recommendation"
```

预期 Trace：

```text
Workflow Trace (7 Nodes)
...
7. Local LLM Node: mock provider executed ...
```

### 2. Remote Provider

配置文件：

```text
configs/local_llm_node.remote.example.json
```

用途：

- 把 GPU 服务器上的 Qwen 推理服务接入 Workflow
- 通过 HTTP POST 调用远程模型
- 返回模型输出和性能指标

请求结构：

```json
{
  "model": "Qwen/Qwen2.5-1.5B-Instruct",
  "role": "compose",
  "prompt": "...",
  "context": {
    "workflow_name": "...",
    "runtime_type": "...",
    "query": "..."
  }
}
```

响应结构：

```json
{
  "answer": "model output",
  "model": "Qwen/Qwen2.5-1.5B-Instruct",
  "provider": "remote_local_llm",
  "metrics": {
    "infer_seconds": 2.1,
    "generated_tokens": 180,
    "tokens_per_second": 85.7,
    "peak_memory_mb": 3040.8,
    "device": "cuda:0"
  }
}
```

如果 remote 调用失败，且 `fallback_to_mock=true`，系统会自动回退到 mock 输出，避免演示中断。

### 3. Replay Provider

配置文件：

```text
configs/local_llm_node.replay.json
```

用途：

- 使用已经在 GPU 上成功跑出的 Qwen JSON 结果
- 不需要 SSH tunnel
- 不需要实时 API server
- 不受 CUDA 进程状态影响
- 适合作为稳定演示和报告证据

运行方式：

```powershell
tools\gpu\run_gpu_replay_demo.cmd
```

预期 Trace：

```text
Workflow Trace (7 Nodes)
...
7. Local LLM Node: replay provider executed ...
```

推荐结论：

```text
GPU 실험 결과를 replay provider로 Workflow에 연결하여,
Local LLM Node가 실제 Qwen 실행 결과와 metrics를 Workflow Trace에 포함할 수 있음을 안정적으로 검증했다.
```

## Workflow 中的位置

当前接入位置：

```text
Compose Node 之后
```

执行顺序：

```text
Request Parser
-> Question
-> Tool/Data/Decision Nodes
-> Compose
-> Local LLM Node
```

原因：

- 不破坏现有规则型 Workflow
- 先保留稳定、可解释的确定性输出
- 再用 Local LLM Node 做最终解释增强、自然语言润色或结构化总结

## GPU API 服务（可选实验）

GPU 端文件：

```text
experiments/gpu_llm/local_llm_api_server.py
experiments/gpu_llm/run_local_llm_api_server.sh
experiments/gpu_llm/smoke_local_llm_api.py
```

GPU 服务器启动：

```bash
cd ~/gpu_llm
source .venv/bin/activate
bash run_local_llm_api_server.sh
```

本地通过 SSH 转发：

```powershell
ssh -p <SSH_PORT> -L 9100:127.0.0.1:9100 <GPU_USER>@<GPU_SERVER_IP>
```

本地运行远程节点 Demo：

```powershell
.\tools\gpu\run_local_llm_remote_demo.cmd
```

注意：实时 API 模式依赖 SSH tunnel、远程 Python 进程、CUDA 状态和端口占用，稳定性不如 replay provider。正式演示优先使用 replay provider。

## 当前测试

新增测试：

```text
tests/test_local_llm_api_server.py
```

验证内容：

- GPU API 请求解析格式稳定
- GPU API 响应格式符合 Local LLM Node contract
- replay provider 可以读取已下载的 GPU JSON 结果
- `builder_demo.py` 可以通过 `--local-llm-config` 启用 Local LLM Node
- 开启 Local LLM Node 后 Trace 数量从 6 变成 7

## 下学期报告说法

中文：

```text
我们已经把 Local LLM Node 作为可选节点接入 Workflow 结构。
当前本地 Demo 可以用 mock provider 稳定验证接口和 Trace；
GPU 实验已经验证 Qwen2.5 模型可以在 A100 上运行；
进一步通过 replay provider，可以把 GPU 实验结果稳定接入 Workflow Trace；
remote provider 则作为实时 API 连接的可选实验。
```

韩语：

```text
본 프로젝트는 Local LLM Node를 Workflow의 선택적 실행 노드로 추가했다.
현재 로컬 Demo에서는 mock provider로 인터페이스와 Trace를 안정적으로 검증하고,
GPU 실험에서는 Qwen2.5 모델이 A100 환경에서 실행 가능함을 확인했다.
이후 replay provider를 통해 GPU 실험 결과를 Workflow Trace에 안정적으로 연결할 수 있으며,
remote provider는 실시간 API 연결을 위한 선택적 실험으로 유지한다.
```

## 注意边界

不要说：

```text
已经完成完整 GPU 기반 상용 Agent Builder
```

应该说：

```text
已经完成 Local LLM Node 的接口、Workflow 集成、GPU replay 接入和 GPU API 原型；
正式演示优先使用 replay provider，实时 GPU API 作为可选实验。
```

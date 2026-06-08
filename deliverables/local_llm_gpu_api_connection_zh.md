# Local LLM Node + GPU API 连接说明

## 目标

把当前 Builder Workflow 的最后一步连接到 GPU 服务器上的 Qwen 模型：

```text
Workflow 本地运行
-> Local LLM Node
-> HTTP /generate
-> GPU Qwen 生成结果
-> 返回 answer + metrics
```

这证明本项目不是只能跑规则 Demo，而是可以把本地/私有 LLM 作为 Workflow Node 接入。

## 1. 在 GPU 服务器启动 API

进入 GPU 服务器：

```bash
ssh -p <SSH_PORT> <GPU_USER>@<GPU_SERVER_IP>
```

进入实验目录：

```bash
cd ~/gpu_llm
source .venv/bin/activate
```

启动 1.5B 模型服务：

```bash
bash run_local_llm_api_server.sh
```

默认参数：

```text
MODEL=Qwen/Qwen2.5-1.5B-Instruct
HOST=0.0.0.0
PORT=9100
DEVICE=cuda:0
```

如果要加载 v2 LoRA：

```bash
ADAPTER_PATH=lora_outputs/Qwen_Qwen2.5-1.5B-Instruct_workflow_builder_v2 bash run_local_llm_api_server.sh
```

## 2. 本地建立 SSH 端口转发

在 Windows PowerShell 另开一个窗口：

```powershell
ssh -p <SSH_PORT> -L 9100:127.0.0.1:9100 <GPU_USER>@<GPU_SERVER_IP>
```

这个窗口不要关闭。它会把本地：

```text
http://127.0.0.1:9100
```

转发到 GPU 服务器的 API。

## 3. 本地运行 Workflow 远程节点 Demo

在项目目录运行：

```powershell
cd D:\综合设计
.\tools\gpu\run_local_llm_remote_demo.cmd
```

或者直接运行：

```powershell
python builder_demo.py --workflow --local-llm-config configs\local_llm_node.remote.example.json --user user_a "Seoul tomorrow casual outfit recommendation"
```

如果 GPU API 正常，会在 Trace 里看到：

```text
Local LLM Node: remote provider executed with model=...
```

如果 GPU API 没开，配置会自动 fallback 到 mock，避免演示崩掉。

## 4. API 单独测试

在 GPU 服务器本机测试：

```bash
cd ~/gpu_llm
source .venv/bin/activate
python smoke_local_llm_api.py
```

通过 SSH 转发后，也可以在本地测：

```powershell
python experiments\gpu_llm\smoke_local_llm_api.py --endpoint http://127.0.0.1:9100/generate
```

## 5. 项目表述

推荐用于报告的说法：

```text
본 프로젝트는 Workflow Builder MVP에 Local LLM Node를 추가하여,
GPU 서버의 Qwen 모델을 실행 노드로 연결할 수 있음을 검증했다.
이를 통해 추천/지원/발표 준비 등 다양한 Workflow가
규칙 기반 노드와 LLM 생성 노드를 함께 사용할 수 있다.
```

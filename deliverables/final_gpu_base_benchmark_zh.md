# 最后一轮 GPU 基线实验说明

## 目的

这一步不是继续训练模型，而是补一份稳定的技术证据：

```text
在 A100 GPU 上，Qwen2.5-1.5B Base 模型可以作为 Local LLM Node 的候选模型运行。
```

它用于下学期说明：

- 本项目已经验证过本地 LLM 接入可行性。
- 当前最稳定方案是先使用 Base Model + Workflow 结构。
- LoRA 训练可以作为后续优化方向，不是当前必须依赖的主路线。

## 运行顺序

先双击：

```text
tools\gpu\run_final_base_benchmark.cmd
```

脚本会要求输入 GPU 服务器信息：

```text
GPU server host or IP: <由学校或导师提供>
SSH port: <由学校或导师提供>
GPU user: <由学校或导师提供>
Password: <不要写入文件，运行时手动输入>
```

运行完成后，再双击：

```text
tools\gpu\download_final_base_benchmark.cmd
```

下载后的结果会放在本地：

```text
_local_artifacts\gpu_results\final_base_benchmark
```

## 应保留的结果

保留最新的两个文件：

```text
benchmark_Qwen_Qwen2.5-1.5B-Instruct_*.json
benchmark_Qwen_Qwen2.5-1.5B-Instruct_*.md
```

其中 `.md` 文件适合直接打开查看，`.json` 文件适合以后做表格统计。

## 可写进报告的结论

```text
Qwen2.5-1.5B-Instruct was benchmarked on the allocated A100 GPU as a candidate Local LLM Node.
The experiment measures loading time, inference latency, generated tokens per second, and peak GPU memory usage.
This provides technical evidence that the Workflow Builder MVP can be extended from mock/replay execution to a real local LLM execution path.
```

中文解释：

```text
我们使用学校分配的 A100 GPU 对 Qwen2.5-1.5B-Instruct 进行了基线测试。
实验记录了模型加载时间、推理延迟、生成速度和 GPU 显存占用。
该结果证明项目中的 Local LLM Node 不只是概念，可以接入真实本地模型执行。
```

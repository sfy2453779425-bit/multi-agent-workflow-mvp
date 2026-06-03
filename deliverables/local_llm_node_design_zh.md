# Local LLM Node 设计草案

## 目标

把本地开源模型作为 Workflow 中的一个可配置节点，而不是把整个系统改成聊天机器人。

## 节点定位

Local LLM Node 应该作为 Workflow 的一部分出现：

```text
Input Node
-> Parser / Question Node
-> Tool / Data Node
-> Rule / Decision Node
-> Local LLM Compose Node
-> Output
```

## 第一阶段接入点

优先实现：

```text
Local LLM Compose Node
```

原因：

- 风险最低
- 不破坏现有规则流程
- 可以直接使用 Qwen 生成自然语言解释
- 适合证明本地模型可接入 Builder

## 输入

Local LLM Compose Node 接收结构化上下文：

```json
{
  "workflow_name": "...",
  "user_query": "...",
  "tool_results": {},
  "decision_result": {},
  "ranked_items": [],
  "required_language": "ko"
}
```

## 输出

输出自然语言文本：

```json
{
  "final_answer": "...",
  "model": "Qwen2.5-7B-Instruct",
  "latency_seconds": 3.7,
  "generated_tokens": 220,
  "token_per_second": 59.33
}
```

## 配置示例

```json
{
  "id": "local_llm_compose",
  "name": "Local LLM Compose Node",
  "category": "output",
  "runtime": {
    "type": "local_llm",
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "server": "local_or_gpu_server",
    "max_new_tokens": 220
  },
  "inputs": ["workflow_context", "decision_result"],
  "outputs": ["final_answer", "llm_metrics"]
}
```

## 技术路线

第一版可以先不做复杂服务化，直接用 Python 调用：

```text
transformers + AutoModelForCausalLM + AutoTokenizer
```

第二版再封装成 HTTP 服务：

```text
Workflow Engine -> Local LLM API -> Qwen Model -> Response
```

## 风险

- GPU 账号有期限
- 模型加载时间较长
- 多用户并发需要单独设计
- 生成内容需要约束，不能替代确定性流程

## 结论

Local LLM Node 不应该替代 Builder，而应该作为 Builder 生成 Workflow 后的可选执行节点。

当前 A100 实验已经证明 Qwen2.5-7B 可以稳定运行，速度和显存都满足原型需求。


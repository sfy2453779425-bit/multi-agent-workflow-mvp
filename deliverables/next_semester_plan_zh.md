# 下学期推进计划

## 当前项目定位

当前系统已经从单一穿搭推荐 Demo 扩展为：

```text
Template-based Multi-Agent Workflow Builder MVP
```

它支持通过业务模板生成可执行 Workflow JSON，并在统一引擎中执行。

当前已有 4 个模板：

- Outfit Recommendation
- Commute Outfit Recommendation
- Presentation Planning
- Customer Support Ticket Routing

## 下学期主线

下学期不建议重写项目，而是在当前 Builder MVP 上继续扩展。

建议主线：

```text
Template-based Multi-Agent Workflow Builder
+ Local LLM Node
+ Harness Comparison
+ Multi-domain Workflow Validation
```

## 具体任务

### 1. Local LLM Node

把本地 Qwen 模型作为一个可插拔节点接入 Workflow。

优先接入位置：

- Compose Node
- Planning Node
- Reasoning Node
- Routing Decision Node

### 2. Builder Workspace 增强

让用户可以在网页里选择：

- 业务 Preset
- Workflow 名称
- 输入内容
- 是否使用 Local LLM Node

### 3. 多领域验证

继续保留至少 4 个领域：

- 推荐
- 发表规划
- 客服工单
- 通勤/旅行

目标不是每个领域都做得很深，而是证明同一套 Builder 结构可以迁移。

### 4. Harness Engineering 对比

继续维护 Harness Comparison：

```text
Generic Harness: 手动定义 Agent / Tool / Context / Constraints / Verification
Builder Workspace: 选择 Preset 后生成标准 Workflow JSON
```

当前实验结果显示：

```text
Generic Harness 平均构建触点: 17
Builder Workspace 平均构建触点: 3
平均减少: 14
```

### 5. 可视化验证

继续以网页作为主要演示入口：

```text
run_web.cmd
http://127.0.0.1:8000
```

保留命令行验证：

```text
run_verify.cmd
run_harness_comparison.cmd
```

## 最小可交付版本

下学期第一阶段目标：

```text
网页 Builder 可以选择一个 Workflow 模板，
运行时至少一个节点调用本地 Qwen 模型，
最终输出 Trace 和模型回答。
```


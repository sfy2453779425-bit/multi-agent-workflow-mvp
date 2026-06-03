# Harness Engineering 对比实验结果

## 实验设计

本实验不是比较模型聪明程度，而是比较 Workflow 构建方式。
两组都使用同一个本地执行引擎，差异只放在构建阶段：

- Generic Harness Engineering：手动定义 Agent、Tool、Context/Memory、Constraints、Feedback Loop、Verification、Execution Environment。
- Builder Workspace：选择业务领域 Preset，生成标准 Workflow JSON，再执行并输出 Trace。

## 总体结果

- 对比任务数：2
- Builder 可用 Preset 数：4
- Generic Harness 平均构建触点：17.0
- Builder Workspace 平均构建触点：3.0
- 平均减少构建触点：14.0
- 两组 Trace 步数是否一致：是

## 任务对比

| 任务 | Generic Harness 构建触点 | Builder Workspace 构建触点 | 减少 | Generic Trace | Builder Trace | Builder 生成来源 |
|---|---:|---:|---:|---:|---:|---|
| 发表规划任务 | 17 | 3 | 14 | 6 | 6 | BuilderWorkspace |
| 客服工单分流任务 | 17 | 3 | 14 | 6 | 6 | BuilderWorkspace |

## 可放进 PPT 的结论

Harness Engineering 可以解决 Agent 的运行结构问题，但它本身仍然要求开发者手动定义不同业务的 Agent、Tool、上下文、约束和验证规则。

本项目的价值不是重新发明 Harness，而是把 Harness 思路上升为 Builder Workspace：通过业务 Template/Preset 生成可执行 Workflow JSON，并在多个领域保持同样的顺序执行和 Trace 验证结构。

因此，面对“用 Harness Engineering 不就可以了吗”的问题，可以回答：

> Harness 是通用运行框架，本项目解决的是业务 Workflow 如何被模板化、生成、迁移和验证。实验中，同样两个任务下，Generic Harness 平均需要手动维护 17.0 个构建触点，而 Builder Workspace 平均只需要 3.0 个构建触点，就能生成标准 JSON 并执行 6 步 Trace。

# 外部 Builder 工具验证记录

## 目标

企业导师要求研究现有 Builder 工具：

- Flowise
- Dify
- Langflow

本项目不能假装这些工具不存在。正确做法是：

```text
承认已有通用 Builder，
并说明我们的贡献是推荐领域 Workflow Template 和本地 Builder Prototype。
```

## 当前完成情况

### 1. Flowise

已完成：

- 查询 npm 包信息：

```powershell
npm view flowise version description bin --json
```

结果：

```json
{
  "version": "3.1.2",
  "description": "Flowiseai Server",
  "bin": {
    "flowise": "bin/run"
  }
}
```

- 新增可复现启动环境：

```text
external_tools/flowise_poc/package.json
external_tools/flowise_poc/README.md
external_tools/flowise_poc/run_flowise_poc.cmd
```

- 启动方式：

```bat
external_tools\flowise_poc\run_flowise_poc.cmd
```

说明：

```text
脚本使用 npx flowise@3.1.2，避免把大型 node_modules 提交进 Git。
```

实际限制：

```text
本地 npm install flowise 依赖树很大，尝试安装超过 5 分钟仍未完成。
随后尝试 npm exec --yes flowise@3.1.2 -- --version，也在 5 分钟内超时。
因此当前项目不能声称 Flowise 已经本地跑通。
项目保留固定版本 npx runner 和 Flowise 节点映射，作为下一步外部 PoC 的可复现入口。
```

### 2. Dify

当前处理方式：

- 已在 `deliverables/builder_tool_comparison_kr.md` 中完成调研比较。
- 已新增 Dify PoC 说明：

```text
external_tools/dify_poc/README.md
external_tools/dify_poc/run_dify_poc.cmd
```

- 已检查当前机器 Docker 环境：

```powershell
docker --version
docker compose version
```

结果：

```text
docker: command not found
```

原因：

```text
Dify 更偏生产级 LLM App 平台，包含 Workflow、Knowledge、Tool、API 发布和监控。
其自托管部署依赖 Docker / Docker Compose。
当前机器没有 Docker，因此不能声称已经本地跑通 Dify。
```

### 3. Langflow

当前处理方式：

- 已在 `deliverables/builder_tool_comparison_kr.md` 中完成调研比较。
- 已新增 Langflow PoC 说明和启动脚本：

```text
external_tools/langflow_poc/README.md
external_tools/langflow_poc/run_langflow_poc.cmd
```

- 已验证 Python package index 可查到 Langflow：

```powershell
python -m pip index versions langflow
```

结果：

```text
langflow (1.9.4)
```

原因：

```text
Langflow 适合 Python 生态扩展，但当前项目已经有 Python 本地 Builder Prototype。
下一步可以把 TemplateWorkflowBuilder 包装成 Langflow custom component。
```

## 我们项目与外部 Builder 的关系

```text
Flowise / Dify / Langflow 是通用 Builder。
我们的项目不是重复造通用 Builder。

我们的项目定义了个性化推荐场景需要的 Workflow Template：
Question Node、Weather Tool Node、Shopping History Analysis Node、
Recommendation Ranking、Compose Node。
```

## 当前项目内已实现的 Builder 证据

- `run_builder_app.cmd`
  - 本地 Builder Prototype
- `configs/builder_templates/outfit_recommendation_template.json`
  - 推荐领域 Builder Template
- `src/agent_builder/template_builder.py`
  - 从 Template 生成 Workflow JSON
- `python builder_demo.py --run-generated ...`
  - 生成后的 Workflow 可执行

## 发表时建议说法

```text
멘토님이 말씀하신 Flowise, Dify, Langflow를 조사했고,
이들은 범용 Workflow Builder라는 것을 확인했습니다.

저희는 이 도구들을 대체하는 것이 아니라,
개인화 의류 추천에 필요한 도메인 Workflow Template을 정의했습니다.

현재는 Python 기반 로컬 Builder Prototype에서 Template을 통해
Workflow JSON을 생성하고 실행할 수 있으며,
Flowise는 다음 단계에서 시각적 PoC 도구로 활용할 계획입니다.
```

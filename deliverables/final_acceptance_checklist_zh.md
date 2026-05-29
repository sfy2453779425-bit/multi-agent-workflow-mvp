# 最终验收清单

这份清单用于确认项目是否真正按企业导师和教授反馈推进。

## 一键验证

运行：

```bat
run_verify.cmd
```

或：

```powershell
python verify_project.py
python verify_project.py --external
```

当前验证结果：

```text
All required checks passed.
```

外部工具检查说明：

```text
Flowise package version check: PASS, 3.1.2
Langflow package index check: PASS, 1.9.4
Dify Docker availability check: INFO, 当前机器未安装 Docker
```

## 导师要求 1：不要只做一个推荐 App

状态：已处理

证据：

- `builder_app.py`
- `src/agent_builder/template_builder.py`
- `configs/builder_templates/outfit_recommendation_template.json`
- `configs/builder_templates/commute_outfit_template.json`

说明：

```text
当前项目不是只有一个穿搭 Demo。
同一个 Builder Prototype 可以切换多个模板，并生成不同 Workflow。
```

## 导师要求 2：要有 Builder / Workflow 方向

状态：已处理

证据：

- `run_builder_app.cmd`
- `builder_demo.py --show-builder`
- `builder_demo.py --list-templates`
- `workflow_builder_preview.html`

说明：

```text
项目可以展示 Node Palette、Workflow 顺序、模板生成 JSON、生成后执行。
```

## 导师要求 3：自动化 Workflow，不是用户手动一步一步点

状态：已处理

证据：

```powershell
python builder_demo.py --run-generated "칭다오 다음 주 여행 캐주얼 옷 추천해줘" --user user_a
```

输出包含：

```text
Workflow Trace (6 Nodes)
Question Node
추천 순위
```

## 导师要求 4：信息不足要追问

状态：已处理

证据：

- `src/agent_builder/workflow.py`
- `Question Node`
- 单元测试：
  - `test_question_agent_asks_city_first_when_information_missing`
  - `test_question_agent_continues_to_next_missing_field`
  - `test_question_agent_asks_purpose_or_style_last`

## 导师要求 5：研究 Flowise / Dify / Langflow

状态：已处理

证据：

- `deliverables/builder_tool_comparison_kr.md`
- `deliverables/external_builder_tool_verification_zh.md`
- `external_tools/flowise_poc/README.md`
- `external_tools/dify_poc/README.md`
- `external_tools/langflow_poc/README.md`

真实验证结论：

```text
Flowise: 包存在，版本 3.1.2；本机完整安装/启动超时，已记录限制。
Dify: 需要 Docker；本机没有 Docker，已记录限制。
Langflow: pip index 可查到 1.9.4；下一步可做 custom component。
```

## 导师要求 6：要有数据方向

状态：已处理

证据：

- `deliverables/dataset_research_kr.md`

说明：

```text
本学期使用 mock shopping history 验证 Workflow。
下学期候选数据集包括 H&M Personalized Fashion Recommendations、
Fashion Product Images Small、Fashion Retail Sales Dataset 等。
```

## 导师要求 7：要说明和现有平台差异

状态：已处理

证据：

- `deliverables/competitor_positioning_kr.md`
- `deliverables/professor_answer_drill_kr.md`

核心答法：

```text
我们不是替代 Flowise/Dify/Langflow，也不是重做 Coupang/LotteON 的推荐系统。
我们的贡献是推荐领域 Workflow Template：
Question、Weather、Shopping History、Recommendation Ranking、Compose。
```

## 当前可演示路径

1. Sample Workflow：

```bat
run_desktop.cmd
```

2. Builder Prototype：

```bat
run_builder_app.cmd
```

3. 命令行模板生成：

```powershell
python builder_demo.py --list-templates
python builder_demo.py --run-generated "칭다오 다음 주 여행 캐주얼 옷 추천해줘" --user user_a
python builder_demo.py --run-generated --builder-template configs\builder_templates\commute_outfit_template.json "서울 내일 출근 포멀 옷 추천해줘" --user user_b
```

4. 验收：

```bat
run_verify.cmd
```

## 当前边界

不要在发表中声称：

- 已完成完整商业级拖拽 Builder
- 已跑通 Dify 本地部署
- 已跑通 Flowise 本地启动
- 已接入真实购物平台 OAuth
- 已训练推荐模型

应该声称：

```text
本学期完成了可运行 Sample Workflow、模板化 Builder Prototype、
两个推荐模板、外部 Builder 工具调研和验证入口。
```

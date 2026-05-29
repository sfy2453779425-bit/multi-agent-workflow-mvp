# 企业导师要求对照表

这份文件用于说明：当前项目已经按企业导师的反馈，从“单个穿搭 Demo”
调整为“Sample Workflow + Builder Prototype”的方向。

## 1. 导师要求：不要只做一个推荐 App

导师核心意思：

```text
现在做出来的是一个 sample。
真正重要的是以后能不能快速组装类似的 workflow。
```

当前对应实现：

- `configs/outfit_workflow.json`
  - 保留当前可运行的穿搭推荐 Sample Workflow。
- `configs/builder_templates/outfit_recommendation_template.json`
  - 新增 Builder Template，用模板定义节点、顺序、角色、输入输出。
- `configs/builder_templates/commute_outfit_template.json`
  - 新增第二个通勤/上班穿搭模板，证明不是只服务一个旅行穿搭场景。
- `src/agent_builder/template_builder.py`
  - 新增模板生成器，可以从 Builder Template 生成可执行 Workflow JSON。

## 2. 导师要求：像 Flowise/Dify/Langflow 那样做 Workflow Builder 思路

导师核心意思：

```text
研究 Flowise / Dify / Langflow，不要从零造完整平台。
用 Builder 的方式理解你们的系统。
```

当前对应实现：

- `deliverables/builder_tool_comparison_kr.md`
  - 对比 Flowise / Dify / Langflow 的功能、优缺点和本项目关系。
- `deliverables/dataset_research_kr.md`
  - 整理后续可接入的 Kaggle / 电商推荐数据集。
- `deliverables/competitor_positioning_kr.md`
  - 整理 Coupang、LotteON、11번가 等现有推荐系统与本项目差异。
- `configs/flowise_poc_mapping.json`
  - 把当前 6 个 Node 映射到 Flowise/Dify/Langflow 类 Builder 节点。
- `workflow_builder_preview.html`
  - 静态可视化 Builder 预览页。
- `builder_app.py`
  - 可运行的本地 Builder Prototype。

## 3. 导师要求：要有自动化 Workflow，不是用户一步一步手动点

导师核心意思：

```text
输入一次后，Agent/Node 自动协作，最后输出结果。
```

当前对应实现：

- `src/agent_builder/workflow.py`
  - 自动按顺序执行：

```text
Request Parser
-> Question
-> Weather Tool
-> Shopping History Analysis
-> Recommendation
-> Compose
```

- `builder_demo.py --run-generated`
  - 从 Builder Template 生成 Workflow 后直接执行，证明不是只停留在画图。
- `builder_demo.py --list-templates`
  - 展示当前 Builder 支持多个模板。

## 4. 导师要求：信息不足时要追问

导师核心意思：

```text
如果用户没有说清楚城市、日期、目的或风格，系统要补问。
```

当前对应实现：

- `Question Node`
  - 检查缺失字段：
    - city
    - date
    - purpose_or_style
  - 缺失时停止后续工具调用，先返回追问。

测试覆盖：

- `test_question_agent_asks_city_first_when_information_missing`
- `test_question_agent_continues_to_next_missing_field`
- `test_question_agent_asks_purpose_or_style_last`

## 5. 导师要求：每个 Agent/Node 要职责清楚

当前对应实现：

- `configs/builder_templates/outfit_recommendation_template.json`
  - 每个节点都有：
    - `id`
    - `name`
    - `category`
    - `role`
    - `inputs`
    - `outputs`
    - `builder_equivalent`

这可以用于 PPT 中解释：

```text
不是 3 个独立 Agent，而是一个推荐 Workflow 中的多个功能 Node。
```

## 6. 导师要求：要能展示 Builder 方向

当前展示路径：

1. 打开 Sample Demo：

```bat
run_desktop.cmd
```

2. 打开 Builder Prototype：

```bat
run_builder_app.cmd
```

3. 命令行展示 Builder 生成：

```powershell
python builder_demo.py --show-builder
python builder_demo.py --run-generated "칭다오 다음 주 여행 캐주얼 옷 추천해줘"
```

## 7. 当前项目边界

已经实现：

- 可运行穿搭 Sample Workflow
- 追问机制
- 天气 API
- 模拟购物记录分析
- 推荐排序
- Builder Template
- 第二个通勤/上班推荐 Template
- 从模板生成 Workflow JSON
- 生成后的 Workflow 可执行
- 本地 Builder Prototype UI
- Flowise/Dify/Langflow 对比资料

没有假装完成：

- 完整拖拽式商业 Builder
- 真实购物平台 OAuth
- 大规模推荐模型训练
- 企业级监控和权限系统

## 8. 答辩核心说法

```text
저희는 단순히 의류 추천 App을 만든 것이 아니라,
추천 업무를 구성하는 Workflow Template을 정의하고,
그 Template으로 실행 가능한 Workflow를 생성하는 Builder Prototype을 구현했습니다.

현재 결과물은 완성된 상용 Builder는 아니지만,
Sample Workflow와 Builder Template, 그리고 로컬 Builder Prototype을 통해
다음 학기 확장 방향을 검증했습니다.
```

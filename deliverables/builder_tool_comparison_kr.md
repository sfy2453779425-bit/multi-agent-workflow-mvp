# Builder Tool Research: Flowise / Dify / Langflow

## 목적

기업 멘토가 언급한 기존 Agent Builder 도구를 조사하고, 본 프로젝트가
어디에 위치하는지 정리한다. 결론은 다음과 같다.

```text
기존 Builder를 대체하는 것이 아니라,
추천 도메인에 필요한 Workflow Template을 정의하고 검증한다.
```

## 비교표

| 항목 | Flowise | Dify | Langflow |
|---|---|---|---|
| 핵심 성격 | Visual AI Agent / Workflow Builder | Production-ready LLM App / Agentic Workflow Platform | Python 기반 Visual AI App Framework |
| Visual Workflow | 지원 | 지원 | 지원 |
| Tool / API 호출 | Tool, MCP Tool 등 지원 | Built-in / Custom / Workflow / MCP Tools 지원 | Component, Agent Tool, Custom Component 지원 |
| Multi-Agent / Multi-Node | AgentFlow, Multi-Agent 구조 지원 | Workflow / Chatflow / Agent Node 기반 구성 가능 | Flow, Agent, Component 조합 가능 |
| 추천 Agent 적합성 | 높음. 빠른 시각화와 발표용 PoC에 적합 | 중간~높음. 운영/배포/LLMOps에 강함 | 높음. Python 커스터마이징에 강함 |
| 장점 | 시각적 설명이 쉽고 멘토가 말한 Lego식 Workflow와 가장 유사 | API, 권한, 지식베이스, 모니터링 등 제품화 기능이 강함 | Python 기반이라 기존 코드와 연결하기 좋고 커스텀 컴포넌트가 쉬움 |
| 한계 | 범용 도구라 추천 도메인 로직은 별도 설계 필요 | MVP 발표용으로는 다소 무겁고 플랫폼 성격이 강함 | 설치/구성 및 커스텀 컴포넌트 설계 부담이 있음 |
| 본 프로젝트와 관계 | 1차 PoC 도구 후보 | 차기 제품화/운영 관점 비교 대상 | Python 기반 확장 후보 |

## 본 프로젝트의 선택

이번 학기에는 **Flowise를 우선 PoC 기준으로 사용**한다.

이유:

- 시각적 Workflow 설명이 가장 쉽다.
- 현재 6-Node Sample Workflow를 그대로 노드 그래프로 매핑할 수 있다.
- 교수님/멘토가 질문할 "기존 Builder를 쓰면 되는 것 아닌가?"에 직접 답할 수 있다.

하지만 실제 코드는 당장 Flowise로 전면 이전하지 않는다. 현재 Python MVP는
Sample Workflow와 로컬 Builder Prototype으로 유지하고,
Flowise/Dify/Langflow는 외부 Builder 방향 검증용으로 사용한다.

## 발표용 한 문장

```text
Flowise, Dify, Langflow 같은 범용 Builder는 이미 존재하지만,
개인화 추천에 필요한 사용자 정보 보완, 쇼핑 기록 분석, 날씨 반영,
추천 우선순위화 Workflow Template은 별도로 설계해야 합니다.
저희는 이 도메인 특화 Workflow 구조를 현재 MVP로 검증하고 있습니다.
```

## 참고 링크

- Flowise AgentFlow V2: https://docs.flowiseai.com/using-flowise/agentflowv2
- Flowise Multi-Agents: https://docs.flowiseai.com/using-flowise/agentflowv1/multi-agents
- Dify Workflow / Chatflow: https://docs.dify.ai/en/use-dify/build/workflow-chatflow
- Dify Tools: https://docs.dify.ai/en/guides/workflow/node/tools
- Langflow Overview: https://docs.langflow.org/next
- Langflow Build Flows: https://docs.langflow.org/concepts-flows

# Multi-Agent Workflow MVP Scope

## Revised Project Definition

This project is not a full AI Agent Builder platform.

It is a minimal MVP that proves this idea:

> A template/config file can define several small Agents and connect them into a fixed workflow, so a user request can be handled by reusable Agent steps instead of one hard-coded script.

Korean presentation sentence:

> 본 프로젝트는 완성형 Agent Builder 플랫폼이 아니라, 템플릿 기반으로 여러 Agent를 구성하고 순차 Workflow로 실행하는 Multi-Agent Workflow Builder MVP입니다.

## Current Workflow Demo

Config:

- `configs/outfit_workflow.json`

Execution order:

1. Request Parser Agent
2. Weather Agent
3. Shopping Analysis Agent
4. Recommendation Agent
5. Compose Agent

Implementation:

- `src/agent_builder/workflow.py`
- Reuses `src/agent_builder/engine.py`
- Reuses `configs/outfit_agent.json` as the base recommendation logic
- Reuses `data/shopping_history.json` as simulated purchase history

## What Is In Scope

- JSON-based workflow definition
- Sequential multi-Agent execution
- Weather API tool call
- Local shopping-history analysis
- Recommendation rule matching
- Web UI trace showing each Agent step
- CLI demo and unit tests

## What Is Out Of Scope For This MVP

- Full visual drag-and-drop Builder
- Admin dashboard
- Agent deployment system
- Real shopping-platform OAuth integration
- Local Qwen/Gemma model training
- Complex orchestrator features such as retry, branching, memory, or monitoring

## Mentor Questions

Simple questions to ask the enterprise mentor:

```text
1. 저희가 단순 추천 Agent가 아니라,
여러 Agent를 연결하는 Workflow Builder MVP로 방향을 잡아도 괜찮을까요?

2. MVP에서는 Agent를 3~5개 정도로 나누면 충분할까요?
예: 요청 분석, 날씨 조회, 쇼핑 기록 분석, 추천 생성, 최종 출력

3. Workflow는 일단 순차 실행 방식으로만 구현해도 MVP로 충분할까요?

4. Builder 화면은 복잡한 관리자 페이지가 아니라,
Agent 설정과 실행 흐름만 보여줘도 괜찮을까요?

5. 최종 발표에서 재사용성, 제작 시간 단축, Workflow 구조 중
어떤 점을 가장 강조하면 좋을까요?
```

## Professor Questions

Simple questions to ask the professor:

```text
교수님, 기업 멘토님께서는 저희가 단순 의류 추천 Agent가 아니라,
여러 Agent를 구성하고 Workflow로 연결하는 Builder MVP 방향으로 진행하면 좋겠다고 조언해 주셨습니다.

저희는 MVP 범위를 크게 잡지 않고,
요청 분석 Agent, 날씨 Agent, 쇼핑 기록 분석 Agent, 추천 Agent, 출력 Agent 정도로 나누어
순차적으로 실행되는 구조를 만들려고 합니다.

이 방향이 종합설계 프로젝트로 적절한지 확인 부탁드립니다.
또한 평가에서는 추천 성능보다 Agent 제작 과정 단축, 재사용성, Workflow 구조를 중심으로 설명해도 괜찮을지 여쭤보고 싶습니다.

추가로, 멘토님께서 Qwen/Gemma 같은 오픈소스 모델 활용 가능성도 말씀해 주셨는데,
학교에서 사용할 수 있는 GPU 자원이 있는지도 확인하고 싶습니다.
다만 현재 MVP는 우선 API 기반 또는 경량 방식으로 구현하고,
GPU가 가능하면 추후 로컬 모델 실험으로 확장하려고 합니다.
```

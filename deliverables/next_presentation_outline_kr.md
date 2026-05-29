# Next Presentation Outline

목표 발표 시간: 15분  
데모 시간: 최대 2분

## 발표 제목

```text
개인화 의류 추천을 위한 Multi-Agent Workflow Builder MVP
```

## Slide 1. 문제 재정의

핵심 메시지:

```text
단순히 의류 추천 앱을 만드는 것이 아니라,
추천 업무를 구성하는 Workflow를 템플릿화하는 것이 목표입니다.
```

말할 내용:

- 사용자는 날씨, 일정, 스타일, 쇼핑 기록을 따로 고려해야 한다.
- 기존 추천은 개인 맥락이 부족하다.
- 하나의 Agent 앱만 만들면 다른 추천 업무로 확장하기 어렵다.

## Slide 2. 현재 구현된 Sample Workflow

보여줄 내용:

```text
Request Parser
-> Question
-> Weather Tool
-> Shopping History Analysis
-> Recommendation
-> Compose
```

말할 내용:

- 현재 시스템은 완성된 Builder가 아니라 Sample Workflow다.
- 이 Sample은 Builder가 생성해야 할 목표 결과물이다.
- 정보가 부족하면 Question Node가 먼저 추가 질문을 한다.
- 같은 Builder Prototype에서 여행/일반 의류 추천 템플릿과 출근/통근 템플릿을 전환할 수 있다.

## Slide 3. 기존 Builder 도구 조사

표로 넣을 내용:

| 도구 | 강점 | 한계 | 우리 프로젝트와 관계 |
|---|---|---|---|
| Flowise | 시각적 Workflow, AgentFlow | 추천 도메인 로직은 직접 설계 필요 | 1차 PoC 기준 |
| Dify | 운영/배포/LLMOps 강점 | MVP 발표용으로는 무거움 | 차기 제품화 후보 |
| Langflow | Python 확장성 | 커스텀 설계 부담 | Python 연동 후보 |

## Slide 4. 차별점

핵심 답변:

```text
기존 Builder 자체를 대체하지 않는다.
추천 도메인에 필요한 Workflow Template을 정의하고 검증한다.
```

강조할 도메인 특화 요소:

- 사용자 정보 보완 Question Node
- 쇼핑 기록 기반 스타일 분석
- 실시간 날씨 반영
- 보유 단품 우선 추천
- 추천 결과 Ranking

## Slide 5. Flowise PoC Mapping

보여줄 내용:

- `workflow_builder_preview.html`
- `run_builder_app.cmd`
- `configs/builder_templates/outfit_recommendation_template.json`
- `configs/flowise_poc_mapping.json`

말할 내용:

```text
현재 Python Workflow를 Flowise 스타일의 노드 구조로 매핑했고,
로컬 Builder Prototype에서 템플릿을 통해 Workflow JSON을 생성한 뒤
다시 실행할 수 있게 만들었습니다.
```

## Slide 6. Demo

2분 데모 순서:

1. `run_desktop.cmd` 실행
2. 입력:

```text
다음 주에 칭다오 여행 가는데 캐주얼 옷 추천해줘
```

3. 출력 확인:
   - 날씨 반영
   - 쇼핑 기록 분석
   - 추천 Ranking
   - Trace에 6개 Node 표시

4. 짧게 말하기:

```text
이 결과가 단순 Chatbot 답변이 아니라,
6개 Workflow Node가 순서대로 실행된 결과입니다.
```

## Slide 7. 다음 학기 계획

계획:

- Flowise/Dify/Langflow 중 하나를 선택해 실제 Builder PoC 구현
- 현재 JSON Workflow를 Builder Template으로 변환
- 현재 2개 템플릿을 더 많은 추천 업무 템플릿으로 확장
- Shopping API / OAuth / 실제 데이터 연동 검토
- 더 많은 추천 도메인으로 확장

예시 확장:

- 여행 준비물 추천
- 계절 쇼핑 추천
- 업무 상황별 복장 추천

## 결론

```text
이번 학기에는 개인화 의류 추천 Sample Workflow를 구현했고,
다음 단계에서는 이 Workflow를 Builder에서 재사용 가능한
추천 도메인 Template으로 확장하는 방향을 검증합니다.
```

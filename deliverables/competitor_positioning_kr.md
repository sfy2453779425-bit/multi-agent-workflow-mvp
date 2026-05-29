# Competitor / Existing Platform Positioning

## 목적

교수님과 기업 멘토가 공통으로 지적한 부분은 다음이다.

```text
이미 추천 시스템과 Agent Builder가 많은데,
왜 이 프로젝트가 필요한가?
```

이 문서는 기존 플랫폼의 방향과 우리 프로젝트의 차이를 정리한다.

## 기존 추천 시스템 사례

| 플랫폼/사례 | 확인된 방향 | 우리 프로젝트와의 차이 |
|---|---|---|
| Coupang | 홈 피드, 검색, 광고 등에서 추천/개인화 모델을 사용 | 대형 플랫폼 내부 추천 시스템이며, 사용자가 Workflow를 구성하는 Builder가 아님 |
| LotteON | Amazon SageMaker/MLOps 기반 실시간 추천 시스템 사례 | 추천 모델 운영 사례에 가깝고, 도메인 Workflow Template Builder는 아님 |
| 11번가 Ai홈 | AI 기반 초개인화 추천 서비스 | 사용자-facing 추천 서비스이며, 추천 Workflow 생성 도구는 아님 |
| Lotte Card Discovery | 결제/그룹 데이터를 활용한 개인화 추천 | 데이터 기반 추천 서비스이며, multi-node Agent Workflow 구조는 아님 |

## 기존 Builder 도구 사례

| 도구 | 강점 | 우리 프로젝트와의 차이 |
|---|---|---|
| Flowise | Visual AgentFlow / Workflow 구성 | 범용 Builder라서 추천 도메인 로직은 직접 설계해야 함 |
| Dify | LLM App 운영, Workflow, Tool, Knowledge, API 배포 | 제품화 기능이 강하지만 추천 도메인 Template은 별도 설계 필요 |
| Langflow | Python 기반 Visual AI Flow | 커스텀 컴포넌트 확장에 적합하지만 추천 업무 구조는 직접 정의 필요 |

## 본 프로젝트의 위치

```text
기존 추천 시스템처럼 완성된 상용 추천 엔진을 만드는 것이 아니다.
기존 Builder처럼 범용 플랫폼을 새로 만드는 것도 아니다.

본 프로젝트는 개인화 추천 업무를 구성하는 Workflow Template을 정의하고,
그 Template으로 실행 가능한 Sample Workflow를 생성하는 MVP다.
```

## 차별점

- 정보가 부족하면 Question Node가 먼저 보완 질문을 한다.
- 날씨 API와 쇼핑 기록을 하나의 Workflow 안에서 결합한다.
- 보유한 옷을 우선 추천하고, 추가 구매 후보를 뒤에 배치한다.
- 추천 결과를 ranking으로 보여준다.
- Sample Workflow를 Builder Template에서 생성할 수 있다.

## 발표용 답변

```text
Coupang, LotteON, 11번가 같은 플랫폼은 이미 추천 시스템을 운영하고 있습니다.
하지만 저희 프로젝트는 대형 추천 엔진을 다시 만드는 것이 아니라,
개인화 추천 업무를 구성하는 Workflow Template과 Builder Prototype을 검증합니다.

또한 Flowise/Dify/Langflow 같은 Builder는 범용 도구이므로,
추천 도메인에 필요한 Question Node, Weather Tool, Shopping History Analysis,
Recommendation Ranking 구조는 별도로 정의해야 합니다.
```

## 참고 링크

- Coupang AI / recommendation surfaces: https://www.coupang.jobs/en/life-at-coupang/engineering-blog/accelerating-coupang-s-ai-journey-with-llms/
- LotteON recommendation system on Amazon SageMaker: https://aws.amazon.com/blogs/machine-learning/how-lotteon-built-a-personalized-recommendation-system-using-amazon-sagemaker-and-mlops/
- 11번가 Ai홈 press release: https://m.11stcorp.com/pr/detail?contentId=1532
- Lotte Card Discovery personalized recommendation: https://www.chosun.com/english/market-money-en/2026/03/30/V66ZB6C6WBHANNWUGETWLDQS3A/

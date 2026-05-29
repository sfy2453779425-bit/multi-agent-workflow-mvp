# Professor / Mentor Q&A Drill

## Q1. Flowise / Dify / Langflow를 쓰면 되는 것 아닌가요?

답변:

```text
맞습니다. 그래서 저희도 기존 Builder를 무시하지 않고 조사했습니다.
다만 기존 Builder는 범용 도구이기 때문에, 개인화 추천에 필요한
도메인 Workflow Template은 직접 정의해야 합니다.

저희 프로젝트의 핵심은 Builder 자체를 대체하는 것이 아니라,
추천 도메인에서 필요한 Question Node, 쇼핑 기록 분석, 날씨 반영,
추천 우선순위화 구조를 설계하고 MVP로 검증하는 것입니다.
```

## Q2. 지금 만든 것은 3개 Agent인가요?

답변:

```text
아닙니다. 3개의 독립 Agent를 만든 것이 아니라,
하나의 추천 Workflow 안에서 여러 기능 Node가 협업하는 구조입니다.

현재 구조는 Request Parser, Question, Weather Tool,
Shopping History Analysis, Recommendation, Compose의 6개 Node로 구성됩니다.
```

## Q3. 지금 시스템은 Builder인가요?

답변:

```text
현재 구현은 완성된 상용 Builder가 아니라 Builder가 생성해야 할
Sample Workflow와 이를 템플릿에서 생성하는 로컬 Builder Prototype입니다.

이번 학기에는 먼저 Sample Workflow를 실제로 동작하게 만들고,
그 구조를 Flowise/Dify/Langflow 같은 Builder 방식으로
매핑할 수 있음을 보이는 것이 목표입니다.
```

## Q4. AI에게 그냥 각각 만들어달라고 하면 되는 것 아닌가요?

답변:

```text
단순 코드 생성은 가능하지만, 매번 구조와 품질이 달라질 수 있고
도구 호출, 정보 보완, 추천 우선순위 같은 실행 흐름을 일관되게
보장하기 어렵습니다.

저희는 이런 반복적인 추천 업무를 Workflow Template으로 정의해서,
같은 구조를 안정적으로 재사용하는 방향을 검증합니다.
```

## Q5. 이번 학기 결과물은 무엇인가요?

답변:

```text
첫째, 날씨와 쇼핑 기록을 활용하는 개인화 의류 추천 Sample Workflow를 구현했습니다.
둘째, 정보가 부족할 때 Question Node가 추가 질문을 하도록 만들었습니다.
셋째, Flowise/Dify/Langflow를 조사하고 현재 Workflow를 Builder 구조로 매핑했습니다.
```

## Q6. 다음 학기에는 무엇을 할 건가요?

답변:

```text
다음 학기에는 현재 JSON Workflow를 실제 Builder Template으로 전환하고,
Flowise 또는 Langflow 같은 도구에서 재현 가능한 PoC를 만들 계획입니다.
또한 실제 쇼핑 데이터 API나 OAuth 연동 가능성을 검토하겠습니다.
```

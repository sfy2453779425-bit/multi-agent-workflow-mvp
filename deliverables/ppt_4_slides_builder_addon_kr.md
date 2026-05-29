# PPT Add-on: 4 Core Slides

아래 4장은 기존 발표자료 뒤쪽에 그대로 추가할 수 있는 내용이다.

## Slide A. 현재 구현물의 위치

제목:

```text
현재 구현물: Sample Workflow + Builder Prototype
```

본문:

```text
현재 시스템은 완성된 상용 Visual Builder가 아니라,
개인화 의류 추천 Sample Workflow와 이를 생성하는 로컬 Builder Prototype입니다.
현재는 여행/일반 의류 추천 템플릿과 출근/통근 의류 추천 템플릿을 지원합니다.

사용자 입력을 받은 뒤 6개의 Workflow Node가 순서대로 실행됩니다.

Request Parser -> Question -> Weather Tool
-> Shopping History Analysis -> Recommendation -> Compose
```

발표 멘트:

```text
저희는 이번 학기에 먼저 Builder가 생성해야 할 목표 결과물인 Sample Workflow를 구현했고,
추가로 Builder Template을 통해 여러 추천 Workflow JSON을 생성하고 실행하는 원형을 만들었습니다.
```

## Slide B. 왜 하나의 추천 App만으로는 부족한가

제목:

```text
한 개 Agent App의 한계
```

본문:

```text
한 개의 추천 App만 만들면 다른 추천 업무로 확장할 때
비슷한 코드를 다시 만들거나 수정해야 합니다.

예를 들어 의류 추천, 여행 준비물 추천, 계절 쇼핑 추천은
모두 입력 분석, 정보 보완, 외부 데이터 호출, 추천 생성이라는
공통 구조를 가집니다.

따라서 핵심은 App 하나가 아니라 재사용 가능한 Workflow Template입니다.
```

발표 멘트:

```text
저희가 만들고 싶은 것은 단순 의류 추천 서비스가 아니라,
추천 업무를 빠르게 구성할 수 있는 Workflow Template 구조입니다.
```

## Slide C. 기존 Builder 도구 조사

제목:

```text
Flowise / Dify / Langflow 조사
```

표:

| 도구 | 강점 | 한계 | 우리 프로젝트와 관계 |
|---|---|---|---|
| Flowise | 시각적 AgentFlow, 빠른 PoC | 도메인 로직은 직접 설계 필요 | 1차 PoC 기준 |
| Dify | 배포, API, 지식베이스, 모니터링 | MVP 단계에서는 다소 무거움 | 차기 제품화 후보 |
| Langflow | Python 기반 확장성 | 커스텀 컴포넌트 설계 필요 | Python 연동 후보 |

발표 멘트:

```text
기존 Builder는 이미 존재합니다. 그래서 저희는 이를 대체하려는 것이 아니라,
추천 도메인에 필요한 Workflow Template을 정의하는 방향으로 접근합니다.
```

## Slide D. 우리 프로젝트의 차별점

제목:

```text
추천 도메인 특화 Workflow Template
```

본문:

```text
본 프로젝트의 차별점은 범용 Builder 자체가 아니라,
개인화 추천에 필요한 실행 구조를 정의했다는 점입니다.

1. 부족한 정보를 추가 질문하는 Question Node
2. 날씨 API를 반영하는 Weather Tool Node
3. 쇼핑 기록을 분석하는 Preference Node
4. 보유 단품을 우선하는 Recommendation Ranking
5. 결과를 설명 가능한 형태로 출력하는 Compose Node
```

발표 멘트:

```text
따라서 저희 결과물은 기존 Builder와 경쟁하는 것이 아니라,
기존 Builder 위에서 재사용 가능한 추천 Workflow Template으로 확장될 수 있습니다.
```

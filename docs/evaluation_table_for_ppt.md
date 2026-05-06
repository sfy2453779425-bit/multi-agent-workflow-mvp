# PPT용 평가 표 정리

이 문서는 발표 슬라이드에 바로 옮길 수 있는 평가 표와 핵심 문장을 정리한 것입니다.
실제 소요 시간은 발표 전 팀 기록으로 채워야 합니다.

## Slide 1. 평가 목적

### 제목

```text
Agent 생성 과정 평가
```

### 핵심 문장

```text
본 프로젝트는 완성된 Agent의 기능만 평가하지 않고,
Agent를 만드는 과정에서 Builder가 작업량을 얼마나 줄이는지 평가한다.
```

### 평가 질문

```text
동일한 실행 엔진을 재사용하면,
새로운 Agent를 만들 때 코드 수정량과 제작 시간이 줄어드는가?
```

## Slide 2. 기존 방식 vs Builder 방식

| 작업 단계 | 기존 직접 구현 방식 | Builder 방식 |
|---|---|---|
| 실행 흐름 설계 | Agent마다 직접 설계 | `Plan -> Act -> Analyze -> Decide -> Compose` 재사용 |
| Weather API 호출 | API 호출 코드 직접 작성 | 기존 Weather Tool 재사용 |
| 쇼핑 기록 분석 | 분석 로직 직접 작성 | `shopping.py` 분석 모듈 재사용 |
| 추천 규칙 작성 | Python 코드 수정 | JSON `temperature_rules` 수정 |
| 추가 조건 작성 | Python 조건문 작성 | JSON `conditional_extras` 수정 |
| 출력 형식 작성 | 코드에서 문자열 수정 | JSON `output_template` 수정 |
| 테스트 | 단계별 동작 직접 확인 | trace로 실행 단계 확인 |

### 발표 문장

```text
기존 방식은 Agent마다 입력 처리, 도구 호출, 분석 로직, 추천 규칙을 직접 구현해야 합니다.
반면 Builder 방식은 실행 엔진과 도구를 재사용하고, Agent별 차이는 설정 파일에 작성합니다.
```

## Slide 3. Agent A와 Agent B 비교

| 항목 | Agent A: Outfit Agent | Agent B: Travel Packing Agent | Agent C: Commute Agent |
|---|---|---|---|
| 목적 | 쇼핑 기록 + 날씨 기반 의류 추천 | 쇼핑 기록 + 날씨 기반 여행 준비물 추천 | 쇼핑 기록 + 날씨 기반 통학/출근 준비 추천 |
| 실행 엔진 | 신규 구축 | 기존 엔진 재사용 | 기존 엔진 재사용 |
| Weather API | 연결/재사용 | 재사용 | 재사용 |
| 쇼핑 기록 분석 | 분석 모듈 구축 | 분석 모듈 재사용 | 분석 모듈 재사용 |
| 주요 수정 파일 | `engine.py`, `shopping.py`, `outfit_agent.json`, `shopping_history.json`, `web_app.py` | `travel_pack_agent.json` 중심 | `commute_agent.json` 중심 |
| Python 코드 수정 | 있음 | 없음 또는 최소 | 없음 또는 최소 |
| Config 수정 | 있음 | 있음 | 있음 |
| 출력 확인 | 성공 | 성공 | 성공 |

### 발표 문장

```text
첫 번째 Agent는 공통 엔진과 데이터 분석 구조를 함께 구축해야 했습니다.
두 번째와 세 번째 Agent는 동일한 엔진과 쇼핑 기록 분석 모듈을 재사용하고,
주로 설정 파일을 변경하여 구현했습니다.
```

## Slide 4. 시간 기록 표

아래 표는 발표 전 실제 작업 시간을 채워야 합니다.

| 작업 단계 | Agent A: Outfit | Agent B: Travel | Agent C: Commute | 개선 근거 |
|---|---:|---:|---:|---|
| 문제 정의 | TBD | TBD | TBD | 세 Agent 모두 필요 |
| 데이터 구조 설계 | TBD | TBD | TBD | B/C는 기존 shopping_history 재사용 |
| API 연결 | TBD | TBD | TBD | B/C는 Weather Tool 재사용 |
| 쇼핑 기록 분석 | TBD | TBD | TBD | B/C는 `shopping.py` 재사용 |
| 추천 규칙 작성 | TBD | TBD | TBD | B/C는 config rule만 작성 |
| 출력 템플릿 작성 | TBD | TBD | TBD | B/C는 output_template만 수정 |
| UI 연결 | TBD | TBD | TBD | Agent 선택 UI 재사용 |
| 테스트/디버깅 | TBD | TBD | TBD | 동일 trace로 확인 |
| 총 소요 시간 | TBD | TBD | TBD | B/C 제작 시간 감소 여부 확인 |

### 기록 방법

| 기록 항목 | 작성 방식 |
|---|---|
| 실제 소요 시간 | 팀원이 작업한 실제 시간만 기록 |
| 회의/대기 시간 | 제외 |
| 오류 수정 시간 | 별도 기록 가능 |
| 파일 수정 수 | 실제 수정한 파일 기준 |
| 코드 수정량 | Python 파일과 JSON 설정 파일을 구분 |

## Slide 5. 수정 파일 수 비교

| 항목 | Agent A: Outfit | Agent B: Travel | Agent C: Commute |
|---|---:|---:|---:|
| 수정한 Python 파일 수 | TBD | TBD | TBD |
| 수정한 JSON config 파일 수 | TBD | TBD | TBD |
| 수정한 데이터 파일 수 | TBD | TBD | TBD |
| 수정한 UI 파일 수 | TBD | TBD | TBD |
| 새로 작성한 테스트 수 | TBD | TBD | TBD |

### 발표 문장

```text
Builder 방식의 핵심은 새 Agent를 만들 때 Python 실행 엔진을 다시 작성하지 않는 것입니다.
따라서 두 번째 이후 Agent에서는 Python 코드 수정량보다 설정 파일 수정량이 중심이 됩니다.
```

## Slide 6. 현재 구현 기준 요약

현재 코드 기준으로 설명 가능한 사실:

| 항목 | 현재 상태 |
|---|---|
| 공통 실행 엔진 | `src/agent_builder/engine.py` |
| 쇼핑 기록 분석 모듈 | `src/agent_builder/shopping.py` |
| 의류 추천 설정 | `configs/outfit_agent.json` |
| 여행 준비물 설정 | `configs/travel_pack_agent.json` |
| 쇼핑 기록 데이터 | `data/shopping_history.json` |
| 실행 흐름 | `Plan -> Act -> Analyze -> Decide -> Compose` |
| Web Demo | `web_app.py` |
| 테스트 | `run_tests.cmd` 통과 |

현재 파일 기준 객관적 수치:

| 항목 | 값 |
|---|---:|
| 지원 Agent 수 | 3 |
| Agent 설정 파일 수 | 3 |
| Outfit config 라인 수 | 58 |
| Travel config 라인 수 | 58 |
| Commute config 라인 수 | 58 |
| 공통 실행 엔진 라인 수 | 248 |
| 쇼핑 기록 분석 모듈 라인 수 | 85 |
| 모의 쇼핑 기록 사용자 수 | 2 |
| 전체 테스트 수 | 6 |

### 발표 문장

```text
현재 세 Agent는 같은 실행 엔진과 같은 쇼핑 기록 분석 모듈을 사용합니다.
차이는 Agent별 JSON 설정 파일에 있으며, Web Demo에서 설정을 바꾸면 다른 Agent로 실행됩니다.
```

```text
현재 세 Agent의 설정 파일은 각각 58줄이며,
공통 실행 엔진과 쇼핑 기록 분석 모듈은 세 Agent가 함께 재사용합니다.
```

## Slide 7. 결론 표

| 평가 관점 | 결과 |
|---|---|
| 재사용성 | 공통 엔진과 분석 모듈을 세 Agent에서 재사용 |
| 설정 가능성 | 추천 규칙과 출력 형식을 JSON으로 변경 가능 |
| 확장 가능성 | 유사한 추천 Agent를 config 추가로 확장 가능 |
| 한계 | 아직 완전한 No-code UI는 아니며, 설정 파일을 직접 작성해야 함 |
| 다음 단계 | 실제 작업 시간 기록으로 Builder 효과 정량화 |

### 발표 결론 문장

```text
본 MVP는 완전한 Builder 플랫폼은 아니지만,
동일한 실행 엔진에서 설정 파일만 변경하여 서로 다른 Agent를 실행할 수 있음을 보였습니다.
향후 실제 작업 시간과 수정 파일 수를 기록하여 Builder 방식의 효율성을 정량적으로 평가할 계획입니다.
```

## 채워야 할 실제 데이터 체크리스트

발표 전 아래 값을 팀에서 직접 채워야 합니다.

| 체크 항목 | 상태 |
|---|---|
| Outfit Agent 총 제작 시간 | TBD |
| Travel Packing Agent 총 제작 시간 | TBD |
| Commute Preparation Agent 총 제작 시간 | TBD |
| Outfit Agent 수정 파일 수 | TBD |
| Travel Packing Agent 수정 파일 수 | TBD |
| Commute Preparation Agent 수정 파일 수 | TBD |
| Python 코드 수정량 | TBD |
| JSON config 수정량 | TBD |
| 오류 수정/디버깅 시간 | TBD |
| Demo 실행 성공 여부 | 성공 |

## 주의할 표현

피해야 할 표현:

```text
초보자도 바로 만들 수 있습니다.
완전한 No-code 플랫폼입니다.
모든 쇼핑몰 구매 기록을 읽을 수 있습니다.
```

사용할 표현:

```text
현재는 설정 기반 Builder MVP입니다.
모의 쇼핑 기록 JSON을 사용해 구매 기록 분석 흐름을 검증했습니다.
유사한 Agent 생성 시 실행 엔진 재사용 가능성을 확인했습니다.
실제 쇼핑몰 API는 향후 데이터 소스 교체 방식으로 연동할 수 있습니다.
```

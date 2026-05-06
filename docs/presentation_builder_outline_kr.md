# 설정 기반 AI Agent Builder MVP 발표 구성안

## 발표 핵심 메시지

저희 프로젝트의 핵심은 특정 의류 추천 Agent 하나를 만드는 것이 아니라,
비슷한 구조의 Agent를 더 빠르게 만들 수 있는 설정 기반 Builder MVP를 검증하는 것입니다.

```text
같은 실행 엔진
+ 다른 JSON 설정 파일
= 다른 Agent 동작
```

발표에서 반드시 강조할 문장:

```text
Personalized Outfit Agent는 최종 결과물 자체가 아니라,
Builder의 가능성을 보여주기 위한 예시 Agent입니다.
```

## 1. Problem

특정 목적의 AI Agent를 만들기 위해서는 매번 비슷한 작업을 반복해야 합니다.

예를 들어 쇼핑 기록과 날씨를 활용하는 추천 Agent를 직접 구현하려면 다음 작업이 필요합니다.

1. 사용자 입력 분석
2. 외부 API 연결
3. 사용자 데이터 구조 설계
4. 데이터 분석 로직 작성
5. 추천 규칙 작성
6. 출력 형식 작성
7. UI 연결 및 테스트

문제는 새로운 Agent를 만들 때도 이 과정이 반복된다는 점입니다.

발표 문장:

```text
기존 방식에서는 Agent를 하나 만들 때마다 입력 처리, 도구 호출, 데이터 분석,
추천 규칙, 출력 형식을 다시 구현해야 합니다.
저희는 이 반복 작업을 설정 파일 중심으로 줄일 수 있는지 확인하고자 했습니다.
```

## 2. Goal

본 프로젝트의 목표는 완성된 상용 Builder 플랫폼이 아니라,
Builder의 핵심 가설을 MVP로 검증하는 것입니다.

검증하려는 가설:

```text
공통 실행 엔진을 만들어 두면,
새 Agent를 만들 때 Python 코드를 크게 수정하지 않고
설정 파일 변경만으로 Agent의 동작을 바꿀 수 있다.
```

## 3. Proposed Method

저희는 Agent 실행 과정을 고정된 흐름으로 분리했습니다.

```text
Plan -> Act -> Analyze -> Decide -> Compose
```

| 단계 | 역할 |
|---|---|
| Plan | 사용자 입력에서 도시, 날짜, 사용자, Agent 설정 확정 |
| Act | Weather API와 shopping_history 데이터 소스 호출 |
| Analyze | 쇼핑 기록에서 선호 스타일, 색상, 카테고리 추출 |
| Decide | 날씨와 구매 기록을 기반으로 추천 규칙 적용 |
| Compose | 설정 파일의 output_template로 응답 생성 |

설정 파일에서 바꿀 수 있는 항목:

| 설정 항목 | 역할 |
|---|---|
| `agent_name` | Agent 이름 |
| `tools` | 사용할 도구 선택 |
| `temperature_rules` | 온도별 추천 규칙 |
| `conditional_extras` | 비, 일교차 등 추가 조건 |
| `output_template` | 최종 출력 형식 |

## 4. System Architecture

```text
User Input
  -> Web UI
  -> AgentBuilderEngine
  -> Config Loader
  -> Weather Tool
  -> Shopping History Analyzer
  -> Rule Executor
  -> Output Template Renderer
  -> Final Response
```

현재 구현 파일:

| 파일 | 역할 |
|---|---|
| `src/agent_builder/engine.py` | 공통 실행 엔진 |
| `src/agent_builder/shopping.py` | 쇼핑 기록 분석 및 보유 단품 선택 |
| `configs/outfit_agent.json` | 의류 추천 Agent 설정 |
| `configs/travel_pack_agent.json` | 여행 준비물 Agent 설정 |
| `data/shopping_history.json` | 모의 구매 기록 데이터 |
| `web_app.py` | Web Demo UI |

## 5. Demo 1: Personalized Outfit Agent

입력 예시:

```text
서울 내일 날씨에 맞춰 내 스타일로 옷 추천해줘
```

실행 과정:

```text
Plan: 도시=서울, 날짜=내일, 사용자=user_a
Act: Weather API + shopping_history 호출
Analyze: 쇼핑 기록에서 스타일/색상/카테고리 추출
Decide: 날씨와 구매 기록 기반 추천 규칙 적용
Compose: 의류 추천 응답 생성
```

강조할 점:

```text
이 Agent는 사용자의 쇼핑 기록을 실제로 읽고,
구매한 단품 중에서 날씨에 맞는 아이템을 추천합니다.
```

## 6. Demo 2: Travel Packing Agent

두 번째 Demo의 목적은 Builder의 재사용성을 보여주는 것입니다.

변경한 것:

```text
configs/travel_pack_agent.json
```

재사용한 것:

```text
src/agent_builder/engine.py
src/agent_builder/shopping.py
data/shopping_history.json
Weather API tool
```

발표 문장:

```text
두 번째 Agent에서는 실행 엔진을 새로 만들지 않고,
설정 파일을 변경하여 여행 준비물 추천 Agent로 동작을 바꿨습니다.
```

## 6-1. Demo 3: Commute Preparation Agent

세 번째 Demo의 목적은 비슷한 난이도의 다른 주제에서도 같은 실행 엔진을 재사용할 수 있음을 보여주는 것입니다.

변경한 것:

```text
configs/commute_agent.json
```

재사용한 것:

```text
src/agent_builder/engine.py
src/agent_builder/shopping.py
data/shopping_history.json
Weather API tool
```

발표 문장:

```text
세 번째 Agent 역시 Python 실행 엔진을 새로 작성하지 않고,
통학/출근 준비 추천에 맞는 설정 파일만 추가하여 구현했습니다.
```

## 7. Evaluation: Agent 생성 과정 비교

교수님 피드백에 따라, 저희는 완성된 Agent의 기능만 보지 않고
Agent를 만드는 과정 자체를 평가합니다.

평가 기준:

| 평가 항목 | 설명 |
|---|---|
| 단계 수 | Agent를 만들기 위해 필요한 작업 단계 |
| 수정 파일 수 | 새 Agent 생성 시 수정한 파일 개수 |
| Python 코드 수정량 | 실행 엔진을 얼마나 수정했는지 |
| Config 수정량 | 설정 파일 작성/수정량 |
| 생성 시간 | Agent 생성에 걸린 실제 시간 |
| 실행 성공 여부 | 동일한 trace 구조로 정상 실행되는지 |

## 8. Process Time Log

시간 기록 문서는 다음 파일에 정리했습니다.

```text
docs/process_time_log.md
```

발표용 비교 표:

| 항목 | Agent A: Outfit | Agent B: Travel | Agent C: Commute | 해석 |
|---|---:|---:|---:|---|
| 수정한 Python 파일 수 | TBD | TBD | TBD | B/C는 engine 재사용 |
| 수정한 config 파일 수 | TBD | TBD | TBD | 주로 config 변경 |
| 데이터 파일 수정 수 | TBD | TBD | TBD | shopping_history 재사용 |
| 총 작업 시간 | TBD | TBD | TBD | B/C 생성 시간 감소 여부 확인 |
| 실행 성공 여부 | 성공 | 성공 | 성공 | 동일한 실행 흐름 |

주의:

```text
TBD 값은 발표 전 실제 작업 기록으로 채워야 합니다.
```

## 9. Comparison

| 항목 | 직접 구현 방식 | Builder 방식 |
|---|---|---|
| 실행 흐름 설계 | 매번 직접 설계 | 고정 흐름 재사용 |
| Weather API | 직접 연결 | 기존 tool 재사용 |
| 쇼핑 기록 분석 | 직접 코드 작성 | analyzer 재사용 |
| 추천 규칙 | Python 코드 수정 | JSON 설정 변경 |
| 출력 형식 | 코드 수정 | output_template 변경 |
| 새 Agent 생성 | 구현 부담 큼 | 설정 중심으로 변경 |

핵심 주장:

```text
Builder 방식은 첫 번째 Agent를 만들 때는 공통 엔진 구축 비용이 필요하지만,
두 번째 이후의 유사 Agent에서는 엔진을 재사용하여 작업량을 줄일 수 있습니다.
```

## 10. Limitation

현재 MVP의 한계도 명확히 말해야 합니다.

| 한계 | 설명 |
|---|---|
| 실제 쇼핑몰 API 미연동 | 현재는 모의 쇼핑 기록 JSON 사용 |
| 완전한 No-code Builder 아님 | 설정 파일을 직접 수정해야 함 |
| 지원 Agent 수 제한 | 현재 의류 추천, 여행 준비물 추천, 통학/출근 준비 3개 |
| 추천 품질 평가 미완성 | 현재는 생성 과정 효율성 검증 중심 |

발표 문장:

```text
현재 MVP는 실제 쇼핑몰 API 대신 모의 쇼핑 기록 JSON을 사용합니다.
하지만 데이터 소스 계층을 분리했기 때문에 향후 Cafe24, Shopify, WooCommerce 같은
주문 API 또는 사용자 업로드 파일과 연동할 수 있습니다.
```

## 11. Conclusion

```text
본 프로젝트는 특정 Agent 하나를 완성하는 것이 아니라,
설정 기반으로 유사한 Agent를 더 빠르게 만들 수 있는 가능성을 검증한 Builder MVP입니다.
세 개의 Agent Demo를 통해 동일한 실행 엔진에서 설정 파일만 변경하여
다른 Agent 동작을 만들 수 있음을 보였습니다.
향후에는 실제 작업 시간 기록과 더 많은 Agent 예시를 통해
Builder 방식의 효율성을 정량적으로 검증할 계획입니다.
```

## Demo 시연 순서

1. Web Demo 실행
2. UI 언어를 한국어로 설정
3. `Personalized Outfit Agent` 선택
4. `User A`로 실행
5. `Shopping History Analysis`와 `Analyze` 단계 설명
6. `User B`로 변경하여 개인화 결과 비교
7. `Travel Packing Agent`로 변경
8. `Loaded Config`가 `travel_pack_agent.json`으로 바뀌는 점 설명
9. `Commute Preparation Agent`로 변경
10. `Loaded Config`가 `commute_agent.json`으로 바뀌는 점 설명
11. trace는 동일하게 `Plan -> Act -> Analyze -> Decide -> Compose`임을 강조

## 예상 질문 및 답변

### Q1. 이건 그냥 옷 추천 Agent 아닌가요?

아닙니다. 의류 추천 Agent는 Builder의 가능성을 보여주기 위한 예시입니다.
핵심은 동일한 실행 엔진에서 설정 파일만 변경하여 다른 Agent도 만들 수 있다는 점입니다.

### Q2. Builder의 효과를 어떻게 평가하나요?

Agent 생성 과정을 단계별로 나누고, 기존 방식과 Builder 방식의 소요 시간,
수정 파일 수, Python 코드 수정량, config 수정량을 비교합니다.

### Q3. 실제 쇼핑몰 구매 기록을 읽나요?

현재 MVP는 실제 쇼핑몰 API 대신 모의 쇼핑 기록 JSON을 사용합니다.
하지만 시스템은 shopping_history 데이터 소스를 읽고 분석하는 구조로 구현되어 있어,
향후 쇼핑몰 API나 사용자 업로드 파일로 대체할 수 있습니다.

### Q4. 왜 여러 Agent가 필요한가요?

하나의 Agent만 보여주면 Builder의 재사용성을 증명하기 어렵습니다.
Travel Packing Agent와 Commute Preparation Agent를 같은 엔진에서 설정만 바꿔 실행함으로써,
Builder 방식이 유사한 Agent 생성에 재사용될 수 있음을 보여줍니다.

### Q5. 완전한 No-code Builder인가요?

아직 완전한 No-code 플랫폼은 아닙니다.
현재는 설정 기반 Builder MVP이며, 핵심 가설인 실행 엔진 재사용과 설정 기반 Agent 변경을 검증하는 단계입니다.

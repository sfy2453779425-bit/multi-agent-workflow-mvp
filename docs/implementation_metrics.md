# 구현 지표 정리

이 문서는 현재 프로젝트 파일을 기준으로 확인 가능한 객관적 구현 지표를 정리한 것입니다.
작업 시간은 별도 기록이 필요하지만, 파일 수와 라인 수는 현재 코드 기준으로 발표에 활용할 수 있습니다.

## 현재 구현 파일 라인 수

| 분류 | 파일 | 라인 수 |
|---|---|---:|
| 공통 실행 엔진 | `src/agent_builder/engine.py` | 248 |
| 쇼핑 기록 분석 모듈 | `src/agent_builder/shopping.py` | 85 |
| 의류 추천 설정 | `configs/outfit_agent.json` | 58 |
| 여행 준비물 설정 | `configs/travel_pack_agent.json` | 58 |
| 통학/출근 준비 설정 | `configs/commute_agent.json` | 58 |
| 쇼핑 기록 데이터 | `data/shopping_history.json` | 126 |
| Web Demo UI | `web_app.py` | 553 |
| Builder 테스트 | `tests/test_agent_builder.py` | 65 |

## 역할별 구현량

| 역할 | 파일 수 | 주요 파일 | 설명 |
|---|---:|---|---|
| 공통 Python 엔진 | 2 | `engine.py`, `shopping.py` | Agent 실행 흐름과 쇼핑 기록 분석 |
| Agent 설정 | 3 | `outfit_agent.json`, `travel_pack_agent.json`, `commute_agent.json` | Agent별 규칙과 출력 형식 |
| 데이터 | 1 | `shopping_history.json` | 모의 구매 기록 |
| UI | 1 | `web_app.py` | Builder Demo 화면 |
| 테스트 | 1 | `test_agent_builder.py` | 세 Agent와 사용자별 결과 확인 |

## Agent별 차이

| 항목 | Outfit Agent | Travel Packing Agent | Commute Preparation Agent |
|---|---|---|---|
| 설정 파일 | `configs/outfit_agent.json` | `configs/travel_pack_agent.json` | `configs/commute_agent.json` |
| 설정 파일 라인 수 | 58 | 58 | 58 |
| 공통 엔진 사용 | 예 | 예 | 예 |
| 쇼핑 기록 분석 모듈 사용 | 예 | 예 | 예 |
| Weather API 사용 | 예 | 예 | 예 |
| 쇼핑 기록 데이터 사용 | 예 | 예 | 예 |
| UI 재사용 | 예 | 예 | 예 |

## 발표에 사용할 수 있는 객관적 문장

```text
현재 세 Agent는 동일한 Python 실행 엔진과 동일한 쇼핑 기록 분석 모듈을 사용합니다.
Agent별 차이는 각각 58줄 규모의 JSON 설정 파일에 정의되어 있습니다.
```

```text
Outfit Agent, Travel Packing Agent, Commute Preparation Agent 모두 Weather API와 shopping_history 데이터를 사용하지만,
추천 규칙과 출력 형식은 서로 다른 config 파일에서 관리됩니다.
```

```text
두 번째 Agent를 추가할 때 핵심은 Python 엔진을 새로 작성하는 것이 아니라,
새로운 JSON 설정 파일을 작성하는 것입니다.
```

## PPT용 표: 현재 구현 기준

| 항목 | 현재 값 |
|---|---:|
| 지원 Agent 수 | 3 |
| 공통 실행 엔진 파일 수 | 1 |
| 쇼핑 기록 분석 모듈 수 | 1 |
| Agent 설정 파일 수 | 3 |
| 모의 쇼핑 기록 사용자 수 | 2 |
| Builder 테스트 수 | 4 |
| 전체 테스트 수 | 6 |

## PPT용 표: 재사용 구조

| 구성 요소 | Outfit Agent | Travel Packing Agent | Commute Agent | 재사용 여부 |
|---|---|---|---|---|
| `engine.py` | 사용 | 사용 | 사용 | 재사용 |
| `shopping.py` | 사용 | 사용 | 사용 | 재사용 |
| `shopping_history.json` | 사용 | 사용 | 사용 | 재사용 |
| Weather API tool | 사용 | 사용 | 사용 | 재사용 |
| Agent config | `outfit_agent.json` | `travel_pack_agent.json` | `commute_agent.json` | Agent별 변경 |
| Output template | 의류 추천 문장 | 여행 준비물 문장 | 통학/출근 준비 문장 | Agent별 변경 |

## 아직 채워야 하는 실험 데이터

아래 값은 파일에서 자동으로 확인할 수 없고, 팀 작업 기록이 필요합니다.

| 항목 | 상태 |
|---|---|
| Outfit Agent 제작 시간 | TBD |
| Travel Packing Agent 제작 시간 | TBD |
| Commute Preparation Agent 제작 시간 | TBD |
| 기존 방식으로 직접 구현했을 때 예상/실제 시간 | TBD |
| 오류 수정 시간 | TBD |
| 회의 제외 실제 작업 시간 | TBD |

## 해석 시 주의점

현재 라인 수는 구현 규모를 보여주는 보조 지표입니다.
Builder 효과를 증명하는 핵심 지표는 라인 수 자체가 아니라,
새 Agent를 만들 때 공통 엔진을 얼마나 재사용했는지와 작업 시간이 얼마나 줄었는지입니다.

따라서 발표에서는 다음 순서로 해석하는 것이 안전합니다.

```text
1. 공통 엔진과 분석 모듈을 만들었다.
2. 세 Agent가 같은 엔진을 사용한다.
3. Agent별 차이는 JSON 설정 파일에 있다.
4. 다음 단계로 실제 작업 시간을 기록해 Builder 효과를 정량화한다.
```

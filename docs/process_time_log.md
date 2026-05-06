# Agent 생성 과정 및 시간 기록

이 문서는 교수님 피드백에 따라, 하나의 Agent를 만드는 과정을 단계별로 나누고
기존 방식과 Builder 방식의 작업량을 비교하기 위한 기록표입니다.

핵심 평가 질문:

> 동일한 수준의 Agent를 만들 때, Builder를 사용하면 기존 방식보다 얼마나 빠르고 적은 수정으로 만들 수 있는가?

## 평가 대상

| 구분 | Agent | 목적 | 구현 방식 |
|---|---|---|---|
| Agent A | Personalized Outfit Agent | 쇼핑 기록 + 날씨 기반 의류 추천 | 실행 엔진 + 설정 + 데이터 구축 |
| Agent B | Travel Packing Agent | 쇼핑 기록 + 날씨 기반 여행 준비물 추천 | 동일 실행 엔진 재사용 + 설정 변경 |
| Agent C | Commute Preparation Agent | 쇼핑 기록 + 날씨 기반 통학/출근 준비 추천 | 동일 실행 엔진 재사용 + 설정 변경 |

## 공통 실행 엔진

세 Agent는 같은 실행 엔진을 사용합니다.

```text
src/agent_builder/engine.py
```

공통 실행 흐름:

```text
Plan -> Act -> Analyze -> Decide -> Compose
```

| 단계 | 역할 |
|---|---|
| Plan | 사용자 입력에서 도시, 날짜, 사용자, Agent 설정을 확정 |
| Act | Weather API와 shopping_history 데이터 소스 실행 |
| Analyze | 쇼핑 기록에서 선호 스타일, 색상, 카테고리 추출 |
| Decide | 날씨와 구매 기록을 기준으로 추천 규칙 적용 |
| Compose | 설정 파일의 output_template로 최종 응답 생성 |

## 기존 방식 작업 단계

Builder 없이 Agent를 직접 구현하면 다음 작업이 필요합니다.

| 단계 | 작업 내용 | 예상 난이도 | 기록할 항목 |
|---|---|---|---|
| 1 | 문제 정의 및 입력 문장 설계 | 중 | 요구사항 정리 시간 |
| 2 | 도시/날짜 파싱 로직 작성 | 중 | 코드 작성 시간, 예외 처리 |
| 3 | Weather API 연동 | 중 | API 호출 코드, 응답 파싱 |
| 4 | 쇼핑 기록 데이터 구조 설계 | 중 | 필드 정의, 예시 데이터 작성 |
| 5 | 쇼핑 기록 분석 로직 작성 | 높음 | 스타일/색상/카테고리 통계 |
| 6 | 추천 규칙 작성 | 높음 | 온도별 규칙, 비/일교차 조건 |
| 7 | 출력 문장 생성 | 중 | 템플릿/문장 포맷 작성 |
| 8 | UI 연결 | 중 | 입력, 실행, 결과 표시 |
| 9 | 테스트 및 디버깅 | 중 | 정상 실행 여부, 사용자별 결과 차이 |

## Builder 방식 작업 단계

Builder 방식에서는 공통 엔진과 도구를 재사용하고, 주로 설정 파일을 작성합니다.

| 단계 | 작업 내용 | 구현 위치 | 기록할 항목 |
|---|---|---|---|
| 1 | Agent 이름과 목적 정의 | `configs/*.json` | 설정 작성 시간 |
| 2 | 사용할 도구 선택 | `tools` 설정 | weather, shopping_history 재사용 여부 |
| 3 | 추천 규칙 작성 | `temperature_rules` | 규칙 개수, 작성 시간 |
| 4 | 추가 조건 작성 | `conditional_extras` | 비, 일교차 등 조건 |
| 5 | 출력 형식 작성 | `output_template` | 문장 수정 시간 |
| 6 | 사용자 데이터 확인 | `data/shopping_history.json` | 기존 데이터 재사용 여부 |
| 7 | 실행 및 trace 확인 | Web Demo / CLI | 정상 작동 확인 시간 |

## 시간 기록표

아래 시간은 발표 전 실제 작업 기록으로 수정해야 합니다. 지금은 기록 형식을 잡기 위한 초안입니다.

### Agent A: Personalized Outfit Agent

| 작업 단계 | 작업 내용 | 수정 파일 | 실제 소요 시간 | 비고 |
|---|---|---|---:|---|
| 문제 정의 | 쇼핑 기록 + 날씨 기반 의류 추천 정의 | 문서/PPT | TBD | 첫 번째 Agent라 범위 정의 필요 |
| 데이터 설계 | 구매 기록 필드 정의 | `data/shopping_history.json` | TBD | item/category/color/style/warmth |
| API 연동 | Weather API 연결 | `weather_agent/tools.py` | TBD | 기존 코드 재사용 가능 |
| 분석 로직 | 쇼핑 기록 분석 모듈 작성 | `src/agent_builder/shopping.py` | TBD | 스타일/색상/카테고리 추출 |
| 실행 엔진 | 공통 흐름 구현 | `src/agent_builder/engine.py` | TBD | Plan-Act-Analyze-Decide-Compose |
| 추천 규칙 | 의류 추천 규칙 작성 | `configs/outfit_agent.json` | TBD | 온도별 규칙 |
| 출력 형식 | 응답 템플릿 작성 | `configs/outfit_agent.json` | TBD | 쇼핑 기록 분석 결과 포함 |
| UI 연결 | Web Demo 연결 | `web_app.py` | TBD | Agent/User 선택 |
| 테스트 | 단위 테스트 및 실행 확인 | `tests/test_agent_builder.py` | TBD | User A/B 결과 차이 |

### Agent B: Travel Packing Agent

| 작업 단계 | 작업 내용 | 수정 파일 | 실제 소요 시간 | 비고 |
|---|---|---|---:|---|
| 문제 정의 | 여행 준비물 추천으로 목적 변경 | 문서/PPT | TBD | 동일한 데이터 구조 사용 |
| 데이터 설계 | 기존 쇼핑 기록 재사용 | 없음 | TBD | 새 데이터 구조 불필요 |
| API 연동 | Weather API 재사용 | 없음 | TBD | 코드 수정 없음 |
| 분석 로직 | 쇼핑 기록 분석 모듈 재사용 | 없음 | TBD | 코드 수정 없음 |
| 실행 엔진 | 공통 엔진 재사용 | 없음 | TBD | 코드 수정 없음 |
| 추천 규칙 | 여행 준비물 규칙 작성 | `configs/travel_pack_agent.json` | TBD | 설정만 변경 |
| 출력 형식 | 여행 준비물 응답 템플릿 작성 | `configs/travel_pack_agent.json` | TBD | 설정만 변경 |
| UI 연결 | 기존 Agent 선택 UI 재사용 | 없음 또는 소폭 수정 | TBD | 선택지만 추가 |
| 테스트 | 실행 확인 | `tests/test_agent_builder.py` | TBD | Agent B 출력 확인 |

### Agent C: Commute Preparation Agent

| 작업 단계 | 작업 내용 | 수정 파일 | 실제 소요 시간 | 비고 |
|---|---|---|---:|---|
| 문제 정의 | 통학/출근 준비 추천으로 목적 변경 | 문서/PPT | TBD | 동일한 데이터 구조 사용 |
| 데이터 설계 | 기존 쇼핑 기록 재사용 | 없음 | TBD | 새 데이터 구조 불필요 |
| API 연동 | Weather API 재사용 | 없음 | TBD | 코드 수정 없음 |
| 분석 로직 | 쇼핑 기록 분석 모듈 재사용 | 없음 | TBD | 코드 수정 없음 |
| 실행 엔진 | 공통 엔진 재사용 | 없음 | TBD | 코드 수정 없음 |
| 추천 규칙 | 통학/출근 준비 규칙 작성 | `configs/commute_agent.json` | TBD | 설정만 변경 |
| 출력 형식 | 통학/출근 준비 응답 템플릿 작성 | `configs/commute_agent.json` | TBD | 설정만 변경 |
| UI 연결 | 기존 Agent 선택 UI 재사용 | 없음 또는 소폭 수정 | TBD | 선택지만 추가 |
| 테스트 | 실행 확인 | `tests/test_agent_builder.py` | TBD | Agent C 출력 확인 |

## 비교 지표

발표에서는 기능 성능보다 Agent 생성 과정의 효율성을 비교합니다.

| 평가 항목 | 기존 직접 구현 방식 | Builder 방식 |
|---|---|---|
| 새 Agent 생성 시 코드 수정량 | 큼 | 작음 |
| 도구/API 재사용 | 직접 구현 필요 | 설정에서 선택 |
| 추천 규칙 수정 | Python 코드 수정 | JSON 규칙 수정 |
| 출력 형식 수정 | Python/HTML 코드 수정 | `output_template` 수정 |
| 실행 흐름 안정성 | 매번 직접 설계 | 고정 흐름 재사용 |
| 테스트 방식 | 직접 확인 | trace로 단계 확인 |

## 발표용 결과 표 초안

실제 시간 기록 후 아래 표를 완성합니다.

| 항목 | Agent A: Outfit | Agent B: Travel | Agent C: Commute | 개선 근거 |
|---|---:|---:|---:|---|
| 수정한 Python 파일 수 | TBD | TBD | TBD | B/C는 engine 재사용 |
| 수정한 config 파일 수 | TBD | TBD | TBD | B/C는 주로 config 변경 |
| 데이터 파일 수정 수 | TBD | TBD | TBD | 기존 shopping_history 재사용 여부 |
| 총 작업 시간 | TBD | TBD | TBD | 두 번째 이후 Agent 생성 시간 감소 |
| 실행 성공 여부 | 성공 | 성공 | 성공 | 동일한 trace 구조 |

## 발표에서 사용할 문장

```text
저희는 완성된 Agent 하나만 평가하지 않고, Agent를 만드는 과정 자체를 평가합니다.
첫 번째 Agent는 실행 엔진과 데이터 구조를 함께 준비해야 했지만,
두 번째와 세 번째 Agent는 동일한 실행 엔진을 재사용하고 설정 파일만 변경하여 구현했습니다.
이를 통해 Builder 방식이 유사한 Agent 생성 시간을 줄일 수 있는지 확인합니다.
```

## 다음 기록해야 할 실제 데이터

1. Outfit Agent 제작에 실제로 걸린 시간
2. Travel Packing Agent 제작에 실제로 걸린 시간
3. Commute Preparation Agent 제작에 실제로 걸린 시간
4. 각 Agent 생성 시 수정한 파일 목록
5. Python 코드 수정 라인 수와 config 수정 라인 수
6. 데모 실행 성공 여부와 오류 수정 시간

## 현재 파일 기준

| 파일 | 역할 |
|---|---|
| `src/agent_builder/engine.py` | 공통 실행 엔진 |
| `src/agent_builder/shopping.py` | 쇼핑 기록 분석 및 보유 단품 선택 |
| `data/shopping_history.json` | 모의 구매 기록 데이터 |
| `configs/outfit_agent.json` | 의류 추천 Agent 설정 |
| `configs/travel_pack_agent.json` | 여행 준비물 Agent 설정 |
| `configs/commute_agent.json` | 통학/출근 준비 Agent 설정 |
| `web_app.py` | Builder Demo UI |
| `tests/test_agent_builder.py` | Builder 동작 테스트 |

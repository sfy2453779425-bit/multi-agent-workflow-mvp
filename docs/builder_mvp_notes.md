# Configuration-driven Agent Builder MVP

## 2026-05 방향 수정

기업 멘토 피드백 이후 현재 방향은 단일 추천 Agent가 아니라
**템플릿 기반 Multi-Agent Workflow Builder MVP**로 정리한다.

핵심 증거:

> JSON 설정으로 여러 Agent를 정의하고, 하나의 Workflow로 순차 실행할 수 있다.

현재 추가된 Workflow:

| Config | Workflow | Agent 구성 |
|---|---|---|
| `configs/outfit_workflow.json` | Outfit Multi-Agent Workflow | Request Parser -> Weather -> Shopping Analysis -> Recommendation -> Compose |

핵심 코드는 `src/agent_builder/workflow.py`이며, 기존 `src/agent_builder/engine.py`의 추천 로직을 재사용한다.

명령줄 실행:

```powershell
python builder_demo.py --workflow
```

웹 Demo 기본 화면도 이 Workflow를 먼저 보여준다.

자세한 범위와 질문지는 `docs/multi_agent_workflow_scope.md`에 정리했다.

---

이번 단계에서 추가한 핵심 증거:

> 같은 실행 엔진을 사용하고, JSON 설정 파일만 바꾸면 다른 Agent처럼 동작한다.

## 실행 방법

웹 Demo:

```bat
open_web_demo.cmd
```

또는:

```bat
run_web.cmd
```

명령줄 Demo:

```bat
run_builder_demo.cmd
```

또는:

```powershell
python builder_demo.py --all
```

## 현재 지원하는 세 Agent

| Config | Agent | 목적 |
|---|---|---|
| `configs/outfit_agent.json` | Personalized Outfit Agent | 날씨 + 쇼핑 기록 분석 기반 옷 추천 |
| `configs/travel_pack_agent.json` | Travel Packing Agent | 날씨 + 쇼핑 기록 분석 기반 여행 준비물 추천 |
| `configs/commute_agent.json` | Commute Preparation Agent | 날씨 + 쇼핑 기록 분석 기반 통학/출근 준비 추천 |

세 Agent는 모두 같은 코드인 `src/agent_builder/engine.py`를 사용합니다.

## Builder MVP로 주장할 수 있는 부분

1. `tools` 설정을 통해 사용할 도구를 지정합니다.
2. `temperature_rules` 설정을 통해 추천 규칙을 바꿉니다.
3. `conditional_extras` 설정을 통해 비, 일교차 같은 조건을 추가합니다.
4. `output_template` 설정을 통해 출력 형식을 바꿉니다.
5. `data/shopping_history.json`의 구매 기록을 분석해 개인화 결과를 생성합니다.

## 발표용 핵심 문장

저희는 완성된 Builder 플랫폼을 만드는 대신, Builder의 핵심 가설을 MVP로 검증했습니다.
동일한 실행 엔진에서 설정 파일만 교체하여 서로 다른 Agent 동작을 만들 수 있음을 보였습니다.

## Demo에서 보여줄 것

1. 웹 Demo 실행
2. `Personalized Outfit Agent` + `User A` 결과 확인
3. 오른쪽 trace에서 `Act`가 `shopping_history`를 실행하고 `Analyze`가 스타일/색상을 추출하는지 확인
4. 같은 Agent에서 `User B`로 바꿔 구매 기록 기반 개인화 결과 비교
5. `Travel Packing Agent`로 바꿔 다른 Agent 동작 확인
6. `Commute Preparation Agent`로 바꿔 세 번째 Agent 동작 확인
7. 세 결과가 같은 `engine.py`에서 나왔다는 점 강조
8. 오른쪽의 `Loaded Config`에서 어떤 JSON 설정이 로드됐는지 확인

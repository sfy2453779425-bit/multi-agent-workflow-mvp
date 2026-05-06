# Multi-Agent Workflow Builder MVP

이 프로젝트는 발표용 MVP입니다. 핵심은 날씨 기능 자체가 아니라,
**템플릿 기반으로 여러 Agent를 구성하고 Workflow로 실행하는 방식**을
보여주는 것입니다.

## 한 줄 정의

완성형 Agent Builder 플랫폼이 아니라, JSON 설정으로 여러 Agent를 정의하고
`Request Parser -> Weather -> Shopping Analysis -> Recommendation -> Compose`
순서로 실행해 하나의 사용자 요청을 처리하는 Multi-Agent Workflow MVP입니다.

## 빠른 실행

Python 3.10 이상을 권장합니다. 외부 패키지는 필요 없습니다.

설정 기반 Builder MVP Demo:

```bat
run_builder_demo.cmd
```

이 명령은 같은 실행 엔진으로 여러 Agent 설정 파일을 순서대로 실행합니다.

```text
configs/outfit_agent.json      -> Personalized Outfit Agent
configs/travel_pack_agent.json -> Travel Packing Agent
configs/commute_agent.json     -> Commute Preparation Agent
```

Multi-Agent Workflow Demo:

```powershell
python builder_demo.py --workflow
```

이 명령은 아래 Workflow를 실행합니다.

```text
configs/outfit_workflow.json
Request Parser Agent -> Weather Agent -> Shopping Analysis Agent -> Recommendation Agent -> Compose Agent
```

핵심 코드는 [src/agent_builder/engine.py](src/agent_builder/engine.py)에 있고,
설정은 [configs](configs) 폴더에 있습니다.

```powershell
python demo.py "서울 내일 날씨 알려주고 옷 추천해줘"
```

현재 PC에서 `python` 명령이 없다면 Windows 명령 프롬프트에서 아래 파일을 실행하세요.

```bat
run_demo.cmd
```

웹 Demo:

```powershell
python web_app.py
```

가장 쉬운 방법은 아래 파일을 더블클릭하는 것입니다.

```text
open_web_demo.cmd
```

이 파일은 로컬 서버를 실행한 뒤 브라우저에서 Demo 페이지를 자동으로 엽니다.
현재 웹 Demo는 Multi-Agent Workflow를 기본 화면으로 보여줍니다. 화면에서 Demo Config와
Shopping History User를 바꿔 실행하면 Workflow trace와 구매 기록 기반 개인화 결과를 확인할 수 있습니다.

또는:

```bat
run_web.cmd
```

브라우저에서 출력된 주소를 열면 됩니다. 기본 주소는 보통
`http://127.0.0.1:8000` 입니다.

발표용 웹 시연 순서:

1. 기본 `의류 추천 Multi-Agent Workflow` 실행
2. 오른쪽 trace에서 5개 Agent가 순서대로 실행되는지 확인
3. `User A`와 `User B`를 바꿔 쇼핑 기록 기반 개인화 결과 비교
4. 단일 Agent 설정으로 바꿔 기존 방식도 같은 코드베이스에서 실행됨을 확인

전통적인 Python baseline:

```powershell
python baseline_traditional.py "서울 내일 날씨 알려주고 옷 추천해줘"
```

또는:

```bat
run_baseline.cmd
```

테스트:

```powershell
python -m unittest discover -s tests
```

또는:

```bat
run_tests.cmd
```

PowerShell에서 `.ps1` 파일을 쓰고 싶다면 실행 정책 때문에 막힐 수 있습니다. 그 경우:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
```

## 프로젝트 구조

```text
.
├── configs/
│   ├── outfit_workflow.json      # Multi-Agent Workflow 설정
│   ├── outfit_agent.json         # 기본 의류 추천 Agent 설정
│   ├── travel_pack_agent.json
│   └── commute_agent.json
├── src/agent_builder/
│   ├── workflow.py               # Multi-Agent Workflow 실행 엔진
│   ├── engine.py                 # 단일 Agent 실행 엔진
│   └── shopping.py               # 쇼핑 기록 분석
├── src/weather_agent/
│   ├── tools.py                  # Open-Meteo API 도구
│   └── models.py
├── builder_demo.py               # CLI Builder/Workflow Demo
├── web_app.py                    # 발표용 웹 Demo
├── baseline_traditional.py
├── tests/
└── docs/
```

## 발표에서 강조할 점

이 Demo는 단순 챗봇이 아닙니다.

1. `Request Parser Agent`: 사용자 입력에서 도시, 날짜, 작업 유형을 추출합니다.
2. `Weather Agent`: 템플릿에 바인딩된 Weather API를 호출합니다.
3. `Shopping Analysis Agent`: 구매 기록에서 스타일과 색상 선호를 분석합니다.
4. `Recommendation Agent`: 날씨와 쇼핑 분석을 규칙에 매칭합니다.
5. `Compose Agent`: 설정된 출력 템플릿으로 최종 답변을 생성합니다.

즉, 같은 유형의 작업은 같은 Workflow로 실행되므로 prompt만 사용하는 방식보다
제어성, 재사용성, 제작 과정 단축을 설명하기 쉽습니다.

## Baseline 비교용 수치

`baseline_traditional.py`는 전통적인 절차형 구현 예시입니다. 현재 예시는
약 140줄이며, 발표에서는 "약 100-150줄"로 말하면 안전합니다.

| 항목 | 전통 구현 | 범용 No-code 도구 | 본 프로젝트 |
|---|---:|---:|---:|
| 코드 작성 | 필요 | 불필요 | 불필요에 가까움 |
| 도구 호출 제어성 | 높음 | 낮음 | 높음 |
| 흐름 안정성 | 높음 | 낮음 | 높음 |
| 구축 시간 | 김 | 짧음 | 가장 짧음 |
| 재사용성 | 낮음 | 중간 | 높음 |

## 사용 API

Open-Meteo의 무료 Geocoding API와 Forecast API를 사용합니다.
API 키가 필요 없습니다.

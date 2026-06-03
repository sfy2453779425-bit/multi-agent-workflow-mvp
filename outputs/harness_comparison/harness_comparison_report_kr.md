# Harness Engineering 대비 실험 결과

## 실험 설계

본 실험은 모델 성능 비교가 아니라 Workflow 구성 방식 비교입니다.
두 방식 모두 같은 로컬 실행 엔진을 사용하고, 차이는 구성 단계에만 둡니다.

- Generic Harness Engineering: Agent, Tool, Context/Memory, Constraints, Feedback Loop, Verification, Execution Environment를 수동 정의
- Builder Workspace: 업무 Preset 선택 후 표준 Workflow JSON을 생성하고 Trace를 출력

## 전체 결과

- 비교 업무 수: 2
- Builder Preset 수: 4
- Generic Harness 평균 구성 접점: 17.0
- Builder Workspace 평균 구성 접점: 3.0
- 평균 감소 접점: 14.0
- 두 방식의 Trace 단계 수 동일 여부: 예

## 업무별 비교

| 업무 | Generic Harness 구성 접점 | Builder Workspace 구성 접점 | 감소 | Generic Trace | Builder Trace | Builder 생성 출처 |
|---|---:|---:|---:|---:|---:|---|
| 발표 기획 업무 | 17 | 3 | 14 | 6 | 6 | BuilderWorkspace |
| 고객 문의 분류 업무 | 17 | 3 | 14 | 6 | 6 | BuilderWorkspace |

## 발표용 결론

Harness Engineering은 Agent 실행 구조를 단순화할 수 있지만, 업무별 Agent, Tool, Context, 제약조건, 검증 규칙은 여전히 직접 정의해야 합니다.

본 프로젝트의 차별점은 Harness를 다시 만드는 것이 아니라, 업무 Workflow를 Template/Preset으로 정의하고 Builder Workspace에서 실행 가능한 Workflow JSON으로 생성한 뒤 여러 도메인에서 동일한 Trace 구조로 검증하는 것입니다.

> Harness는 범용 실행 프레임워크이고, 저희 MVP는 업무 Workflow를 템플릿화하고 생성, 이전, 검증하는 Builder 구조를 구현한 것입니다.

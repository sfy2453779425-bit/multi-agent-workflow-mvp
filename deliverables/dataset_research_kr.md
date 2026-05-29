# Dataset Research for Next MVP

## 목적

현재 MVP는 로컬 mock shopping history를 사용한다. 다음 단계에서는 실제 추천
데이터셋으로 확장 가능성을 검토해야 한다.

## 후보 데이터셋

| 후보 | 데이터 성격 | 장점 | 한계 | 본 프로젝트 활용 |
|---|---|---|---|---|
| H&M Personalized Fashion Recommendations | 고객, 상품, 거래 기반 패션 추천 데이터 | 개인화 추천 연구에 가장 직접적 | 데이터 규모가 크고 전처리 필요 | 다음 학기 추천 성능 검증 후보 |
| Fashion Product Images Small | 상품 이미지 + 카테고리/속성 | 가볍고 시각 자료 만들기 쉬움 | 구매 기록/사용자 행동이 부족 | 상품 메타데이터/스타일 분류 후보 |
| E-commerce Product Images | 상품 이미지 + title/description/category/gender | 상품 설명과 카테고리 분석 가능 | 개인 구매 이력은 부족 | 상품 카탈로그 데이터 후보 |
| Fashion Retail Sales Dataset | 약 3,400개 패션 retail transaction | MVP 규모에 적당하고 구매 분석 가능 | 실제 대형 플랫폼 수준은 아님 | 쇼핑 기록 분석 logic 대체 후보 |
| Multi-category E-commerce Behavior Data | view/cart/purchase 등 이벤트 데이터 | 실제 e-commerce 행동 데이터 구조 | 패션 특화가 아니고 규모가 큼 | 범용 추천 workflow 확장 후보 |

## 이번 학기 적용 판단

이번 학기는 mock shopping history를 유지한다.

이유:

- 목표가 추천 모델 성능이 아니라 Workflow Builder 구조 검증이다.
- 실제 데이터셋 전처리는 시간이 오래 걸린다.
- 발표에서는 mock 데이터라도 Tool Node, Data Node, Recommendation Node의 역할이 명확하면 충분하다.

## 다음 학기 적용 계획

1. H&M 또는 Fashion Retail Sales Dataset을 선택한다.
2. 현재 `data/shopping_history.json` 구조로 변환한다.
3. Builder Template의 Shopping History Analysis Node가 실제 데이터셋을 읽도록 확장한다.
4. 추천 결과를 현재 rule-based ranking과 비교한다.

## 발표용 한 문장

```text
이번 학기에는 Workflow 구조 검증을 위해 mock shopping history를 사용했고,
다음 단계에서는 H&M 패션 추천 데이터셋이나 Fashion Retail Sales Dataset을
현재 Shopping History Analysis Node에 연결할 계획입니다.
```

## 참고 링크

- H&M Personalized Fashion Recommendations: https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations
- Fashion Product Images Small: https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-small
- E-commerce Product Images: https://www.kaggle.com/datasets/vikashrajluhaniwal/fashion-images
- Fashion Retail Sales Dataset: https://www.kaggle.com/datasets/atharvasoundankar/fashion-retail-sales
- Multi-category E-commerce Behavior Data: https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store

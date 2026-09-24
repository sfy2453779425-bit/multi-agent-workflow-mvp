# outfit_02

## Task

다음 주에 칭다오 여행 가는데 비 오는 날 캐주얼 옷 추천해줘

## Context

Language: 한국어
Weather:
- City: 칭다오
- Date: 2026-09-24
- Condition: 비
- Temperature: 12.0–18.0°C
- Precipitation probability: 80%
Supplied inventory:
- A001: 블랙 후드티; style=캐주얼; warmth=medium; rain_ok=True
- A002: 네이비 조거 팬츠; style=스트릿; warmth=medium; rain_ok=True
- A003: 라이트 그레이 바람막이; style=스포티; warmth=light; rain_ok=True
- A004: 블랙 패딩; style=캐주얼; warmth=heavy; rain_ok=False
- A005: 화이트 반팔 티셔츠; style=캐주얼; warmth=light; rain_ok=True
- A006: 블랙 캔버스 스니커즈; style=스트릿; warmth=all; rain_ok=False
Constraints:
- Use only supplied inventory: True
- Rain-safe precipitation threshold: 40%
- Purpose: 여행
- Style: 캐주얼
- Do not invent facts: True

## Response A

날씨 요약

- 날씨: 비
- 기온: 12~18°C
- 강수확률: 80%

추천 아이템 순위

1. 라이트 그레이 바람막이 (A003)
   - 비 오는 날 착용 가능(rain_ok: true)
   - 가벼운 아우터라 12~18°C 날씨에 레이어드하기 좋음

2. 블랙 후드티 (A001)
   - 캐주얼 스타일이며 비 오는 날 착용 가능
   - 중간 보온감이라 바람막이 안에 입기 적합

3. 네이비 조거 팬츠 (A002)
   - 비 오는 날 착용 가능
   - 후드티·바람막이와 함께 편한 여행용 캐주얼 코디 구성 가능

4. 화이트 반팔 티셔츠 (A005)
   - 비 오는 날 착용 가능
   - 기온이 올라가는 낮에는 후드티 안쪽 이너로 활용 가능

추천 조합

화이트 반팔 → 블랙 후드티 → 라이트 그레이 바람막이 + 네이비 조거 팬츠

비가 올 확률이 **80%**이므로, 보유 옷 중 rain_ok: true인 아이템을 우선했습니다.

다만 신발은 비 오는 날에 적합한 보유 아이템이 없습니다. 유일하게 제공된 **블랙 캔버스 스니커즈(A006)**는 rain_ok: false이므로 이번 조건에서는 추천 목록에서 제외합니다. 블랙 패딩(A004) 역시 rain_ok: false이고 보온감이 heavy라 제외했습니다.

## Response B

[Personalized Outfit Agent]
칭다오의 다음 주(2026-09-24) 날씨는 비, 평균 15.0°C, 강수확률 80%입니다.
쇼핑 기록 분석: 총 6개 구매 기록에서 선호 스타일은 캐주얼, 스트릿, 스포티, 선호 색상은 블랙, 네이비, 그레이로 분석되었습니다.
추천 방향: 일교차를 고려한 가벼운 레이어드가 적합합니다.
추천 순위: 1. 라이트 그레이 바람막이 | 2. 블랙 후드티 | 3. 네이비 조거 팬츠
보유 단품 기반 추천: 1. 라이트 그레이 바람막이, 2. 블랙 후드티, 3. 네이비 조거 팬츠
추가 추천: 
추가 조건: 

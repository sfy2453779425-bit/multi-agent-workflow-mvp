TASK
Use the frozen task input below to complete the outfit task.

INPUT
{
  "query": "다음 주에 칭다오 여행 가는데 캐주얼 옷 추천해줘",
  "user_id": "user_a"
}

CONTEXT / DATA
{
  "shared_context": {
    "weather": {
      "city_name": "칭다오",
      "country": "중국",
      "date": "2026-09-23",
      "condition": "흐림",
      "weather_code": 3,
      "temp_min": 10.0,
      "temp_max": 21.0,
      "precipitation_probability": 20,
      "latitude": 36.0671,
      "longitude": 120.3826
    }
  },
  "business_data": {
    "shopping_history": {
      "user_a": [
        {
          "id": "A001",
          "item": "블랙 후드티",
          "category": "top",
          "color": "블랙",
          "style": "캐주얼",
          "warmth": "medium",
          "rain_ok": true,
          "purchased_at": "2026-02-12"
        },
        {
          "id": "A002",
          "item": "네이비 조거 팬츠",
          "category": "bottom",
          "color": "네이비",
          "style": "스트릿",
          "warmth": "medium",
          "rain_ok": true,
          "purchased_at": "2026-02-20"
        },
        {
          "id": "A003",
          "item": "라이트 그레이 바람막이",
          "category": "outer",
          "color": "그레이",
          "style": "스포티",
          "warmth": "light",
          "rain_ok": true,
          "purchased_at": "2026-03-05"
        },
        {
          "id": "A004",
          "item": "블랙 패딩",
          "category": "outer",
          "color": "블랙",
          "style": "캐주얼",
          "warmth": "heavy",
          "rain_ok": false,
          "purchased_at": "2025-12-02"
        },
        {
          "id": "A005",
          "item": "화이트 반팔 티셔츠",
          "category": "top",
          "color": "화이트",
          "style": "캐주얼",
          "warmth": "light",
          "rain_ok": true,
          "purchased_at": "2026-04-02"
        },
        {
          "id": "A006",
          "item": "블랙 캔버스 스니커즈",
          "category": "shoes",
          "color": "블랙",
          "style": "스트릿",
          "warmth": "all",
          "rain_ok": false,
          "purchased_at": "2026-01-18"
        }
      ]
    }
  }
}

CONSTRAINTS
{
  "use_frozen_weather": true,
  "use_only_supplied_inventory": true,
  "purpose": "여행",
  "style": "캐주얼",
  "language": "한국어",
  "do_not_invent_facts": true
}

REQUIRED OUTPUT
{
  "required_fields": [
    "weather",
    "temperature",
    "precipitation",
    "selected_items",
    "reason"
  ],
  "format": "weather summary, ranked owned items, and short reasons"
}

MISSING INFORMATION RULE
Do not invent missing facts, data, policy details, weather, inventory, or model metadata. State what is missing when the supplied information is insufficient.

FIXTURE VERSION: outfit-2026-09-16-v1
FIXTURE SHA256: 3e3b3417dce7482094d73e04368f2c1420c3548bb89e3d3bab0ac46c6b521678

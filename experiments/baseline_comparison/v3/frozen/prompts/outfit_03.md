TASK
Use the frozen task input below to complete the outfit task.

INPUT
{
  "query": "서울 내일 출근 포멀 옷 추천해줘",
  "user_id": "user_b"
}

CONTEXT / DATA
{
  "shared_context": {
    "weather": {
      "city_name": "서울",
      "country": "대한민국",
      "date": "2026-09-24",
      "condition": "흐림",
      "weather_code": 3,
      "temp_min": 6.0,
      "temp_max": 14.0,
      "precipitation_probability": 20,
      "latitude": 37.5665,
      "longitude": 126.978
    }
  },
  "business_data": {
    "shopping_history": {
      "user_b": [
        {
          "id": "B001",
          "item": "네이비 블레이저",
          "category": "outer",
          "color": "네이비",
          "style": "포멀",
          "warmth": "medium",
          "rain_ok": true,
          "purchased_at": "2026-01-12"
        },
        {
          "id": "B002",
          "item": "그레이 슬랙스",
          "category": "bottom",
          "color": "그레이",
          "style": "포멀",
          "warmth": "medium",
          "rain_ok": true,
          "purchased_at": "2026-02-20"
        },
        {
          "id": "B003",
          "item": "화이트 셔츠",
          "category": "top",
          "color": "화이트",
          "style": "포멀",
          "warmth": "light",
          "rain_ok": true,
          "purchased_at": "2026-03-05"
        },
        {
          "id": "B004",
          "item": "블랙 로퍼",
          "category": "shoes",
          "color": "블랙",
          "style": "포멀",
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
  "inventory_only": true,
  "rain_safe_precipitation_min": 40,
  "purpose": "출근",
  "style": "포멀",
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

FIXTURE VERSION: outfit-2026-09-16-v2-commute
FIXTURE SHA256: a169262507936026d7f615f16b1521a237c49e97a846ee42a6d09123de6a3776

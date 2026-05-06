import json
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


CITY_MAP = {
    "서울": "Seoul",
    "seoul": "Seoul",
    "부산": "Busan",
    "busan": "Busan",
    "제주": "Jeju City",
    "jeju": "Jeju City",
}

WEATHER_TEXT = {
    0: "맑음",
    1: "대체로 맑음",
    2: "부분적으로 흐림",
    3: "흐림",
    45: "안개",
    48: "서리 안개",
    51: "약한 이슬비",
    53: "이슬비",
    55: "강한 이슬비",
    61: "약한 비",
    63: "비",
    65: "강한 비",
    71: "약한 눈",
    73: "눈",
    75: "강한 눈",
    80: "약한 소나기",
    81: "소나기",
    82: "강한 소나기",
    95: "뇌우",
}


def parse_city(text):
    lower = text.lower()
    for keyword, city in CITY_MAP.items():
        if keyword in lower:
            return keyword, city
    raise ValueError("도시를 직접 처리해야 합니다.")


def parse_day(text):
    lower = text.lower()
    if "모레" in lower:
        return 2, "모레"
    if "내일" in lower or "tomorrow" in lower:
        return 1, "내일"
    return 0, "오늘"


def get_json(url):
    with urlopen(url, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def find_coordinates(city_query):
    params = urlencode(
        {
            "name": city_query,
            "count": 1,
            "language": "ko",
            "format": "json",
        }
    )
    url = f"https://geocoding-api.open-meteo.com/v1/search?{params}"
    data = get_json(url)
    results = data.get("results") or []
    if not results:
        raise ValueError("좌표 검색 실패")
    return results[0]


def fetch_weather(latitude, longitude, day_offset):
    params = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "daily": (
                "weather_code,temperature_2m_max,"
                "temperature_2m_min,precipitation_probability_max"
            ),
            "timezone": "Asia/Seoul",
            "forecast_days": max(day_offset + 1, 3),
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    return get_json(url)["daily"]


def recommend_clothes(avg_temp, weather_code, precipitation):
    if avg_temp <= 5:
        clothes = "두꺼운 코트나 패딩"
    elif avg_temp <= 16:
        clothes = "자켓이나 가디건"
    elif avg_temp <= 22:
        clothes = "얇은 긴팔과 가벼운 겉옷"
    else:
        clothes = "반팔과 통풍이 잘 되는 옷"

    if precipitation >= 50 or weather_code in {51, 53, 55, 61, 63, 65, 80, 81, 82, 95}:
        return f"{clothes}, 우산"
    return clothes


def build_answer(city_label, date_label, day_offset, daily):
    code = int(daily["weather_code"][day_offset])
    temp_max = float(daily["temperature_2m_max"][day_offset])
    temp_min = float(daily["temperature_2m_min"][day_offset])
    precipitation = daily.get("precipitation_probability_max", [0, 0, 0])[day_offset] or 0
    avg_temp = (temp_min + temp_max) / 2
    condition = WEATHER_TEXT.get(code, f"알 수 없음({code})")
    clothes = recommend_clothes(avg_temp, code, int(precipitation))
    return (
        f"{city_label}의 {date_label} 날씨는 {condition}, "
        f"최저 {temp_min:.1f}°C / 최고 {temp_max:.1f}°C, "
        f"강수확률 {int(precipitation)}%입니다. 옷 추천: {clothes}"
    )


def main():
    text = " ".join(sys.argv[1:]).strip() or "서울 내일 날씨 알려주고 옷 추천해줘"

    city_label, city_query = parse_city(text)
    day_offset, date_label = parse_day(text)
    coordinates = find_coordinates(city_query)
    daily = fetch_weather(coordinates["latitude"], coordinates["longitude"], day_offset)
    answer = build_answer(city_label, date_label, day_offset, daily)

    line_count = len(Path(__file__).read_text(encoding="utf-8").splitlines())
    print("=== Traditional Baseline ===")
    print("manual_steps=9")
    print(f"code_lines={line_count}")
    print("estimated_beginner_time=30-60 minutes")
    print()
    print(answer)


if __name__ == "__main__":
    main()

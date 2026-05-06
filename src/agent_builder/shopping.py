from collections import Counter
from typing import Any


WARMTH_BY_TEMP = [
    ("heavy", None, 8),
    ("medium", 8, 22),
    ("light", 22, None),
]


def analyze_shopping_history(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {
            "total_items": 0,
            "top_styles": [],
            "top_colors": [],
            "top_categories": [],
            "favorite_items": [],
            "items_by_category": {},
        }

    styles = Counter(item.get("style", "") for item in items if item.get("style"))
    colors = Counter(item.get("color", "") for item in items if item.get("color"))
    categories = Counter(item.get("category", "") for item in items if item.get("category"))
    items_by_category: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        items_by_category.setdefault(item.get("category", "other"), []).append(item)

    return {
        "total_items": len(items),
        "top_styles": [name for name, _ in styles.most_common(3)],
        "top_colors": [name for name, _ in colors.most_common(3)],
        "top_categories": [name for name, _ in categories.most_common(3)],
        "favorite_items": [item["item"] for item in items[:3]],
        "items_by_category": items_by_category,
    }


def select_owned_items(
    items: list[dict[str, Any]],
    avg_temp: float,
    precipitation_probability: int,
    target_categories: list[str],
) -> list[str]:
    warmth = _warmth_for_temp(avg_temp)
    selected: list[str] = []
    used_ids: set[str] = set()

    for category in target_categories:
        candidate = _best_item_for_category(
            items,
            category=category,
            warmth=warmth,
            precipitation_probability=precipitation_probability,
            used_ids=used_ids,
        )
        if candidate:
            selected.append(candidate["item"])
            used_ids.add(candidate.get("id", candidate["item"]))

    return selected


def _warmth_for_temp(avg_temp: float) -> str:
    for warmth, min_temp, max_temp in WARMTH_BY_TEMP:
        if min_temp is not None and avg_temp < min_temp:
            continue
        if max_temp is not None and avg_temp > max_temp:
            continue
        return warmth
    return "medium"


def _best_item_for_category(
    items: list[dict[str, Any]],
    category: str,
    warmth: str,
    precipitation_probability: int,
    used_ids: set[str],
) -> dict[str, Any] | None:
    candidates = [
        item
        for item in items
        if item.get("category") == category and item.get("id", item.get("item")) not in used_ids
    ]
    if not candidates:
        return None

    def score(item: dict[str, Any]) -> tuple[int, str]:
        value = 0
        item_warmth = item.get("warmth")
        if item_warmth == warmth:
            value += 3
        if item_warmth == "all":
            value += 2
        if precipitation_probability >= 40 and item.get("rain_ok"):
            value += 1
        return value, item.get("purchased_at", "")

    return max(candidates, key=score)

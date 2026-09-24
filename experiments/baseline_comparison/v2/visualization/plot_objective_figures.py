from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "objective_figure_data.csv"
WHITE = "#FFFFFF"
TEXT = "#111827"
MUTED = "#6B7280"
GRID = "#E5E7EB"
BLUE = "#2F6B9A"
GOLD = "#C58B2A"
GREY = "#6B7280"
RED = "#C44E52"
SKIPPED = "#A7B0BA"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _rows() -> list[dict[str, str]]:
    with DATA_PATH.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _image(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (width, height), WHITE)
    return image, ImageDraw.Draw(image)


def _title(draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> None:
    draw.text((54, 28), title, font=_font(28, True), fill=TEXT)
    draw.text((54, 66), subtitle, font=_font(15), fill=MUTED)


def _label(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, size: int = 14, fill: str = TEXT, bold: bool = False, anchor: str | None = None) -> None:
    draw.text(xy, text, font=_font(size, bold), fill=fill, anchor=anchor)


def _grid(draw: ImageDraw.ImageDraw, left: int, right: int, baseline: int, height: int, maximum: int, step: int) -> None:
    for value in range(0, maximum + 1, step):
        y = baseline - int(height * value / maximum)
        draw.line((left, y, right, y), fill=GRID, width=1)
        _label(draw, (left - 12, y), str(value), 12, MUTED, anchor="rm")


def _bar(draw: ImageDraw.ImageDraw, x: int, baseline: int, width: int, height: int, value: int, maximum: int, color: str) -> tuple[int, int, int, int]:
    top = baseline - int(height * value / maximum)
    box = (x, top, x + width, baseline)
    draw.rectangle(box, fill=color)
    return box


def figure_1(rows: list[dict[str, str]]) -> None:
    image, draw = _image(980, 600)
    _title(draw, "Objective Compliance", "Frozen evaluation-v2 results; denominator = 30 runs")
    metrics = ["Required fields", "Constraint satisfaction", "Completeness"]
    systems = [("ChatGPT", BLUE), ("Builder", GOLD)]
    selected = [row for row in rows if row["figure"] == "Figure 1"]
    left, right, baseline, height, maximum = 125, 910, 475, 315, 34
    _grid(draw, left, right, baseline, height, maximum, 10)
    centers = [260, 515, 770]
    for metric_index, metric in enumerate(metrics):
        center = centers[metric_index]
        for system_index, (system, color) in enumerate(systems):
            row = next(row for row in selected if row["system"] == system and row["metric"] == metric)
            value = int(row["value"])
            denominator = int(row["denominator"])
            bar = _bar(draw, center - 58 + system_index * 62, baseline, 48, height, value, maximum, color)
            _label(draw, ((bar[0] + bar[2]) / 2, bar[1] - 9), f"{value}/{denominator}", 14, TEXT, True, "ms")
        _label(draw, (center, baseline + 24), metric, 14, TEXT, anchor="ma")
    draw.rectangle((650, 28, 666, 44), fill=BLUE)
    _label(draw, (674, 36), "ChatGPT", 13, TEXT, anchor="lm")
    draw.rectangle((760, 28, 776, 44), fill=GOLD)
    _label(draw, (784, 36), "Builder", 13, TEXT, anchor="lm")
    _label(draw, (54, 548), "Counts show passing runs. This is objective compliance, not language quality.", 13, MUTED)
    image.save(ROOT / "figure_1_objective_compliance.png")


def figure_2(rows: list[dict[str, str]]) -> None:
    image, draw = _image(1300, 600)
    _title(draw, "Structured Repeatability by Task Domain", "A case is repeatable when its structured fields match across three runs")
    selected = [row for row in rows if row["figure"] == "Figure 2 summary"]
    domains = ["Customer Support", "Presentation", "Outfit"]
    systems = [("ChatGPT", BLUE), ("Builder", GOLD)]
    left, baseline, height, maximum = 105, 485, 325, 5.8
    _grid(draw, left, 820, baseline, height, 6, 1)
    centers = [240, 455, 670]
    for index, domain in enumerate(domains):
        center = centers[index]
        for system_index, (system, color) in enumerate(systems):
            row = next(row for row in selected if row["system"] == system and row["scope"] == domain)
            value = int(row["value"])
            denominator = int(row["denominator"])
            bar = _bar(draw, center - 47 + system_index * 52, baseline, 40, height, value, 6, color)
            _label(draw, ((bar[0] + bar[2]) / 2, bar[1] - 8), f"{value}/{denominator}", 13, TEXT, True, "ms")
        _label(draw, (center, baseline + 24), domain, 13, TEXT, anchor="ma")
    _label(draw, (190, 155), "By task domain", 17, TEXT, True)
    _label(draw, (970, 155), "Overall", 17, TEXT, True)
    overall_rows = [row for row in selected if row["scope"] == "Overall"]
    for index, (system, color) in enumerate(systems):
        row = next(row for row in overall_rows if row["system"] == system)
        value = int(row["value"])
        denominator = int(row["denominator"])
        bar = _bar(draw, 950 + index * 120, baseline, 70, height, value, 10, color)
        _label(draw, ((bar[0] + bar[2]) / 2, bar[1] - 8), f"{value}/{denominator}", 14, TEXT, True, "ms")
        _label(draw, ((bar[0] + bar[2]) / 2, baseline + 24), system, 13, TEXT, anchor="ma")
    draw.rectangle((520, 112, 536, 128), fill=BLUE)
    _label(draw, (544, 120), "ChatGPT", 13, TEXT, anchor="lm")
    draw.rectangle((620, 112, 636, 128), fill=GOLD)
    _label(draw, (644, 120), "Builder", 13, TEXT, anchor="lm")
    _label(draw, (54, 558), "Repeatability is reported separately from answer quality and does not create an overall score.", 13, MUTED)
    image.save(ROOT / "figure_2_structured_repeatability.png")


def figure_3(rows: list[dict[str, str]]) -> None:
    image, draw = _image(1250, 590)
    _title(draw, "Controlled Failure Localization", "Weather failed; downstream nodes were skipped")
    selected = sorted((row for row in rows if row["figure"] == "Figure 3"), key=lambda row: int(row["sequence"]))
    colors = {"SUCCESS": BLUE, "FAILED": RED, "SKIPPED": SKIPPED}
    y_start = 150
    row_height = 55
    for index, row in enumerate(selected):
        y = y_start + index * row_height
        status = row["status"]
        color = colors[status]
        draw.rounded_rectangle((85, y, 720, y + 36), radius=5, fill=color)
        _label(draw, (105, y + 18), row["category"], 15, WHITE if status != "SKIPPED" else TEXT, True, "lm")
        _label(draw, (760, y + 18), status, 14, TEXT, True, "lm")
    _label(draw, (54, 540), "Direct ChatGPT interaction did not expose an equivalent internal workflow trace in this experiment.", 13, MUTED)
    image.save(ROOT / "figure_3_failure_localization.png")


def _horizontal_panel(draw: ImageDraw.ImageDraw, left: int, top: int, width: int, height: int, title: str, group: list[dict[str, str]], color: str) -> None:
    _label(draw, (left, top - 38), title, 17, TEXT, True)
    labels = [row["metric"] for row in group]
    values = [int(row["value"]) for row in group]
    maximum = max(values) or 1
    row_height = height / len(group)
    label_width = 205
    for index, (label, value) in enumerate(zip(labels, values)):
        y = top + index * row_height + 6
        bar_left = left + label_width
        bar_width = int((width - label_width - 70) * value / maximum)
        _label(draw, (left, y + 14), label, 12, TEXT, anchor="lm")
        draw.rectangle((bar_left, y, bar_left + max(bar_width, 2), y + 28), fill=color)
        _label(draw, (bar_left + max(bar_width, 2) + 8, y + 14), str(value), 12, TEXT, True, "lm")
    draw.line((left + label_width, top - 8, left + label_width, top + height), fill="#CBD5E1", width=1)


def figure_4(rows: list[dict[str, str]]) -> None:
    image, draw = _image(1500, 650)
    _title(draw, "Template-based Configuration Abstraction", "Counts have different meanings. They are not interaction-efficiency measurements.")
    selected = [row for row in rows if row["figure"] == "Figure 4"]
    manual = [row for row in selected if row["scope"] == "Manual"]
    builder = [row for row in selected if row["scope"] == "Template Builder"]
    _horizontal_panel(draw, 65, 155, 610, 300, "Manual JSON editing", manual, GREY)
    _horizontal_panel(draw, 790, 155, 640, 300, "Template Builder", builder, GOLD)
    _label(draw, (65, 535), "Manual: semantic JSON differences and observed logical actions.", 13, MUTED)
    _label(draw, (65, 560), "Template Builder: exposed inputs and generated workflow contract.", 13, MUTED)
    image.save(ROOT / "figure_4_template_configuration_abstraction.png")


def main() -> None:
    rows = _rows()
    figure_1(rows)
    figure_2(rows)
    figure_3(rows)
    figure_4(rows)
    print(f"Generated four objective figures in {ROOT}")


if __name__ == "__main__":
    main()

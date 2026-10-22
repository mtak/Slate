"""Render provider values through an editable JSON layout to a v1 frame."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from PIL import Image, ImageDraw, ImageFont

from frame import HEIGHT, WIDTH, validate_frame

DEFAULT_LAYOUT_PATH = Path(__file__).parent / "layout.json"
FONT_FILES = {
    ("sans", "regular"): "DejaVuSans.ttf",
    ("sans", "bold"): "DejaVuSans-Bold.ttf",
    ("serif", "regular"): "DejaVuSerif.ttf",
    ("serif", "bold"): "DejaVuSerif-Bold.ttf",
    ("mono", "regular"): "DejaVuSansMono.ttf",
    ("mono", "bold"): "DejaVuSansMono-Bold.ttf",
}
FONT_DIRECTORY = Path("/usr/share/fonts/truetype/dejavu")
COLORS = {"black": 0, "white": 1}


class Renderer:
    """Draw text and simple shapes on the 800×480 monochrome canvas."""

    def __init__(self, layout: Mapping):
        if layout.get("width") != WIDTH or layout.get("height") != HEIGHT:
            raise ValueError(f"layout canvas must be {WIDTH}×{HEIGHT}")
        blocks = layout.get("blocks")
        if not isinstance(blocks, list):
            raise ValueError("layout blocks must be a list")
        self.blocks = blocks

    @classmethod
    def from_file(cls, path: str | Path = DEFAULT_LAYOUT_PATH) -> "Renderer":
        with Path(path).open(encoding="utf-8") as layout_file:
            return cls(json.load(layout_file))

    def render(self, data: Mapping[str, object]) -> bytes:
        image = Image.new("1", (WIDTH, HEIGHT), 1)
        draw = ImageDraw.Draw(image)
        for block in self.blocks:
            self._draw_block(draw, block, data)
        return validate_frame(image.tobytes())

    @staticmethod
    def _draw_block(draw: ImageDraw.ImageDraw, block: Mapping, data: Mapping[str, object]) -> None:
        kind = block.get("type")
        x, y = block.get("x", 0), block.get("y", 0)
        if kind == "text":
            key = block.get("key")
            if not isinstance(key, str) or key not in data:
                raise ValueError(f"text block references missing data key: {key!r}")
            size = block.get("size", 24)
            if not isinstance(size, int) or size < 1:
                raise ValueError("text size must be a positive integer")
            font, bold_stroke = Renderer._font(block, size)
            value = str(data[key])
            ink = Renderer._ink(block)
            draw.text((x, y), value, font=font, fill=ink, stroke_width=1 if bold_stroke else 0, stroke_fill=ink)
        elif kind == "wrapped_text":
            key = block.get("key")
            if not isinstance(key, str) or key not in data:
                raise ValueError(f"text block references missing data key: {key!r}")
            size = block.get("size", 24)
            max_width = block.get("max_width")
            max_lines = block.get("max_lines", 3)
            if not isinstance(size, int) or size < 1:
                raise ValueError("text size must be a positive integer")
            if not isinstance(max_width, int) or max_width < 1:
                raise ValueError("wrapped_text max_width must be a positive integer")
            if not isinstance(max_lines, int) or max_lines < 1:
                raise ValueError("wrapped_text max_lines must be a positive integer")
            font, _ = Renderer._font(block, size)
            lines = Renderer._wrap_text(draw, str(data[key]), font, max_width)
            line_height = block.get("line_height", size + 6)
            if not isinstance(line_height, int) or line_height < 1:
                raise ValueError("wrapped_text line_height must be a positive integer")
            if len(lines) > max_lines:
                lines = lines[:max_lines]
                lines[-1] = Renderer._truncate_text(draw, lines[-1] + " ...", font, max_width)
            for index, line in enumerate(lines):
                draw.text((x, y + index * line_height), line, font=font, fill=Renderer._ink(block))
        elif kind == "line":
            draw.line((x, y, block["x2"], block["y2"]), fill=Renderer._ink(block), width=block.get("width", 2))
        elif kind == "rectangle":
            bounds = (x, y, x + block["width"], y + block["height"])
            Renderer._draw_rectangle(draw, bounds, block)
        elif kind == "calendar":
            Renderer._draw_calendar(draw, block, data, x, y)
        elif kind == "power":
            Renderer._draw_power(draw, block, data, x, y)
        elif kind == "forecast_hours":
            Renderer._draw_forecast_hours(draw, block, data, x, y)
        elif kind == "forecast_days":
            Renderer._draw_forecast_days(draw, block, data, x, y)
        elif kind == "events":
            events = data.get(block.get("key", "events"), [])
            if not isinstance(events, list):
                raise ValueError("events block data must be a list")
            count = block.get("count", 6)
            row_height = block.get("row_height", 48)
            if not isinstance(count, int) or count < 1 or not isinstance(row_height, int) or row_height < 1:
                raise ValueError("events count and row_height must be positive integers")
            title_font, _ = Renderer._font(block, Renderer._positive_int(block, "title_size", 24))
            detail_font, _ = Renderer._font(block, Renderer._positive_int(block, "detail_size", 18))
            max_width = block.get("max_width")
            if max_width is not None and (not isinstance(max_width, int) or max_width < 1):
                raise ValueError("events max_width must be a positive integer")
            for index, event in enumerate(events[:count]):
                row_y = y + index * row_height
                title = str(event.get("title", "(Untitled event)"))
                details = " · ".join(str(event.get(field, "")) for field in ("date", "time") if event.get(field))
                if max_width is not None:
                    title = Renderer._truncate_text(draw, title, title_font, max_width)
                    details = Renderer._truncate_text(draw, details, detail_font, max_width)
                draw.text((x, row_y), title, font=title_font, fill=Renderer._ink(block))
                draw.text((x, row_y + title_font.size + 2), details, font=detail_font, fill=Renderer._ink(block))
        else:
            raise ValueError(f"unsupported layout block type: {kind!r}")

    @staticmethod
    def _draw_calendar(draw: ImageDraw.ImageDraw, block: Mapping, data: Mapping[str, object], x: int, y: int) -> None:
        width, height = block.get("width", 120), block.get("height", 140)
        if not isinstance(width, int) or width < 40 or not isinstance(height, int) or height < 60:
            raise ValueError("calendar width must be at least 40 and height at least 60")
        stroke = Renderer._positive_int(block, "stroke", 2)
        ink = Renderer._ink(block)
        Renderer._draw_rectangle(draw, (x, y, x + width, y + height), block, stroke)
        weekday = Renderer._calendar_value(block, data, "weekday_key", "weekday")
        day = Renderer._calendar_value(block, data, "day_key", "day")
        month = Renderer._calendar_value(block, data, "month_key", "month")
        weekday_font, _ = Renderer._font(block, Renderer._positive_int(block, "weekday_size", 16))
        day_font, _ = Renderer._font(block, Renderer._positive_int(block, "day_size", 48))
        month_font, _ = Renderer._font(block, Renderer._positive_int(block, "month_size", 20))
        header_height = max(weekday_font.getbbox(weekday)[3] + 10, 30)
        divider = block.get("divider", True)
        if not isinstance(divider, bool):
            raise ValueError("calendar divider must be a boolean")
        if divider:
            draw.line((x, y + header_height, x + width, y + header_height), fill=ink, width=stroke)
        Renderer._draw_centered_text(draw, weekday, weekday_font, x, y + 4, width, ink)
        Renderer._draw_centered_text(draw, day, day_font, x, y + header_height + 2, width, ink)
        Renderer._draw_centered_text(draw, month, month_font, x, y + height - month_font.getbbox(month)[3] - 8, width, ink)

    @staticmethod
    def _calendar_value(block: Mapping, data: Mapping[str, object], key_option: str, default_key: str) -> str:
        key = block.get(key_option, default_key)
        if not isinstance(key, str) or key not in data:
            raise ValueError(f"calendar block references missing data key: {key!r}")
        return str(data[key])

    @staticmethod
    def _draw_centered_text(draw: ImageDraw.ImageDraw, value: str, font: ImageFont.ImageFont, x: int, y: int, width: int, ink: int = 0) -> None:
        bounds = draw.textbbox((0, 0), value, font=font)
        text_width = bounds[2] - bounds[0]
        draw.text((x + (width - text_width) // 2, y), value, font=font, fill=ink)

    @staticmethod
    def _draw_power(draw: ImageDraw.ImageDraw, block: Mapping, data: Mapping[str, object], x: int, y: int) -> None:
        width, height = block.get("width", 120), block.get("height", 92)
        if not isinstance(width, int) or width < 80 or not isinstance(height, int) or height < 60:
            raise ValueError("power widget width must be at least 80 and height at least 60")
        label = block.get("label", "Power")
        if not isinstance(label, str):
            raise ValueError("power widget label must be a string")
        value = data.get(block.get("key", "power_watts"))
        stroke = Renderer._positive_int(block, "stroke", 2)
        ink = Renderer._ink(block)
        Renderer._draw_rectangle(draw, (x, y, x + width, y + height), block, stroke)
        label_font, _ = Renderer._font(block, Renderer._positive_int(block, "label_size", 16))
        value_font, _ = Renderer._font(block, Renderer._positive_int(block, "value_size", 20))
        divider = block.get("divider", False)
        if not isinstance(divider, bool):
            raise ValueError("power divider must be a boolean")
        if divider:
            draw.line((x + 8, y + 34, x + width - 8, y + 34), fill=ink, width=stroke)
        Renderer._draw_centered_text(draw, label, label_font, x, y + 8, width, ink)
        reading = f"{value:,} W" if isinstance(value, int) and not isinstance(value, bool) else "Unavailable"
        Renderer._draw_centered_text(draw, reading, value_font, x, y + 42, width, ink)

    @staticmethod
    def _draw_forecast_hours(draw: ImageDraw.ImageDraw, block: Mapping, data: Mapping[str, object], x: int, y: int) -> None:
        width, height = block.get("width", 330), block.get("height", 168)
        if not isinstance(width, int) or width < 180 or not isinstance(height, int) or height < 48:
            raise ValueError("forecast widget width must be at least 180 and height at least 48")
        key = block.get("key", "precipitation_forecast")
        forecast = data.get(key)
        ink = Renderer._ink(block)
        normal_block = dict(block)
        normal_block["bold"] = False
        normal_block["font_weight"] = "regular"
        amount_font, _ = Renderer._font(normal_block, Renderer._positive_int(block, "amount_size", 14))
        time_font, _ = Renderer._font(normal_block, Renderer._positive_int(block, "time_size", 14))
        chance_block = dict(block)
        chance_block["bold"] = True
        chance_block["font_weight"] = "bold"
        chance_font, _ = Renderer._font(chance_block, Renderer._positive_int(block, "chance_size", 22))
        show_attribution = block.get("show_attribution", True)
        if not isinstance(show_attribution, bool):
            raise ValueError("forecast widget show_attribution must be a boolean")
        if show_attribution:
            attribution_font, _ = Renderer._font(
                normal_block, Renderer._positive_int(block, "attribution_size", 8)
            )
            attribution = "Open-Meteo"
            attribution_width = draw.textlength(attribution, font=attribution_font)
            draw.text((x + width - attribution_width, y - 11), attribution,
                      font=attribution_font, fill=ink)
        draw.rectangle((x, y, x + width, y + height), outline=ink, width=1)

        if not isinstance(forecast, list) or not forecast:
            unavailable_font, _ = Renderer._font(block, Renderer._positive_int(block, "unavailable_size", 18))
            Renderer._draw_centered_text(draw, "Forecast unavailable", unavailable_font,
                                         x, y + (height - 24) // 2, width, ink)
            return

        count = min(len(forecast), max(1, width // 64))
        cell_width = width / count
        for index, entry in enumerate(forecast[:count]):
            if not isinstance(entry, Mapping) or not isinstance(entry.get("hour"), str):
                raise ValueError("forecast widget entries must include an hour")
            probability, amount = entry.get("probability"), entry.get("amount")
            probability_text = "—" if probability is None else f"{round(float(probability))}%"
            amount_text = "—" if amount is None else f"{float(amount):.1f} mm"
            cell_x = x + index * cell_width
            if index:
                draw.line((round(cell_x), y, round(cell_x), y + height), fill=ink, width=1)
            Renderer._draw_centered_text(draw, amount_text, amount_font, round(cell_x), y + 12,
                                         round(cell_width), ink)
            chance_y = y + (height - Renderer._positive_int(block, "chance_size", 22)) // 2 - 2
            Renderer._draw_centered_text(draw, probability_text, chance_font, round(cell_x), chance_y,
                                         round(cell_width), ink)
            Renderer._draw_centered_text(draw, entry["hour"], time_font, round(cell_x), y + height - 30,
                                         round(cell_width), ink)

    @staticmethod
    def _draw_forecast_days(draw: ImageDraw.ImageDraw, block: Mapping, data: Mapping[str, object], x: int, y: int) -> None:
        width, height = block.get("width", 352), block.get("height", 52)
        if not isinstance(width, int) or width < 180 or not isinstance(height, int) or height < 48:
            raise ValueError("daily forecast widget width must be at least 180 and height at least 48")
        forecast = data.get(block.get("key", "precipitation_daily_forecast"))
        ink = Renderer._ink(block)
        draw.rectangle((x, y, x + width, y + height), outline=ink, width=1)
        if not isinstance(forecast, list) or not forecast:
            unavailable_font, _ = Renderer._font(block, 14)
            Renderer._draw_centered_text(draw, "Forecast unavailable", unavailable_font, x, y + 10, width, ink)
            return
        columns = block.get("columns", max(1, width // 64))
        if not isinstance(columns, int) or columns < 1:
            raise ValueError("daily forecast columns must be a positive integer")
        count = min(len(forecast), columns)
        cell_width = width / count
        for index, entry in enumerate(forecast[:count]):
            if not isinstance(entry, Mapping) or not isinstance(entry.get("day"), str):
                raise ValueError("daily forecast entries must include a day")
            probability, amount = entry.get("probability"), entry.get("amount")
            label = "—" if amount is None else f"{float(amount):.1f}mm"
            chance = "—" if probability is None else f"{round(float(probability))}%"
            cell_x = round(x + index * cell_width)
            cell_size = round(cell_width)
            if index:
                draw.line((cell_x, y, cell_x, y + height), fill=ink, width=1)
            day_font, _ = Renderer._font(block, Renderer._positive_int(block, "day_size", 12))
            amount_font, _ = Renderer._font(block, Renderer._positive_int(block, "amount_size", 12))
            Renderer._draw_centered_text(draw, entry["day"], day_font, cell_x, y + 2, cell_size, ink)
            Renderer._draw_centered_text(draw, label, amount_font, cell_x, y + 23, cell_size, ink)
            Renderer._draw_centered_text(draw, chance, amount_font, cell_x, y + 43, cell_size, ink)

    @staticmethod
    def _truncate_text(draw: ImageDraw.ImageDraw, value: str, font: ImageFont.ImageFont, max_width: int) -> str:
        if draw.textlength(value, font=font) <= max_width:
            return value
        ellipsis = "..."
        if draw.textlength(ellipsis, font=font) > max_width:
            return ""
        low, high = 0, len(value)
        while low < high:
            middle = (low + high + 1) // 2
            if draw.textlength(value[:middle] + ellipsis, font=font) <= max_width:
                low = middle
            else:
                high = middle - 1
        return value[:low] + ellipsis

    @staticmethod
    def _wrap_text(draw: ImageDraw.ImageDraw, value: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
        lines: list[str] = []
        current = ""
        for word in value.split():
            candidate = f"{current} {word}" if current else word
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = Renderer._truncate_text(draw, word, font, max_width)
        if current:
            lines.append(current)
        return lines or [""]

    @staticmethod
    def _font(block: Mapping, size: int) -> tuple[ImageFont.ImageFont, bool]:
        if not isinstance(size, int) or isinstance(size, bool) or size < 1 or size > 256:
            raise ValueError("font size must be an integer from 1 to 256")
        family = block.get("font_family", "default")
        weight = block.get("font_weight")
        legacy_bold = block.get("bold", False)
        if family not in ("default", "sans", "serif", "mono"):
            raise ValueError("font_family must be default, sans, serif, or mono")
        if not isinstance(legacy_bold, bool):
            raise ValueError("text bold must be a boolean")
        if weight is None:
            weight = "bold" if legacy_bold else "regular"
        if weight not in ("regular", "bold"):
            raise ValueError("font_weight must be regular or bold")
        if family == "default":
            return ImageFont.load_default(size=size), weight == "bold"
        font_path = FONT_DIRECTORY / FONT_FILES[(family, weight)]
        try:
            return ImageFont.truetype(str(font_path), size=size), False
        except OSError as error:
            raise ValueError(f"font file is unavailable: {font_path}") from error

    @staticmethod
    def _color(block: Mapping, field: str, default: str, allow_none: bool = False) -> int | None:
        value = block.get(field, default)
        if allow_none and value == "none":
            return None
        if not isinstance(value, str) or value not in COLORS:
            options = "black, white, or none" if allow_none else "black or white"
            raise ValueError(f"{field} must be {options}")
        return COLORS[value]

    @staticmethod
    def _ink(block: Mapping) -> int:
        value = Renderer._color(block, "ink", "black")
        assert value is not None
        return value

    @staticmethod
    def _fill(block: Mapping) -> int | None:
        return Renderer._color(block, "fill", "none", allow_none=True)

    @staticmethod
    def _positive_int(block: Mapping, field: str, default: int) -> int:
        value = block.get(field, default)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > 256:
            raise ValueError(f"{field} must be an integer from 1 to 256")
        return value

    @staticmethod
    def _draw_rectangle(draw: ImageDraw.ImageDraw, bounds: tuple[int, int, int, int],
                        block: Mapping, stroke: int | None = None) -> None:
        fill = Renderer._fill(block)
        outline = Renderer._color(block, "outline", "black", allow_none=True)
        options: dict[str, int] = {}
        if fill is not None:
            options["fill"] = fill
        if outline is not None:
            options["outline"] = outline
            options["width"] = stroke or Renderer._positive_int(block, "stroke", 2)
        if options:
            draw.rectangle(bounds, **options)

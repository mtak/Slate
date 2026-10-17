"""Render provider values through an editable JSON layout to a v1 frame."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from PIL import Image, ImageDraw, ImageFont

from frame import HEIGHT, WIDTH, validate_frame

DEFAULT_LAYOUT_PATH = Path(__file__).parent / "layout.json"


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
            font = ImageFont.load_default(size=size)
            value = str(data[key])
            draw.text((x, y), value, font=font, fill=0)
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
            font = ImageFont.load_default(size=size)
            lines = Renderer._wrap_text(draw, str(data[key]), font, max_width)
            line_height = block.get("line_height", size + 6)
            if not isinstance(line_height, int) or line_height < 1:
                raise ValueError("wrapped_text line_height must be a positive integer")
            if len(lines) > max_lines:
                lines = lines[:max_lines]
                lines[-1] = Renderer._truncate_text(draw, lines[-1] + " ...", font, max_width)
            for index, line in enumerate(lines):
                draw.text((x, y + index * line_height), line, font=font, fill=0)
        elif kind == "line":
            draw.line((x, y, block["x2"], block["y2"]), fill=0, width=block.get("width", 2))
        elif kind == "rectangle":
            bounds = (x, y, x + block["width"], y + block["height"])
            draw.rectangle(bounds, outline=0, width=block.get("stroke", 2))
        elif kind == "calendar":
            Renderer._draw_calendar(draw, block, data, x, y)
        elif kind == "events":
            events = data.get(block.get("key", "events"), [])
            if not isinstance(events, list):
                raise ValueError("events block data must be a list")
            count = block.get("count", 6)
            row_height = block.get("row_height", 48)
            if not isinstance(count, int) or count < 1 or not isinstance(row_height, int) or row_height < 1:
                raise ValueError("events count and row_height must be positive integers")
            title_font = ImageFont.load_default(size=block.get("title_size", 24))
            detail_font = ImageFont.load_default(size=block.get("detail_size", 18))
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
                draw.text((x, row_y), title, font=title_font, fill=0)
                draw.text((x, row_y + title_font.size + 2), details, font=detail_font, fill=0)
        else:
            raise ValueError(f"unsupported layout block type: {kind!r}")

    @staticmethod
    def _draw_calendar(draw: ImageDraw.ImageDraw, block: Mapping, data: Mapping[str, object], x: int, y: int) -> None:
        width, height = block.get("width", 120), block.get("height", 140)
        if not isinstance(width, int) or width < 40 or not isinstance(height, int) or height < 60:
            raise ValueError("calendar width must be at least 40 and height at least 60")
        stroke = block.get("stroke", 2)
        draw.rectangle((x, y, x + width, y + height), outline=0, width=stroke)
        weekday = Renderer._calendar_value(block, data, "weekday_key", "weekday")
        day = Renderer._calendar_value(block, data, "day_key", "day")
        month = Renderer._calendar_value(block, data, "month_key", "month")
        weekday_font = ImageFont.load_default(size=block.get("weekday_size", 16))
        day_font = ImageFont.load_default(size=block.get("day_size", 48))
        month_font = ImageFont.load_default(size=block.get("month_size", 20))
        header_height = max(weekday_font.getbbox(weekday)[3] + 10, 30)
        draw.line((x, y + header_height, x + width, y + header_height), fill=0, width=stroke)
        Renderer._draw_centered_text(draw, weekday, weekday_font, x, y + 4, width)
        Renderer._draw_centered_text(draw, day, day_font, x, y + header_height + 2, width)
        Renderer._draw_centered_text(draw, month, month_font, x, y + height - month_font.getbbox(month)[3] - 8, width)

    @staticmethod
    def _calendar_value(block: Mapping, data: Mapping[str, object], key_option: str, default_key: str) -> str:
        key = block.get(key_option, default_key)
        if not isinstance(key, str) or key not in data:
            raise ValueError(f"calendar block references missing data key: {key!r}")
        return str(data[key])

    @staticmethod
    def _draw_centered_text(draw: ImageDraw.ImageDraw, value: str, font: ImageFont.ImageFont, x: int, y: int, width: int) -> None:
        bounds = draw.textbbox((0, 0), value, font=font)
        text_width = bounds[2] - bounds[0]
        draw.text((x + (width - text_width) // 2, y), value, font=font, fill=0)

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

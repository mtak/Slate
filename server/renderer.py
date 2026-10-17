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
        elif kind == "line":
            draw.line((x, y, block["x2"], block["y2"]), fill=0, width=block.get("width", 2))
        elif kind == "rectangle":
            bounds = (x, y, x + block["width"], y + block["height"])
            draw.rectangle(bounds, outline=0, width=block.get("stroke", 2))
        elif kind == "calendar":
            Renderer._draw_calendar(draw, block, data, x, y)
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

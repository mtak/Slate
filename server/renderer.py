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
            for index, event in enumerate(events[:count]):
                row_y = y + index * row_height
                title = str(event.get("title", "(Untitled event)"))
                details = " · ".join(str(event.get(field, "")) for field in ("date", "time") if event.get(field))
                draw.text((x, row_y), title, font=title_font, fill=0)
                draw.text((x, row_y + title_font.size + 2), details, font=detail_font, fill=0)
        else:
            raise ValueError(f"unsupported layout block type: {kind!r}")

"""Slate version 1 monochrome frame contract."""

from __future__ import annotations

WIDTH = 800
HEIGHT = 480
BYTES_PER_ROW = WIDTH // 8
FRAME_SIZE = BYTES_PER_ROW * HEIGHT
CONTENT_TYPE = "application/vnd.slate.frame"


def validate_frame(frame: bytes) -> bytes:
    """Return a frame unchanged, rejecting anything outside the v1 contract."""
    if not isinstance(frame, bytes):
        raise TypeError("frame must be bytes")
    if len(frame) != FRAME_SIZE:
        raise ValueError(f"frame must contain exactly {FRAME_SIZE} bytes")
    return frame


def pixel_is_black(frame: bytes, x: int, y: int) -> bool:
    """Read one pixel from a validated v1 frame."""
    validate_frame(frame)
    if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
        raise ValueError("pixel coordinates are outside the frame")
    offset = y * BYTES_PER_ROW + x // 8
    mask = 0x80 >> (x & 7)
    return (frame[offset] & mask) == 0


def sample_frame() -> bytes:
    """Build a visible asymmetric orientation test pattern in a white frame."""
    frame = bytearray([0xFF]) * FRAME_SIZE

    def black_rect(x: int, y: int, width: int, height: int) -> None:
        for row in range(y, y + height):
            for column in range(x, x + width):
                offset = row * BYTES_PER_ROW + column // 8
                frame[offset] &= ~(0x80 >> (column & 7))

    # Large corner marks plus an offset L make rotation and mirroring obvious.
    corners = ((16, 16), (WIDTH - 48, 16), (16, HEIGHT - 48),
               (WIDTH - 48, HEIGHT - 48))
    for x, y in corners:
        black_rect(x, y, 32, 32)
    black_rect(80, 80, 160, 12)
    black_rect(80, 80, 12, 160)
    return bytes(frame)

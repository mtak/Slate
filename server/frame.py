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
    """Build a small asymmetric orientation test pattern in a white frame."""
    frame = bytearray([0xFF]) * FRAME_SIZE
    # Distinct marks at all four corners, plus a black top-left to anchor origin.
    corners = ((0, 0), (WIDTH - 1, 0), (0, HEIGHT - 1), (WIDTH - 1, HEIGHT - 1))
    for x, y in corners:
        offset = y * BYTES_PER_ROW + x // 8
        frame[offset] &= ~(0x80 >> (x & 7))
    # Add an L near the upper-left so the preview makes row and bit direction clear.
    for x in range(1, 25):
        offset = x // 8
        frame[offset] &= ~(0x80 >> (x & 7))
    for y in range(1, 25):
        offset = y * BYTES_PER_ROW
        frame[offset] &= 0x7F
    return bytes(frame)

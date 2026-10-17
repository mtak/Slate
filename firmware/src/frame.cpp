#include "frame.h"

#include <string.h>

namespace slate {
namespace {
struct Glyph {
  char character;
  uint8_t rows[7];
};

const Glyph kFont[] = {
    {'A', {14, 17, 17, 31, 17, 17, 17}},
    {'B', {30, 17, 17, 30, 17, 17, 30}},
    {'C', {14, 17, 16, 16, 16, 17, 14}},
    {'D', {30, 17, 17, 17, 17, 17, 30}},
    {'E', {31, 16, 16, 30, 16, 16, 31}},
    {'H', {17, 17, 17, 31, 17, 17, 17}},
    {'I', {14, 4, 4, 4, 4, 4, 14}},
    {'K', {17, 18, 20, 24, 20, 18, 17}},
    {'L', {16, 16, 16, 16, 16, 16, 31}},
    {'N', {17, 25, 25, 21, 19, 19, 17}},
    {'O', {14, 17, 17, 17, 17, 17, 14}},
    {'P', {30, 17, 17, 30, 16, 16, 16}},
    {'S', {15, 16, 16, 14, 1, 1, 30}},
    {'T', {31, 4, 4, 4, 4, 4, 4}},
    {'V', {17, 17, 17, 17, 17, 10, 4}},
    {'W', {17, 17, 17, 21, 21, 21, 10}},
    {'2', {30, 1, 1, 6, 8, 16, 31}},
};

const Glyph *findGlyph(char character) {
  for (const Glyph &glyph : kFont) {
    if (glyph.character == character) {
      return &glyph;
    }
  }
  return nullptr;
}

void drawRect(uint8_t *frame, uint16_t x, uint16_t y, uint16_t width,
              uint16_t height, bool black) {
  if (width == 0 || height == 0) return;
  fillRect(frame, x, y, width, 1, black);
  if (height > 1) fillRect(frame, x, y + height - 1, width, 1, black);
  if (height > 2) {
    fillRect(frame, x, y + 1, 1, height - 2, black);
    if (width > 1) fillRect(frame, x + width - 1, y + 1, 1, height - 2, black);
  }
}

void drawText(uint8_t *frame, uint16_t x, uint16_t y, const char *text,
              uint8_t scale, bool black) {
  for (; *text != '\0'; ++text) {
    const Glyph *glyph = findGlyph(*text);
    if (glyph != nullptr) {
      for (uint8_t row = 0; row < 7; ++row) {
        for (uint8_t column = 0; column < 5; ++column) {
          if (glyph->rows[row] & (1 << (4 - column))) {
            fillRect(frame, x + column * scale, y + row * scale, scale, scale,
                     black);
          }
        }
      }
    }
    x += 6 * scale;
  }
}
}  // namespace

void clearFrame(uint8_t *frame) { memset(frame, 0xFF, kFrameSize); }

void setPixel(uint8_t *frame, uint16_t x, uint16_t y, bool black) {
  if (x >= kDisplayWidth || y >= kDisplayHeight) return;
  const size_t index = static_cast<size_t>(y) * kBytesPerRow + (x / 8);
  const uint8_t mask = 0x80 >> (x & 7);
  if (black) {
    frame[index] &= static_cast<uint8_t>(~mask);
  } else {
    frame[index] |= mask;
  }
}

void fillRect(uint8_t *frame, uint16_t x, uint16_t y, uint16_t width,
              uint16_t height, bool black) {
  const uint32_t right = static_cast<uint32_t>(x) + width;
  const uint32_t bottom = static_cast<uint32_t>(y) + height;
  for (uint32_t row = y; row < bottom && row < kDisplayHeight; ++row) {
    for (uint32_t column = x; column < right && column < kDisplayWidth;
         ++column) {
      setPixel(frame, column, row, black);
    }
  }
}

void drawDiagnosticFrame(uint8_t *frame, bool oldProfile) {
  clearFrame(frame);
  drawRect(frame, 8, 8, 784, 464, true);
  drawText(frame, 40, 34, "SLATE TEST", 5, true);
  drawText(frame, 42, 95, oldProfile ? "V2 OLD" : "V2 NEW", 4, true);

  drawRect(frame, 40, 155, 330, 122, true);
  fillRect(frame, 44, 159, 322, 114, true);
  drawText(frame, 85, 195, "WHITE", 4, false);
  drawRect(frame, 430, 155, 330, 122, true);
  drawText(frame, 475, 195, "BLACK", 4, true);

  drawRect(frame, 40, 310, 720, 130, true);
  for (uint16_t y = 318; y < 432; y += 16) {
    for (uint16_t x = 48; x < 752; x += 16) {
      if (((x / 16) + (y / 16)) & 1) fillRect(frame, x, y, 8, 8, true);
    }
  }

  fillRect(frame, 18, 18, 20, 20, true);
  fillRect(frame, 762, 18, 20, 20, true);
  fillRect(frame, 18, 442, 20, 20, true);
  fillRect(frame, 762, 442, 20, 20, true);
}

}  // namespace slate

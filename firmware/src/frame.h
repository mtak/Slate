#pragma once

#include <stddef.h>
#include <stdint.h>

namespace slate {

constexpr uint16_t kDisplayWidth = 800;
constexpr uint16_t kDisplayHeight = 480;
constexpr uint16_t kBytesPerRow = kDisplayWidth / 8;
constexpr size_t kFrameSize = kBytesPerRow * kDisplayHeight;

void clearFrame(uint8_t *frame);
void setPixel(uint8_t *frame, uint16_t x, uint16_t y, bool black);
void fillRect(uint8_t *frame, uint16_t x, uint16_t y, uint16_t width,
              uint16_t height, bool black);
void drawDiagnosticFrame(uint8_t *frame, bool oldProfile);

}  // namespace slate

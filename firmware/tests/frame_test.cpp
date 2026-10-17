#include "frame.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

namespace {
void expect(bool condition, const char *message) {
  if (!condition) {
    fprintf(stderr, "FAIL: %s\n", message);
    exit(1);
  }
}

bool isBlack(const uint8_t *frame, uint16_t x, uint16_t y) {
  const size_t index = static_cast<size_t>(y) * slate::kBytesPerRow + x / 8;
  return (frame[index] & (0x80 >> (x & 7))) == 0;
}

void testFrameContractAndPixelPacking() {
  expect(slate::kDisplayWidth == 800, "display width is 800 pixels");
  expect(slate::kDisplayHeight == 480, "display height is 480 pixels");
  expect(slate::kFrameSize == 48000, "frame contains 48,000 bytes");

  uint8_t frame[slate::kFrameSize];
  memset(frame, 0, sizeof(frame));
  slate::clearFrame(frame);
  expect(frame[0] == 0xFF && frame[slate::kFrameSize - 1] == 0xFF,
         "clear frame sets white pixels");

  slate::setPixel(frame, 0, 0, true);
  slate::setPixel(frame, 7, 0, true);
  slate::setPixel(frame, 8, 0, true);
  expect(frame[0] == 0x7E && frame[1] == 0x7F,
         "pixels are packed left to right, most significant bit first");
  slate::setPixel(frame, 0, 0, false);
  expect(frame[0] == 0xFE, "setting a pixel white preserves its neighbors");
}

void testClippingAndRectangleFill() {
  uint8_t frame[slate::kFrameSize];
  slate::clearFrame(frame);
  slate::fillRect(frame, 798, 478, 10, 10, true);
  expect(isBlack(frame, 798, 478) && isBlack(frame, 799, 479),
         "rectangle includes its visible bottom right pixels");
  expect(!isBlack(frame, 797, 478) && !isBlack(frame, 798, 477),
         "rectangle does not spill outside its bounds");

  slate::clearFrame(frame);
  slate::setPixel(frame, 800, 479, true);
  slate::setPixel(frame, 799, 480, true);
  expect(!isBlack(frame, 799, 479), "out of bounds pixels are ignored");
}

void testDiagnosticFrameIsDeterministicAndDistinguishesProfiles() {
  uint8_t first[slate::kFrameSize];
  uint8_t second[slate::kFrameSize];
  uint8_t oldProfile[slate::kFrameSize];
  slate::drawDiagnosticFrame(first, false);
  slate::drawDiagnosticFrame(second, false);
  slate::drawDiagnosticFrame(oldProfile, true);
  expect(memcmp(first, second, sizeof(first)) == 0,
         "diagnostic rendering is deterministic");

  expect(isBlack(first, 8, 8) && isBlack(first, 791, 471),
         "diagnostic frame draws its border");
  expect(isBlack(first, 18, 18) && isBlack(first, 781, 461),
         "diagnostic frame marks all display corners");
  expect(isBlack(first, 64, 318) && !isBlack(first, 72, 318),
         "diagnostic frame includes the checkerboard pattern");
  expect(memcmp(first, oldProfile, sizeof(first)) != 0,
         "profile label changes the generated frame");
}
}  // namespace

int main() {
  testFrameContractAndPixelPacking();
  testClippingAndRectangleFill();
  testDiagnosticFrameIsDeterministicAndDistinguishesProfiles();
  puts("Firmware frame tests passed");
  return 0;
}

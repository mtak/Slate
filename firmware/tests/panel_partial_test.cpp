#include <stdint.h>

#include <stdio.h>
#include <stdlib.h>
#include <vector>

typedef uint8_t UBYTE;
typedef uint32_t UDOUBLE;

namespace {
std::vector<UBYTE> sentData;
}

void EPD_SendCommand(UBYTE) {}
void EPD_SendData(UBYTE value) { sentData.push_back(value); }
void EPD_SendData2(UBYTE *, UDOUBLE) {}
void EPD_7IN5_V2_TurnOnDisplay() {}

#include "panel_partial.h"

namespace {
void expectWindowEnds(UDOUBLE xEnd, UDOUBLE yEnd, UBYTE xHigh,
                      UBYTE xLow, UBYTE yHigh, UBYTE yLow) {
  UBYTE image[slate::kFrameSize] = {};
  sentData.clear();
  slateDisplayStridedPartial(image, 0, 0, xEnd, yEnd);

#if defined(SLATE_EPD_PROFILE_V2_OLD)
  const size_t windowDataOffset = 0;
#else
  const size_t windowDataOffset = 2;
#endif
  if (sentData.size() < windowDataOffset + 8 ||
      sentData[windowDataOffset + 2] != xHigh ||
      sentData[windowDataOffset + 3] != xLow ||
      sentData[windowDataOffset + 6] != yHigh ||
      sentData[windowDataOffset + 7] != yLow) {
    fprintf(stderr, "FAIL: partial-window endpoint bytes are incorrect\n");
    exit(1);
  }
}
}  // namespace

int main() {
  expectWindowEnds(256, 256, 0x00, 0xFF, 0x00, 0xFF);
  expectWindowEnds(300, 257, 0x01, 0x2B, 0x01, 0x00);
  puts("Partial-window profile tests passed");
  return 0;
}

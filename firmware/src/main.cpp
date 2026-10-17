#include <Arduino.h>
#include <SPI.h>
#include <string.h>

#include "../vendor/waveshare/Config/DEV_Config.h"

#if defined(SLATE_EPD_PROFILE_V2_OLD)
#include "../vendor/waveshare/e-Paper/EPD_7in5_V2_old.cpp"
#else
#include "../vendor/waveshare/e-Paper/EPD_7in5_V2.cpp"
#endif

namespace {
constexpr uint16_t kDisplayWidth = 800;
constexpr uint16_t kDisplayHeight = 480;
constexpr uint16_t kBytesPerRow = kDisplayWidth / 8;
constexpr size_t kFrameSize = kBytesPerRow * kDisplayHeight;
constexpr uint8_t kTextScale = 4;

uint8_t frame[kFrameSize];

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

void setPixel(uint16_t x, uint16_t y, bool black) {
  if (x >= kDisplayWidth || y >= kDisplayHeight) {
    return;
  }

  const size_t index = static_cast<size_t>(y) * kBytesPerRow + (x / 8);
  const uint8_t mask = 0x80 >> (x & 7);
  if (black) {
    frame[index] &= static_cast<uint8_t>(~mask);
  } else {
    frame[index] |= mask;
  }
}

void fillRect(uint16_t x, uint16_t y, uint16_t width, uint16_t height,
              bool black) {
  for (uint16_t row = y; row < y + height && row < kDisplayHeight; ++row) {
    for (uint16_t column = x; column < x + width && column < kDisplayWidth;
         ++column) {
      setPixel(column, row, black);
    }
  }
}

void drawRect(uint16_t x, uint16_t y, uint16_t width, uint16_t height,
              bool black) {
  for (uint16_t column = x; column < x + width; ++column) {
    setPixel(column, y, black);
    setPixel(column, y + height - 1, black);
  }
  for (uint16_t row = y; row < y + height; ++row) {
    setPixel(x, row, black);
    setPixel(x + width - 1, row, black);
  }
}

const Glyph *findGlyph(char character) {
  for (const Glyph &glyph : kFont) {
    if (glyph.character == character) {
      return &glyph;
    }
  }
  return nullptr;
}

void drawText(uint16_t x, uint16_t y, const char *text, uint8_t scale,
              bool black) {
  for (; *text != '\0'; ++text) {
    const Glyph *glyph = findGlyph(*text);
    if (glyph != nullptr) {
      for (uint8_t row = 0; row < 7; ++row) {
        for (uint8_t column = 0; column < 5; ++column) {
          if (glyph->rows[row] & (1 << (4 - column))) {
            fillRect(x + column * scale, y + row * scale, scale, scale, black);
          }
        }
      }
    }
    x += 6 * scale;
  }
}

void drawDiagnosticFrame() {
  memset(frame, 0xFF, sizeof(frame));

  drawRect(8, 8, 784, 464, true);
  drawText(40, 34, "SLATE TEST", 5, true);

#if defined(SLATE_EPD_PROFILE_V2_OLD)
  drawText(42, 95, "V2 OLD", kTextScale, true);
#else
  drawText(42, 95, "V2 NEW", kTextScale, true);
#endif

  drawRect(40, 155, 330, 122, true);
  fillRect(44, 159, 322, 114, true);
  drawText(85, 195, "WHITE", 4, false);

  drawRect(430, 155, 330, 122, true);
  drawText(475, 195, "BLACK", 4, true);

  drawRect(40, 310, 720, 130, true);
  for (uint16_t y = 318; y < 432; y += 16) {
    for (uint16_t x = 48; x < 752; x += 16) {
      if (((x / 16) + (y / 16)) & 1) {
        fillRect(x, y, 8, 8, true);
      }
    }
  }

  // Distinct corner marks make orientation and edge clipping easy to spot.
  fillRect(18, 18, 20, 20, true);
  fillRect(762, 18, 20, 20, true);
  fillRect(18, 442, 20, 20, true);
  fillRect(762, 442, 20, 20, true);
}

void showDiagnosticFrame() {
  drawDiagnosticFrame();

#if defined(SLATE_EPD_PROFILE_V2_OLD)
  Serial.println("Testing Waveshare 7.5V2_old profile");
  EPD_7IN5_V2_Display_old(frame);
#else
  Serial.println("Testing Waveshare 7.5V2 profile");
  EPD_7IN5_V2_Display(frame);
#endif
}

bool initializePanel() {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  Serial.println("Initializing Waveshare 7.5V2_old profile");
  const UBYTE result = EPD_7IN5_V2_Init_old();
#else
  Serial.println("Initializing Waveshare 7.5V2 profile");
  const UBYTE result = EPD_7IN5_V2_Init();
#endif

  return result == 0 && !slateEpdBusyTimeout;
}

void sleepPanel() {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  EPD_7IN5_V2_Sleep_old();
#else
  EPD_7IN5_V2_Sleep();
#endif
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(250);
  Serial.println("Slate e-paper driver-profile diagnostic");

  DEV_Module_Init();
  if (!initializePanel()) {
    Serial.println("Panel initialization failed or timed out");
    DEV_Module_Exit();
    return;
  }

  showDiagnosticFrame();
  if (slateEpdBusyTimeout) {
    Serial.println("Panel refresh timed out");
    DEV_Module_Exit();
    return;
  }

  sleepPanel();
  if (slateEpdBusyTimeout) {
    Serial.println("Panel sleep wait timed out");
  } else {
    Serial.println("Diagnostic update complete");
  }
  DEV_Module_Exit();
}

void loop() {
  delay(1000);
}

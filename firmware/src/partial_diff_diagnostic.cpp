#include <Arduino.h>
#include <string.h>

#include "frame.h"
#include "frame_diff.h"
#include "../vendor/waveshare/Config/DEV_Config.h"

#if defined(SLATE_EPD_PROFILE_V2_OLD)
#include "../vendor/waveshare/e-Paper/EPD_7in5_V2_old.cpp"
#else
#include "../vendor/waveshare/e-Paper/EPD_7in5_V2.cpp"
#endif
#include "panel_partial.h"

namespace {
constexpr uint16_t kMarkY = 286;
constexpr uint16_t kMarkHeight = 16;
constexpr uint16_t kFirstMarkX = 80;
constexpr uint16_t kSecondMarkX = 160;
constexpr uint16_t kMarkWidth = 24;

uint8_t frame[slate::kFrameSize];

bool initializePanel(bool partial) {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  const UBYTE result = partial ? EPD_7IN5_V2_Init_Partial_old()
                               : EPD_7IN5_V2_Init_old();
#else
  const UBYTE result = partial ? EPD_7IN5_V2_Init_Part()
                               : EPD_7IN5_V2_Init();
#endif
  return result == 0 && !slateEpdBusyTimeout;
}

void displayFullFrame() {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  EPD_7IN5_V2_Display_old(frame);
#else
  EPD_7IN5_V2_Display(frame);
#endif
}

void sleepPanel() {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  EPD_7IN5_V2_Sleep_old();
#else
  EPD_7IN5_V2_Sleep();
#endif
}

void makeIncomingRow(uint16_t y, uint8_t *row) {
  memcpy(row, frame + static_cast<size_t>(y) * slate::kBytesPerRow,
         slate::kBytesPerRow);
  if (y < kMarkY || y >= kMarkY + kMarkHeight) return;
  for (uint16_t x = kFirstMarkX; x < kFirstMarkX + kMarkWidth; ++x) {
    row[x / 8] &= static_cast<uint8_t>(~(0x80 >> (x & 7)));
  }
  for (uint16_t x = kSecondMarkX; x < kSecondMarkX + kMarkWidth; ++x) {
    row[x / 8] &= static_cast<uint8_t>(~(0x80 >> (x & 7)));
  }
}

bool runDiagnostic() {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  Serial.println("Local changed-region diagnostic: 7.5V2_old");
#else
  Serial.println("Local changed-region diagnostic: 7.5V2");
#endif
  Serial.println("Baseline first; then two black bars inside one bounded partial window.");

  DEV_Module_Init();
  slate::drawDiagnosticFrame(frame,
#if defined(SLATE_EPD_PROFILE_V2_OLD)
                             true
#else
                             false
#endif
  );
  if (!initializePanel(false)) {
    Serial.println("FAIL: full-refresh initialization timed out");
    return false;
  }
  displayFullFrame();
  if (slateEpdBusyTimeout) {
    Serial.println("FAIL: baseline full refresh timed out");
    return false;
  }
  sleepPanel();
  if (slateEpdBusyTimeout) {
    Serial.println("FAIL: baseline panel sleep timed out");
    return false;
  }
  delay(1500);

  slate::FrameDiff diff;
  uint8_t incomingRow[slate::kBytesPerRow];
  for (uint16_t y = 0; y < slate::kDisplayHeight; ++y) {
    makeIncomingRow(y, incomingRow);
    diff.compareAndReplaceRow(frame, y, incomingRow);
  }
  const slate::ChangedRegion region = diff.region();
  const uint16_t expectedX = kFirstMarkX;
  const uint16_t expectedWidth = kSecondMarkX + kMarkWidth - kFirstMarkX;
  if (!region.changed || region.x != expectedX || region.y != kMarkY ||
      region.width != expectedWidth || region.height != kMarkHeight) {
    Serial.printf("FAIL: detected region x=%u y=%u w=%u h=%u\n",
                  region.x, region.y, region.width, region.height);
    return false;
  }
  Serial.printf("PASS: local compare found x=%u y=%u w=%u h=%u\n",
                region.x, region.y, region.width, region.height);

  if (!initializePanel(true)) {
    Serial.println("FAIL: partial-refresh initialization timed out");
    return false;
  }
  slateDisplayStridedPartial(frame, region.x, region.y,
      region.x + region.width, region.y + region.height);
  if (slateEpdBusyTimeout) {
    Serial.println("FAIL: partial window refresh timed out");
    return false;
  }
  sleepPanel();
  if (slateEpdBusyTimeout) {
    Serial.println("FAIL: partial-update panel sleep timed out");
    return false;
  }
  DEV_Module_Exit();
  Serial.println("READY: inspect the two black bars at x=80 and x=160, y=286.");
  Serial.println("Expected changed window: x=80 y=286 w=104 h=16; image is paused here.");
  return true;
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(250);
  if (!runDiagnostic()) {
    DEV_Module_Exit();
    Serial.println("Diagnostic stopped after failure; check serial output.");
  }
}

void loop() { delay(1000); }

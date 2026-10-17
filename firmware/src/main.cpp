#include <Arduino.h>
#include <SPI.h>

#include "frame.h"
#include "../vendor/waveshare/Config/DEV_Config.h"

#if defined(SLATE_EPD_PROFILE_V2_OLD)
#include "../vendor/waveshare/e-Paper/EPD_7in5_V2_old.cpp"
#else
#include "../vendor/waveshare/e-Paper/EPD_7in5_V2.cpp"
#endif

namespace {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
constexpr bool kOldProfile = true;
#else
constexpr bool kOldProfile = false;
#endif
uint8_t frame[slate::kFrameSize];

void showDiagnosticFrame() {
  slate::drawDiagnosticFrame(frame, kOldProfile);

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

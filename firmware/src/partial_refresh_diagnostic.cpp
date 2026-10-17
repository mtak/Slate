#include <Arduino.h>

#include <string.h>

#include "frame.h"
#include "../vendor/waveshare/Config/DEV_Config.h"

#if defined(SLATE_EPD_PROFILE_V2_OLD)
#include "../vendor/waveshare/e-Paper/EPD_7in5_V2_old.cpp"
#else
#include "../vendor/waveshare/e-Paper/EPD_7in5_V2.cpp"
#endif

namespace {
constexpr UWORD kWindowX = 320;
constexpr UWORD kWindowY = 320;
constexpr UWORD kWindowWidth = 160;
constexpr UWORD kWindowHeight = 80;
constexpr size_t kWindowBytes = kWindowWidth * kWindowHeight / 8;

uint8_t frame[slate::kFrameSize];
uint8_t windowImage[kWindowBytes];

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

void displayPartialWindow() {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  EPD_7IN5_V2_Display_Partial_old(
      windowImage, kWindowX, kWindowY,
      kWindowX + kWindowWidth, kWindowY + kWindowHeight);
#else
  EPD_7IN5_V2_Display_Part(
      windowImage, kWindowX, kWindowY,
      kWindowX + kWindowWidth, kWindowY + kWindowHeight);
#endif
}

void sleepPanel() {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  EPD_7IN5_V2_Sleep_old();
#else
  EPD_7IN5_V2_Sleep();
#endif
}

void setWindowSolid(bool black) {
  memset(windowImage, black ? 0x00 : 0xFF, sizeof(windowImage));
}

void setWindowCheckerboard() {
  memset(windowImage, 0xFF, sizeof(windowImage));
  for (UWORD y = 0; y < kWindowHeight; ++y) {
    for (UWORD x = 0; x < kWindowWidth; ++x) {
      if (((x / 8) + (y / 8)) & 1) {
        windowImage[y * (kWindowWidth / 8) + x / 8] &=
            static_cast<uint8_t>(~(0x80 >> (x & 7)));
      }
    }
  }
}

bool performFullRefresh(const char *description) {
  Serial.printf("Full refresh: %s\n", description);
  slate::drawDiagnosticFrame(frame,
#if defined(SLATE_EPD_PROFILE_V2_OLD)
                             true
#else
                             false
#endif
  );
  if (!initializePanel(false)) {
    Serial.println("Full-refresh initialization failed or timed out");
    return false;
  }
  displayFullFrame();
  if (slateEpdBusyTimeout) {
    Serial.println("Full refresh timed out");
    return false;
  }
  sleepPanel();
  return !slateEpdBusyTimeout;
}

bool performPartialRefresh(const char *description) {
  Serial.printf("Partial refresh: %s, window x=%u y=%u w=%u h=%u\n",
                description, kWindowX, kWindowY,
                kWindowWidth, kWindowHeight);
  if (!initializePanel(true)) {
    Serial.println("Partial-refresh initialization failed or timed out");
    return false;
  }
  displayPartialWindow();
  if (slateEpdBusyTimeout) {
    Serial.println("Partial refresh timed out");
    return false;
  }
  sleepPanel();
  return !slateEpdBusyTimeout;
}

void runDiagnostic() {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  Serial.println("Slate small-window partial-refresh diagnostic: 7.5V2_old");
#else
  Serial.println("Slate small-window partial-refresh diagnostic: 7.5V2");
#endif

  DEV_Module_Init();
  if (!performFullRefresh("static baseline")) {
    DEV_Module_Exit();
    return;
  }
  delay(3000);

  setWindowSolid(true);
  if (!performPartialRefresh("solid black")) {
    DEV_Module_Exit();
    return;
  }
  delay(3000);

  setWindowSolid(false);
  if (!performPartialRefresh("solid white")) {
    DEV_Module_Exit();
    return;
  }
  delay(3000);

  setWindowCheckerboard();
  if (!performPartialRefresh("checkerboard")) {
    DEV_Module_Exit();
    return;
  }
  delay(3000);

  if (performFullRefresh("restore baseline and clear ghosting")) {
    Serial.println("Partial-refresh diagnostic complete");
  }
  DEV_Module_Exit();
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(250);
  runDiagnostic();
}

void loop() { delay(1000); }

#include <Arduino.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <esp_task_wdt.h>

#include "frame.h"
#include "wifi_retry.h"
#include "../vendor/waveshare/Config/DEV_Config.h"

#if __has_include("slate_config.h")
#include "slate_config.h"
#endif

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
constexpr uint32_t kWatchdogTimeoutSeconds = 60;
constexpr uint32_t kReconnectInitialDelayMs = 1000;
constexpr uint32_t kReconnectMaxDelayMs = 30000;
constexpr uint32_t kWatchdogFeedIntervalMs = 1000;
#if defined(SLATE_WIFI_SSID) && defined(SLATE_WIFI_PASSWORD)
constexpr bool kWifiConfigured = true;
#else
constexpr bool kWifiConfigured = false;
#endif

bool fetchFrame() {
#if !defined(SLATE_SERVER_BASE_URL) || !defined(SLATE_DEVICE_TOKEN)
  Serial.println("Frame endpoint is not configured");
  return false;
#else
  const String baseUrl = SLATE_SERVER_BASE_URL;
  if (!baseUrl.startsWith("https://") || SLATE_DEVICE_TOKEN[0] == '\0') {
    Serial.println("Frame endpoint must use HTTPS and a device token");
    return false;
  }
  WiFiClientSecure client;
#if !defined(SLATE_TLS_VERIFY) || SLATE_TLS_VERIFY
  client.setCACert(SLATE_ROOT_CA);
#else
  client.setInsecure();
#endif
  HTTPClient request;
  const String url = baseUrl + "/api/frame/v1";
  if (!request.begin(client, url)) {
    Serial.println("Could not start frame request");
    return false;
  }
  request.addHeader("Authorization", String("Bearer ") + SLATE_DEVICE_TOKEN);
  const int status = request.GET();
  bool ok = false;
  if (status == HTTP_CODE_OK && request.getSize() == slate::kFrameSize) {
    WiFiClient *stream = request.getStreamPtr();
    const size_t count = stream->readBytes(frame, slate::kFrameSize);
    ok = count == slate::kFrameSize;
  }
  request.end();
  if (ok) Serial.println("Frame downloaded over HTTPS");
  else Serial.printf("Frame request failed (HTTP %d or invalid frame size)\n", status);
  return ok;
#endif
}

void feedWatchdog() { esp_task_wdt_reset(); }

void waitWithWatchdog(uint32_t durationMs) {
  const uint32_t startedAt = millis();
  while (millis() - startedAt < durationMs) {
    feedWatchdog();
    delay(kWatchdogFeedIntervalMs);
  }
}

void connectToWifi() {
#if !defined(SLATE_WIFI_SSID) || !defined(SLATE_WIFI_PASSWORD)
  Serial.println("Wi-Fi is not configured; copy include/slate_config.h.example");
  return;
#else
  if (SLATE_WIFI_SSID[0] == '\0') {
    Serial.println("Wi-Fi is not configured; set credentials in slate_config.h");
    return;
  }

  WiFi.mode(WIFI_STA);
  uint32_t retryDelayMs = kReconnectInitialDelayMs;
  while (WiFi.status() != WL_CONNECTED) {
    Serial.println("Connecting to Wi-Fi");
    WiFi.begin(SLATE_WIFI_SSID, SLATE_WIFI_PASSWORD);
    const uint32_t attemptStartedAt = millis();
    while (WiFi.status() != WL_CONNECTED &&
           millis() - attemptStartedAt < retryDelayMs) {
      waitWithWatchdog(kWatchdogFeedIntervalMs);
    }
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("Wi-Fi connected");
      return;
    }
    Serial.println("Wi-Fi connection attempt timed out; retrying");
    retryDelayMs = slate::nextWifiRetryDelay(retryDelayMs, kReconnectMaxDelayMs);
  }
#endif
}

void maintainWifi() {
  if (!kWifiConfigured) return;
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.println("Wi-Fi connection lost; reconnecting");
  connectToWifi();
}

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
  if (esp_task_wdt_init(kWatchdogTimeoutSeconds, true) != ESP_OK ||
      esp_task_wdt_add(NULL) != ESP_OK) {
    Serial.println("Could not initialize task watchdog");
    ESP.restart();
  }
  Serial.println("Slate e-paper driver-profile diagnostic");

  connectToWifi();
  feedWatchdog();
  const bool haveFrame = WiFi.status() == WL_CONNECTED && fetchFrame();

  DEV_Module_Init();
  if (!initializePanel()) {
    Serial.println("Panel initialization failed or timed out");
    DEV_Module_Exit();
    return;
  }

  if (haveFrame) {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
    EPD_7IN5_V2_Display_old(frame);
#else
    EPD_7IN5_V2_Display(frame);
#endif
  } else {
    showDiagnosticFrame();
  }
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
  maintainWifi();
  feedWatchdog();
  delay(kWatchdogFeedIntervalMs);
}

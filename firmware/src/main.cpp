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
bool haveDisplayedFrame = false;
bool havePendingFrame = false;
bool havePanelRefreshAttempt = false;
String lastEtag;
String displayedEtag;
bool frameBufferInvalidated = false;
uint32_t lastPanelRefreshAt = 0;
constexpr uint32_t kWatchdogTimeoutSeconds = 60;
constexpr uint32_t kReconnectInitialDelayMs = 1000;
constexpr uint32_t kReconnectMaxDelayMs = 30000;
constexpr uint32_t kWatchdogFeedIntervalMs = 1000;
#if defined(SLATE_POLL_INTERVAL_SECONDS) && SLATE_POLL_INTERVAL_SECONDS > 0
constexpr uint32_t kPollIntervalMs = SLATE_POLL_INTERVAL_SECONDS * 1000UL;
#else
constexpr uint32_t kPollIntervalMs = 60000;
#endif
#if defined(SLATE_MIN_REFRESH_INTERVAL_SECONDS) && SLATE_MIN_REFRESH_INTERVAL_SECONDS > 0
constexpr uint32_t kMinimumRefreshIntervalMs = SLATE_MIN_REFRESH_INTERVAL_SECONDS * 1000UL;
#else
constexpr uint32_t kMinimumRefreshIntervalMs = 60000;
#endif
uint32_t nextPollAt = 0;
#if defined(SLATE_WIFI_SSID) && defined(SLATE_WIFI_PASSWORD)
constexpr bool kWifiConfigured = true;
#else
constexpr bool kWifiConfigured = false;
#endif

bool fetchFrame() {
  frameBufferInvalidated = false;
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
  const char *headerKeys[] = {"ETag", "Content-Type", "X-Slate-Format-Version",
                              "X-Slate-Width", "X-Slate-Height"};
  request.collectHeaders(headerKeys, sizeof(headerKeys) / sizeof(headerKeys[0]));
  if (lastEtag.length() > 0) request.addHeader("If-None-Match", lastEtag);
  request.setTimeout(10000);
  const int status = request.GET();
  bool ok = false;
  if (status == HTTP_CODE_NOT_MODIFIED) {
    Serial.println("Frame unchanged (ETag)");
    request.end();
    return false;
  }
  const bool validMetadata = request.header("Content-Type") == "application/vnd.slate.frame" &&
      request.header("X-Slate-Format-Version") == "1" &&
      request.header("X-Slate-Width") == "800" &&
      request.header("X-Slate-Height") == "480";
  if (status == HTTP_CODE_OK && validMetadata && request.getSize() == slate::kFrameSize) {
    WiFiClient *stream = request.getStreamPtr();
    frameBufferInvalidated = true;
    const size_t count = stream->readBytes(frame, slate::kFrameSize);
    ok = count == slate::kFrameSize;
    if (ok) {
      const String responseEtag = request.header("ETag");
      if (responseEtag.length() == 0) {
        ok = false;
      } else {
        lastEtag = responseEtag;
        frameBufferInvalidated = false;
      }
    }
  }
  request.end();
  if (ok) Serial.println("Validated frame downloaded over HTTPS");
  else Serial.printf("Frame request rejected (HTTP %d or invalid frame contract)\n", status);
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

void pollForFrame() {
  const uint32_t now = millis();
  if (static_cast<int32_t>(now - nextPollAt) >= 0) {
    nextPollAt = now + kPollIntervalMs;
    if (WiFi.status() == WL_CONNECTED && fetchFrame()) {
      if (!haveDisplayedFrame || lastEtag != displayedEtag) {
        havePendingFrame = true;
      } else {
        havePendingFrame = false;
        Serial.println("Frame payload unchanged");
      }
    } else if (frameBufferInvalidated) {
      havePendingFrame = false;
    }
  }
  if (!havePendingFrame) return;
  if (havePanelRefreshAttempt && now - lastPanelRefreshAt < kMinimumRefreshIntervalMs) {
    Serial.println("Frame changed; waiting for minimum panel refresh interval");
    return;
  }
  DEV_Module_Init();
  if (!initializePanel()) {
    Serial.println("Panel initialization failed or timed out; keeping current display");
    DEV_Module_Exit();
    return;
  }
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  lastPanelRefreshAt = millis();
  havePanelRefreshAttempt = true;
  EPD_7IN5_V2_Display_old(frame);
#else
  lastPanelRefreshAt = millis();
  havePanelRefreshAttempt = true;
  EPD_7IN5_V2_Display(frame);
#endif
  if (slateEpdBusyTimeout) {
    Serial.println("Panel refresh timed out; keeping current display");
    DEV_Module_Exit();
    return;
  }
  sleepPanel();
  if (slateEpdBusyTimeout) {
    Serial.println("Panel sleep wait timed out");
    DEV_Module_Exit();
    return;
  }
  haveDisplayedFrame = true;
  havePendingFrame = false;
  displayedEtag = lastEtag;
  Serial.println("Updated panel with fetched frame");
  DEV_Module_Exit();
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
  Serial.println("Slate frame client");

  connectToWifi();
  pollForFrame();
}

void loop() {
  maintainWifi();
  pollForFrame();
  feedWatchdog();
  delay(kWatchdogFeedIntervalMs);
}

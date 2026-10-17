#include <Arduino.h>
#include <string.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <esp_task_wdt.h>
#include <esp_system.h>

#include "frame.h"
#include "frame_diff.h"
#include "frame_ingestion.h"
#include "refresh_policy.h"
#include "device_hostname.h"
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
#include "panel_partial.h"

namespace {
uint8_t frame[slate::kFrameSize];
bool haveDisplayedFrame = false;
bool havePendingFrame = false;
bool havePanelRefreshAttempt = false;
String lastEtag;
String displayedEtag;
bool frameBufferMatchesDisplay = false;
bool pendingRequiresFullRefresh = false;
bool pendingHasChanges = true;
uint16_t pendingRegionX = 0;
uint16_t pendingRegionY = 0;
uint16_t pendingRegionWidth = slate::kDisplayWidth;
uint16_t pendingRegionHeight = slate::kDisplayHeight;
uint32_t lastPanelRefreshAt = 0;
uint32_t partialRefreshesSinceFull = 0;
constexpr uint32_t kWatchdogTimeoutSeconds = 60;
constexpr uint32_t kReconnectInitialDelayMs = 1000;
constexpr uint32_t kReconnectMaxDelayMs = 30000;
constexpr uint32_t kWatchdogFeedIntervalMs = 1000;
constexpr uint32_t kWatchdogDemoCountdownSeconds = 15;
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
#if defined(SLATE_PARTIAL_REFRESHES_BEFORE_FULL)
#if SLATE_PARTIAL_REFRESHES_BEFORE_FULL > 0
constexpr uint32_t kPartialRefreshesBeforeFull = SLATE_PARTIAL_REFRESHES_BEFORE_FULL;
#else
constexpr uint32_t kPartialRefreshesBeforeFull = 0;
#endif
#else
constexpr uint32_t kPartialRefreshesBeforeFull = 2;
#endif
uint32_t nextPollAt = 0;
#if defined(SLATE_WIFI_SSID) && defined(SLATE_WIFI_PASSWORD)
constexpr bool kWifiConfigured = true;
#else
constexpr bool kWifiConfigured = false;
#endif

bool fetchFrame(bool comparePartial) {
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
  const char *headerKeys[] = {"ETag", "Content-Type"};
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
  const String contentType = request.header("Content-Type");
  const String responseEtag = request.header("ETag");
  const bool validFrame = slate::isValidFrameResponse(
      status, contentType.c_str(), request.getSize(), responseEtag.c_str());
  if (validFrame) {
    WiFiClient *stream = request.getStreamPtr();
    frameBufferMatchesDisplay = false;
    slate::FrameDiff diff;
    ok = slate::ingestFrameRows(frame, comparePartial, diff,
                                [](void *context, uint8_t *row,
                                   size_t rowSize) -> size_t {
                                  WiFiClient *client =
                                      static_cast<WiFiClient *>(context);
                                  return client == nullptr
                                             ? 0
                                             : client->readBytes(row, rowSize);
                                },
                                stream);
    if (ok) {
      lastEtag = responseEtag;
      pendingRequiresFullRefresh = !comparePartial;
      const slate::ChangedRegion changed = diff.region();
      pendingHasChanges = changed.changed || !comparePartial;
      pendingRegionX = changed.changed ? changed.x : 0;
      pendingRegionY = changed.changed ? changed.y : 0;
      pendingRegionWidth = changed.changed ? changed.width : slate::kDisplayWidth;
      pendingRegionHeight = changed.changed ? changed.height : slate::kDisplayHeight;
      if (!changed.changed && comparePartial) {
        displayedEtag = lastEtag;
        frameBufferMatchesDisplay = true;
      }
    }
  }
  request.end();
  if (ok) Serial.println("Validated full frame downloaded over HTTPS");
  else Serial.printf("Frame request rejected (HTTP %d or invalid frame contract)\n", status);
  return ok;
#endif
}

void feedWatchdog() { esp_task_wdt_reset(); }

void runWatchdogDemoIfEnabled() {
#if defined(SLATE_WATCHDOG_DEMO)
  const esp_reset_reason_t resetReason = esp_reset_reason();
  if (resetReason == ESP_RST_TASK_WDT || resetReason == ESP_RST_PANIC) {
    Serial.printf("Watchdog demo: reset reason %d detected; continuing startup without repeating stall\n",
                  static_cast<int>(resetReason));
    return;
  }

  Serial.println("WATCHDOG DEMO ENABLED: send 'g' to arm the intentional task stall");
  while (true) {
    feedWatchdog();
    if (Serial.available() > 0) {
      if (Serial.read() == 'g') break;
      Serial.println("Watchdog demo: send 'g' to start, or reset to cancel");
    }
    delay(kWatchdogFeedIntervalMs);
  }

  for (uint32_t remaining = kWatchdogDemoCountdownSeconds; remaining > 0;
       --remaining) {
    Serial.printf("Watchdog demo: stalling in %lu seconds\n",
                  static_cast<unsigned long>(remaining));
    feedWatchdog();
    delay(kWatchdogFeedIntervalMs);
  }

  Serial.println("Watchdog demo: now stalling without feeding the task watchdog");
  while (true) delay(1000);
#endif
}

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

  char hostname[slate::kDeviceHostnameSize];
  const String macAddress = WiFi.macAddress();
  const bool hostnameAvailable = slate::makeDeviceHostname(
      macAddress.c_str(), hostname, sizeof(hostname));
  if (hostnameAvailable) {
    // WiFi.mode() applies the stored hostname to the station interface.
    WiFi.setHostname(hostname);
  } else {
    Serial.println("Could not create Wi-Fi hostname from station MAC");
  }
  if (!WiFi.mode(WIFI_STA)) {
    Serial.println("Could not start Wi-Fi station");
    return;
  }
  if (hostnameAvailable) {
    Serial.printf("Wi-Fi hostname: %s\n", hostname);
  }
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

bool initializePanel(bool partialRefresh) {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  Serial.println(partialRefresh
      ? "Initializing Waveshare 7.5V2_old partial refresh"
      : "Initializing Waveshare 7.5V2_old profile");
  const UBYTE result = partialRefresh
      ? EPD_7IN5_V2_Init_Partial_old()
      : EPD_7IN5_V2_Init_old();
#else
  Serial.println(partialRefresh
      ? "Initializing Waveshare 7.5V2 partial refresh"
      : "Initializing Waveshare 7.5V2 profile");
  const UBYTE result = partialRefresh
      ? EPD_7IN5_V2_Init_Part()
      : EPD_7IN5_V2_Init();
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
  const slate::RefreshMode plannedRefreshMode = slate::chooseRefreshMode(
      haveDisplayedFrame, partialRefreshesSinceFull,
      kPartialRefreshesBeforeFull);
  const bool plannedPartialRefresh =
      plannedRefreshMode == slate::RefreshMode::Partial;
  if (static_cast<int32_t>(now - nextPollAt) >= 0) {
    nextPollAt = now + kPollIntervalMs;
    if (!havePendingFrame && WiFi.status() == WL_CONNECTED &&
        fetchFrame(plannedPartialRefresh && haveDisplayedFrame && frameBufferMatchesDisplay)) {
      if (!haveDisplayedFrame || lastEtag != displayedEtag) {
        havePendingFrame = lastEtag != displayedEtag;
        if (!havePendingFrame) Serial.println("Frame payload unchanged");
      } else {
        havePendingFrame = false;
        Serial.println("Frame payload unchanged");
      }
    }
  }
  if (!havePendingFrame) return;
  if (havePanelRefreshAttempt && now - lastPanelRefreshAt < kMinimumRefreshIntervalMs) {
    Serial.println("Frame changed; waiting for minimum panel refresh interval");
    return;
  }
  const bool partialRefresh = plannedPartialRefresh && !pendingRequiresFullRefresh;
  const slate::RefreshMode refreshMode = partialRefresh
      ? slate::RefreshMode::Partial : slate::RefreshMode::Full;
  if (partialRefresh && !pendingHasChanges) {
    Serial.println("Frame differs; no changed bytes found; skipping panel refresh");
    displayedEtag = lastEtag;
    havePendingFrame = false;
    frameBufferMatchesDisplay = true;
    return;
  }
  DEV_Module_Init();
  if (!initializePanel(partialRefresh)) {
    Serial.println("Panel initialization failed or timed out; keeping current display");
    DEV_Module_Exit();
    pendingRequiresFullRefresh = true;
    return;
  }
  lastPanelRefreshAt = millis();
  havePanelRefreshAttempt = true;
  if (partialRefresh) {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
    slateDisplayStridedPartial(frame, pendingRegionX, pendingRegionY,
        pendingRegionX + pendingRegionWidth, pendingRegionY + pendingRegionHeight);
#else
    slateDisplayStridedPartial(frame, pendingRegionX, pendingRegionY,
        pendingRegionX + pendingRegionWidth, pendingRegionY + pendingRegionHeight);
#endif
  } else {
#if defined(SLATE_EPD_PROFILE_V2_OLD)
    EPD_7IN5_V2_Display_old(frame);
#else
    EPD_7IN5_V2_Display(frame);
#endif
  }
  if (slateEpdBusyTimeout) {
    Serial.println("Panel refresh timed out; keeping current display");
    DEV_Module_Exit();
    pendingRequiresFullRefresh = true;
    return;
  }
  sleepPanel();
  if (slateEpdBusyTimeout) {
    Serial.println("Panel sleep wait timed out");
    DEV_Module_Exit();
    pendingRequiresFullRefresh = true;
    return;
  }
  haveDisplayedFrame = true;
  frameBufferMatchesDisplay = true;
  pendingRequiresFullRefresh = false;
  havePendingFrame = false;
  displayedEtag = lastEtag;
  partialRefreshesSinceFull =
      slate::partialRefreshesAfterSuccess(refreshMode, partialRefreshesSinceFull);
  if (partialRefresh) {
    Serial.printf("Updated panel with partial refresh (%lu before full)\n",
        static_cast<unsigned long>(partialRefreshesSinceFull));
  } else {
    partialRefreshesSinceFull = 0;
    Serial.println("Updated panel with full refresh");
  }
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
  runWatchdogDemoIfEnabled();

  connectToWifi();
  pollForFrame();
}

void loop() {
  maintainWifi();
  pollForFrame();
  feedWatchdog();
  delay(kWatchdogFeedIntervalMs);
}

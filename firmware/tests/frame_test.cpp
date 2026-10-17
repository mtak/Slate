#include "frame.h"
#include "frame_diff.h"
#include "refresh_policy.h"
#include "device_hostname.h"
#include "wifi_retry.h"

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
  expect(isBlack(first, 18, 18) && isBlack(first, 781, 18) &&
             isBlack(first, 18, 461) && isBlack(first, 781, 461),
         "diagnostic frame marks all display corners");
  expect(isBlack(first, 64, 318) && !isBlack(first, 72, 318),
         "diagnostic frame includes the checkerboard pattern");
  expect(memcmp(first, oldProfile, sizeof(first)) != 0,
         "profile label changes the generated frame");
}

void testWifiRetryBackoffIsBounded() {
  expect(slate::nextWifiRetryDelay(1000, 30000) == 2000,
         "Wi-Fi retry delay doubles after a failed attempt");
  expect(slate::nextWifiRetryDelay(16000, 30000) == 30000,
         "Wi-Fi retry delay caps at the configured maximum");
  expect(slate::nextWifiRetryDelay(30000, 30000) == 30000,
         "Wi-Fi retry delay stays capped");
}

void testRefreshPolicyUsesConfiguredPartialCount() {
  using slate::RefreshMode;
  expect(slate::chooseRefreshMode(false, 0, 2) == RefreshMode::Full,
         "the first displayed frame uses a full refresh");

  uint32_t partialRefreshesSinceFull = 0;
  for (uint32_t expected = 1; expected <= 2; ++expected) {
    const RefreshMode mode = slate::chooseRefreshMode(
        true, partialRefreshesSinceFull, 2);
    expect(mode == RefreshMode::Partial,
           "the configured number of partial refreshes is selected");
    partialRefreshesSinceFull =
        slate::partialRefreshesAfterSuccess(mode, partialRefreshesSinceFull);
    expect(partialRefreshesSinceFull == expected,
           "successful partial refreshes advance the counter");
  }

  const RefreshMode full = slate::chooseRefreshMode(
      true, partialRefreshesSinceFull, 2);
  expect(full == RefreshMode::Full,
         "a full refresh follows the configured partial refreshes");
  expect(slate::partialRefreshesAfterSuccess(full, partialRefreshesSinceFull) == 0,
         "a successful full refresh resets the partial refresh counter");
  expect(slate::chooseRefreshMode(true, 0, 0) == RefreshMode::Full,
         "a configured count of zero disables partial refreshes");
}

void testFrameDiffBuildsByteAlignedChangedBounds() {
  slate::FrameDiff diff;
  expect(!diff.region().changed, "unchanged frame has no changed region");
  diff.record(12, 30);
  diff.record(15, 27);
  diff.record(4, 33);
  const slate::ChangedRegion region = diff.region();
  expect(region.changed, "changed bytes produce a region");
  expect(region.x == 32 && region.y == 27,
         "region starts at the first changed byte and row");
  expect(region.width == 96 && region.height == 7,
         "region covers changed byte and row bounds");
}

void testFrameDiffComparesAndReplacesRowsInPlace() {
  uint8_t frame[slate::kFrameSize];
  uint8_t incoming[slate::kBytesPerRow];
  slate::clearFrame(frame);
  slate::FrameDiff diff;

  memset(incoming, 0xFF, sizeof(incoming));
  incoming[3] = 0xF0;
  diff.compareAndReplaceRow(frame, 14, incoming);
  expect(frame[14 * slate::kBytesPerRow + 3] == 0xF0,
         "incoming row replaces its old bytes in place");

  memset(incoming, 0xFF, sizeof(incoming));
  incoming[7] = 0x0F;
  diff.compareAndReplaceRow(frame, 16, incoming);
  const slate::ChangedRegion region = diff.region();
  expect(region.changed && region.x == 24 && region.y == 14 &&
             region.width == 40 && region.height == 3,
         "row comparisons accumulate bounds across separated changes");
  expect(frame[16 * slate::kBytesPerRow + 7] == 0x0F,
         "later incoming row also replaces its old bytes");
}

void testDeviceHostnameUsesUppercaseMacSuffix() {
  char hostname[slate::kDeviceHostnameSize];
  expect(slate::makeDeviceHostname("AA:BB:CC:69:08:f8", hostname,
                                  sizeof(hostname)),
         "valid station MAC produces a hostname");
  expect(strcmp(hostname, "Slate-6908F8") == 0,
         "hostname uses the final six MAC digits in uppercase");
  expect(strlen(hostname) == 12 && strlen(hostname) <= 63,
         "hostname stays within the DNS hostname length limit");
  expect(!slate::makeDeviceHostname("not-a-mac", hostname, sizeof(hostname)),
         "invalid MAC does not produce a hostname");
  expect(!slate::makeDeviceHostname("AA:BB:CC:69:08:F8", hostname, 12),
         "hostname formatting checks output capacity");
}
}  // namespace

int main() {
  testFrameContractAndPixelPacking();
  testClippingAndRectangleFill();
  testDiagnosticFrameIsDeterministicAndDistinguishesProfiles();
  testWifiRetryBackoffIsBounded();
  testRefreshPolicyUsesConfiguredPartialCount();
  testFrameDiffBuildsByteAlignedChangedBounds();
  testFrameDiffComparesAndReplacesRowsInPlace();
  testDeviceHostnameUsesUppercaseMacSuffix();
  puts("Firmware tests passed");
  return 0;
}

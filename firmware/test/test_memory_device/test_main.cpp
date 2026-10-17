#include <Arduino.h>
#include <esp_heap_caps.h>
#include <string.h>
#include <unity.h>

#include "frame_ingestion.h"

namespace {

uint8_t frame[slate::kFrameSize];

struct RowSource {
  uint8_t value;
};

struct HeapSample {
  size_t free8Bit;
  size_t largest8Bit;
};

size_t fillRow(void *context, uint8_t *row, size_t rowSize) {
  const RowSource *source = static_cast<const RowSource *>(context);
  memset(row, source->value, rowSize);
  return rowSize;
}

HeapSample sampleHeap() {
  return {heap_caps_get_free_size(MALLOC_CAP_8BIT),
          heap_caps_get_largest_free_block(MALLOC_CAP_8BIT)};
}

bool runFrames(uint8_t count) {
  for (uint8_t iteration = 0; iteration < count; ++iteration) {
    RowSource source = {static_cast<uint8_t>((iteration & 1) ? 0x00 : 0xA5)};
    slate::FrameDiff diff;
    if (!slate::ingestFrameRows(frame, true, diff, fillRow, &source)) {
      return false;
    }
  }
  return true;
}

void testRepeatedFrameIngestionKeepsHeapIntact() {
  memset(frame, 0xFF, sizeof(frame));
  TEST_ASSERT_TRUE(runFrames(3));  // Warm up the production path first.
  const HeapSample before = sampleHeap();
  TEST_ASSERT_TRUE_MESSAGE(heap_caps_check_integrity_all(false),
                           "heap integrity check failed before workload");

  TEST_ASSERT_TRUE(runFrames(64));

  const HeapSample after = sampleHeap();
  Serial.printf("MEMORY_TEST cycles=64 free_8bit_before=%u free_8bit_after=%u "
                "largest_8bit_before=%u largest_8bit_after=%u bytes\n",
                static_cast<unsigned>(before.free8Bit),
                static_cast<unsigned>(after.free8Bit),
                static_cast<unsigned>(before.largest8Bit),
                static_cast<unsigned>(after.largest8Bit));
  TEST_ASSERT_TRUE_MESSAGE(heap_caps_check_integrity_all(false),
                           "heap integrity check failed after frame workload");
  TEST_ASSERT_EQUAL_UINT8(0x00, frame[0]);
  TEST_ASSERT_EQUAL_UINT8(0x00, frame[slate::kFrameSize - 1]);
}

void testFrameResponseContract() {
  TEST_ASSERT_TRUE(slate::isValidFrameResponse(
      200, "application/vnd.slate.frame", slate::kFrameSize, "\"device\""));
  TEST_ASSERT_FALSE(slate::isValidFrameResponse(
      200, "application/vnd.slate.frame", slate::kFrameSize - 1,
      "\"device\""));
}

}  // namespace

void setUp() {}
void tearDown() {}

void setup() {
  delay(2000);
  UNITY_BEGIN();
  RUN_TEST(testFrameResponseContract);
  RUN_TEST(testRepeatedFrameIngestionKeepsHeapIntact);
  UNITY_END();
}

void loop() {}

#include "frame_ingestion.h"

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

struct RowSource {
  size_t rowsRead;
  size_t bytesBeforeEnd;
  uint8_t value;
};

size_t readRow(void *context, uint8_t *row, size_t rowSize) {
  RowSource *source = static_cast<RowSource *>(context);
  if (source->bytesBeforeEnd < rowSize) {
    const size_t available = source->bytesBeforeEnd;
    memset(row, source->value, available);
    source->bytesBeforeEnd = 0;
    return available;
  }
  source->bytesBeforeEnd -= rowSize;
  ++source->rowsRead;
  memset(row, source->value, rowSize);
  return rowSize;
}

void testResponseContractRejectsMalformedMetadata() {
  expect(slate::isValidFrameResponse(200, "application/vnd.slate.frame",
                                     slate::kFrameSize, "\"frame-1\""),
         "valid frame response metadata is accepted");
  expect(!slate::isValidFrameResponse(206, "application/vnd.slate.frame",
                                      slate::kFrameSize, "\"frame-1\""),
         "partial HTTP responses are rejected");
  expect(!slate::isValidFrameResponse(200, "text/plain", slate::kFrameSize,
                                      "\"frame-1\""),
         "unexpected media types are rejected");
  expect(!slate::isValidFrameResponse(200, "application/vnd.slate.frame",
                                      slate::kFrameSize - 1, "\"frame-1\""),
         "short frame lengths are rejected");
  expect(!slate::isValidFrameResponse(200, "application/vnd.slate.frame",
                                      slate::kFrameSize, ""),
         "missing ETags are rejected");
  expect(!slate::isValidFrameResponse(200, nullptr, slate::kFrameSize,
                                      "\"frame-1\""),
         "null content types are rejected");
}

void testCompleteFrameIngestionAndRepeatedAlternatingFrames() {
  uint8_t frame[slate::kFrameSize];
  slate::clearFrame(frame);

  for (uint8_t iteration = 0; iteration < 32; ++iteration) {
    const uint8_t value = (iteration & 1) ? 0x00 : 0xA5;
    RowSource source = {0, slate::kFrameSize, value};
    slate::FrameDiff diff;
    const bool ok = slate::ingestFrameRows(frame, true, diff, readRow, &source);
    expect(ok, "complete frames are accepted");
    expect(source.rowsRead == slate::kDisplayHeight,
           "every complete frame row is consumed");
    expect(frame[0] == value && frame[slate::kFrameSize - 1] == value,
           "complete frames replace the first and last framebuffer bytes");
    const slate::ChangedRegion region = diff.region();
    if (iteration == 0) {
      expect(region.changed && region.x == 0 && region.y == 0 &&
                 region.width == slate::kDisplayWidth &&
                 region.height == slate::kDisplayHeight,
             "first update reports the full changed region");
    } else {
      expect(region.changed, "alternating frames report changed pixels");
    }
  }
}

void testTruncatedFrameIsRejectedAndCanRecover() {
  uint8_t frame[slate::kFrameSize];
  slate::clearFrame(frame);
  RowSource truncated = {0, slate::kBytesPerRow * 2 + 40, 0x00};
  slate::FrameDiff partialDiff;
  expect(!slate::ingestFrameRows(frame, false, partialDiff, readRow,
                                 &truncated),
         "a frame ending partway through a row is rejected");
  expect(truncated.rowsRead == 2,
         "a truncated frame stops at the incomplete row");
  expect(frame[0] == 0x00 && frame[slate::kBytesPerRow] == 0x00,
         "fully received rows may be staged in the framebuffer");
  expect(frame[slate::kBytesPerRow * 2] == 0xFF,
         "the incomplete row is not copied into the framebuffer");

  RowSource valid = {0, slate::kFrameSize, 0x5A};
  slate::FrameDiff validDiff;
  expect(slate::ingestFrameRows(frame, false, validDiff, readRow, &valid),
         "a valid frame succeeds after a truncated frame");
  expect(frame[0] == 0x5A && frame[slate::kFrameSize - 1] == 0x5A,
         "recovery replaces the entire staged framebuffer");
}

void testInvalidReaderAndNullBufferFailSafely() {
  uint8_t frame[slate::kFrameSize];
  slate::clearFrame(frame);
  RowSource source = {0, slate::kFrameSize, 0x00};
  slate::FrameDiff diff;
  expect(!slate::ingestFrameRows(frame, false, diff, nullptr, &source),
         "a null row reader is rejected");
  expect(!slate::ingestFrameRows(nullptr, false, diff, readRow, &source),
         "a null framebuffer is rejected");
}

}  // namespace

int main() {
  testResponseContractRejectsMalformedMetadata();
  testCompleteFrameIngestionAndRepeatedAlternatingFrames();
  testTruncatedFrameIsRejectedAndCanRecover();
  testInvalidReaderAndNullBufferFailSafely();
  puts("Firmware memory tests passed");
  return 0;
}

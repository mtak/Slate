#include "frame_ingestion.h"

#include <string.h>

namespace slate {

bool isValidFrameResponse(int status, const char *contentType,
                          int contentLength, const char *etag) {
  return status == 200 && contentType != nullptr &&
         strcmp(contentType, "application/vnd.slate.frame") == 0 &&
         contentLength == static_cast<int>(kFrameSize) && etag != nullptr &&
         etag[0] != '\0';
}

bool ingestFrameRows(uint8_t *frame, bool comparePartial, FrameDiff &diff,
                     FrameRowReader readRow, void *context) {
  if (frame == nullptr || readRow == nullptr) return false;

  uint8_t incomingRow[kBytesPerRow];
  for (uint16_t row = 0; row < kDisplayHeight; ++row) {
    if (readRow(context, incomingRow, sizeof(incomingRow)) !=
        sizeof(incomingRow)) {
      return false;
    }
    if (comparePartial) {
      diff.compareAndReplaceRow(frame, row, incomingRow);
    } else {
      memcpy(frame + static_cast<size_t>(row) * kBytesPerRow, incomingRow,
             sizeof(incomingRow));
    }
  }
  return true;
}

}  // namespace slate

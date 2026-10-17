#pragma once

#include <stddef.h>
#include <stdint.h>

#include "frame.h"
#include "frame_diff.h"

namespace slate {

using FrameRowReader = size_t (*)(void *context, uint8_t *row,
                                  size_t rowSize);

bool isValidFrameResponse(int status, const char *contentType,
                          int contentLength, const char *etag);

bool ingestFrameRows(uint8_t *frame, bool comparePartial, FrameDiff &diff,
                     FrameRowReader readRow, void *context);

}  // namespace slate

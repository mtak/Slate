#pragma once

#include "frame.h"

namespace slate {

struct ChangedRegion {
  bool changed;
  uint16_t x;
  uint16_t y;
  uint16_t width;
  uint16_t height;
};

class FrameDiff {
 public:
  FrameDiff() : changed_(false), minByte_(kBytesPerRow), maxByte_(0),
                minRow_(kDisplayHeight), maxRow_(0) {}

  void record(uint16_t byteColumn, uint16_t row) {
    if (byteColumn >= kBytesPerRow || row >= kDisplayHeight) return;
    if (!changed_) {
      changed_ = true;
      minByte_ = maxByte_ = byteColumn;
      minRow_ = maxRow_ = row;
      return;
    }
    if (byteColumn < minByte_) minByte_ = byteColumn;
    if (byteColumn > maxByte_) maxByte_ = byteColumn;
    if (row < minRow_) minRow_ = row;
    if (row > maxRow_) maxRow_ = row;
  }

  ChangedRegion region() const {
    if (!changed_) return {false, 0, 0, 0, 0};
    return {true, static_cast<uint16_t>(minByte_ * 8), minRow_,
            static_cast<uint16_t>((maxByte_ - minByte_ + 1) * 8),
            static_cast<uint16_t>(maxRow_ - minRow_ + 1)};
  }

 private:
  bool changed_;
  uint16_t minByte_;
  uint16_t maxByte_;
  uint16_t minRow_;
  uint16_t maxRow_;
};

}  // namespace slate

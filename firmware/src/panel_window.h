#pragma once

#include <stdint.h>

namespace slate {
namespace panel {

struct CoordinateBytes {
  uint8_t high;
  uint8_t low;
};

// Partial-window ends are exclusive in Slate's frame bounds, while the
// controller expects an inclusive endpoint split into high and low bytes.
inline CoordinateBytes encodeInclusiveEnd(uint32_t exclusiveEnd) {
  const uint32_t inclusiveEnd = exclusiveEnd - 1;
  return {static_cast<uint8_t>((inclusiveEnd >> 8) & 0xFF),
          static_cast<uint8_t>(inclusiveEnd & 0xFF)};
}

}  // namespace panel
}  // namespace slate

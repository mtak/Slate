#pragma once

#include <stdint.h>

namespace slate {
constexpr uint32_t nextWifiRetryDelay(uint32_t currentDelayMs,
                                      uint32_t maximumDelayMs) {
  return currentDelayMs < maximumDelayMs / 2 ? currentDelayMs * 2
                                             : maximumDelayMs;
}
}  // namespace slate

#ifndef SLATE_REFRESH_POLICY_H
#define SLATE_REFRESH_POLICY_H

#include <stdint.h>

namespace slate {

enum class RefreshMode : uint8_t {
  Full,
  Partial,
};

constexpr RefreshMode chooseRefreshMode(bool haveDisplayedFrame,
                                       uint32_t partialRefreshesSinceFull,
                                       uint32_t partialRefreshesBeforeFull) {
  return haveDisplayedFrame && partialRefreshesBeforeFull > 0 &&
          partialRefreshesSinceFull < partialRefreshesBeforeFull
      ? RefreshMode::Partial
      : RefreshMode::Full;
}

constexpr uint32_t partialRefreshesAfterSuccess(RefreshMode mode,
                                                uint32_t partialRefreshesSinceFull) {
  return mode == RefreshMode::Partial ? partialRefreshesSinceFull + 1 : 0;
}

}  // namespace slate

#endif

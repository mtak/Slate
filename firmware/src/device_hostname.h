#ifndef SLATE_DEVICE_HOSTNAME_H
#define SLATE_DEVICE_HOSTNAME_H

#include <stddef.h>

namespace slate {

constexpr size_t kDeviceHostnameSize = 13;

inline bool makeDeviceHostname(const char *macAddress, char *hostname,
                               size_t hostnameSize) {
  if (macAddress == NULL || hostname == NULL ||
      hostnameSize < kDeviceHostnameSize) {
    return false;
  }

  char suffix[6];
  size_t suffixLength = 0;
  size_t hexDigitCount = 0;
  for (const char *cursor = macAddress; *cursor != '\0'; ++cursor) {
    const char value = *cursor;
    char uppercase = value;
    if (value >= 'a' && value <= 'f') uppercase = value - ('a' - 'A');
    const bool isHex = (uppercase >= '0' && uppercase <= '9') ||
                       (uppercase >= 'A' && uppercase <= 'F');
    if (!isHex) {
      if (value != ':' && value != '-') return false;
      continue;
    }
    ++hexDigitCount;
    if (suffixLength < sizeof(suffix)) {
      suffix[suffixLength++] = uppercase;
    } else {
      for (size_t i = 1; i < sizeof(suffix); ++i) suffix[i - 1] = suffix[i];
      suffix[sizeof(suffix) - 1] = uppercase;
    }
  }

  if (hexDigitCount != 12 || suffixLength != sizeof(suffix)) return false;
  const char prefix[] = "Slate-";
  for (size_t i = 0; i < sizeof(prefix) - 1; ++i) hostname[i] = prefix[i];
  for (size_t i = 0; i < sizeof(suffix); ++i)
    hostname[sizeof(prefix) - 1 + i] = suffix[i];
  hostname[kDeviceHostnameSize - 1] = '\0';
  return true;
}

}  // namespace slate

#endif

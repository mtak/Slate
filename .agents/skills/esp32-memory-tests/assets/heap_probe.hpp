#pragma once

// Optional helper for ESP32 Arduino and ESP-IDF projects.
// Requires ESP-IDF heap APIs exposed by the chosen framework version.
// Copy into the firmware project's include/ directory only if useful.

#include <cstddef>
#include <esp_heap_caps.h>

namespace esp32_memory_tests {

struct HeapSnapshot {
    size_t free_8bit;
    size_t largest_8bit;
    size_t minimum_8bit;
    size_t free_internal_8bit;
};

inline HeapSnapshot sample_heap() {
    return HeapSnapshot{
        heap_caps_get_free_size(MALLOC_CAP_8BIT),
        heap_caps_get_largest_free_block(MALLOC_CAP_8BIT),
        heap_caps_get_minimum_free_size(MALLOC_CAP_8BIT),
        heap_caps_get_free_size(MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL),
    };
}

inline bool heap_is_intact() {
    return heap_caps_check_integrity_all(false);
}

}  // namespace esp32_memory_tests

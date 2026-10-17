# ESP32 on-device memory tests

Use existing PlatformIO hardware environments and available `Arduino` or `espidf` APIs. Do not blindly create a new `board` definition or assume a single SDK version. Use `test_framework = unity` where suitable. Keep suite directory and `test_filter` consistent.

## Hardware-memory measurements

See `assets/heap_probe.hpp` for a helper built on `<esp_heap_caps.h>`. It captures:

- `free_8bit`: total available 8-bit allocatable RAM across matching heaps.
- `largest_8bit`: largest currently allocatable contiguous 8-bit block, **not** the same as total free RAM.
- `minimum_8bit`: lifetime watermark across matching heaps; it is not a before/after leak measurement.
- `free_internal_8bit`: free allocatable internal RAM meeting both capability flags, useful when PSRAM is present.
- `heap_caps_check_integrity_all(false)`: integrity check. It can be expensive and timing-sensitive; call at safe checkpoints, not inside latency-critical code.

Memory performance must be tested in a **steady state**. Start relevant services and warm up caches; sample after initialization, run repeated operations, release any owned resources, allow asynchronous queues/tasks to complete, then sample again. Distinguish deliberate retained caches from leaks. The helper is a measurement aid; the test must invoke the **real production feature** and assert its semantic correctness.

## Example test pattern (adapt, do not copy as final test)

```cpp
#include <unity.h>
#include "esp32_heap_probe.hpp"

void test_repeated_feature_lifecycle() {
    // Required: replace these comments with calls to an ACTUAL component.
    // Initialize/warm up it before the baseline.
    const auto before = esp32_memory_tests::sample_heap();

    for (int i = 0; i < 250; ++i) {
        // Create/start/use/stop/release the real component.
        // Verify the component behaves correctly after each cycle.
    }

    // Wait for any asynchronous deallocation WITHOUT arbitrary long sleeps.
    const auto after = esp32_memory_tests::sample_heap();
    TEST_ASSERT_TRUE(esp32_memory_tests::heap_is_intact());

    // Compare after.free_8bit to before.free_8bit only after deriving
    // the acceptable tolerance from observed baseline/known contracts.
    // Track after.largest_8bit separately for loss of a contiguous block.
    // This is a pattern, not a completed test: add actual assertions.
    (void)before;
    (void)after;
}
```

When copied into a real repository, the helper header must be on an include path (for example project `include/`), and the test must be registered with Unity using its target-appropriate runner. Arduino requires `setup()` and `loop()`; ESP-IDF can use `app_main()` (the actual repo might have its own runner).

## FreeRTOS task stacks

For running tasks, consider `uxTaskGetStackHighWaterMark(handle)` or `uxTaskGetStackHighWaterMark(nullptr)` when the SDK enables the API. Capture during/after the workload's deepest expected call path. Interpret units using the **installed SDK's** documentation: ESP-IDF ESP32 builds commonly report **bytes**, unlike vanilla FreeRTOS which commonly uses words; API documentation has varied between versions. Never multiply/divide blindly.

Report task identity, handle lifetime, raw reading, verified unit, and remaining headroom. No arbitrary universal minimum is valid across boards/tasks; use a justified budget (and note that a high-water mark is not a formal stack-safety proof).

## Tests to prioritize

1. Repeated feature init/use/deinit and reconnect/error/retry.
2. Invalid input causing early returns or partial initialization.
3. Multiple buffer sizes in alternating order; observe largest free block separately from total free bytes.
4. Allocation failure and recovery, where the allocation seam can be controlled (no global allocator override without careful review).
5. Task start/stop lifecycle, high-water mark and eventual resource reclamation.
6. Device-specific buffer constraints (e.g. `MALLOC_CAP_INTERNAL` / `MALLOC_CAP_DMA` / PSRAM) **only if used by the feature**.
7. Bounded soak/stability across many event cycles while yielding to watchdogs.

## Heap tracing and diagnostics

For a suspicious persistent free-heap trend, use ESP-IDF heap tracing when included/configurable in the project's actual SDK. Standalone tracing stores events in a bounded RAM buffer; host-based tracing often requires JTAG. Verify `CONFIG_HEAP_TRACING_DEST` and specific SDK API before changing config. Memory trends can indicate growth from active tasks, caches, logging, or fragmentation; they are not proof of leaked ownership.

Do not run target tests merely because `pio test` is available: physical flashing/uploading requires an identified board and the user's authorization. A successful firmware build is **BUILD ONLY**, not PASS.

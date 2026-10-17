# Native PlatformIO tests with sanitizers

Use this when the subject is **host-compilable** C++ code. This is a configuration pattern, not a drop-in replacement for a repository's `platformio.ini`.

## Example environment

```ini
[env:native]
platform = native
test_framework = unity
# This name should match the actual suite directory below test/.
test_filter = test_memory_native
build_flags =
    -std=gnu++17
    -g
    -O1
    -fno-omit-frame-pointer
    -fsanitize=address,undefined
# Do not enable test_build_src globally by default.
```

- Remove or adapt `-std=gnu++17` if the repository uses a different C++ version. GCC and Clang both accept these sanitizer flags on supported Linux hosts; confirm compilation and linking with the actual platform/toolchain.
- `build_flags` usually propagate to the linker in PlatformIO. Confirm the final test binary is sanitizer-linked, not merely sanitizer-compiled.
- Prefer reusable components under `lib/`, or select/move only the portable implementation units. PlatformIO normally excludes `src/` while testing. Blindly setting `test_build_src = yes` often causes duplicate firmware entry points or non-native includes.
- If dependencies or logging headers are embedded-only, provide *minimal behaviorally accurate* adapters, keep test code separate from production and test the real implementation. Never reimplement the function being tested inside a mock.
- Match test suite directories to `test_filter`; do not allow the native environment to accidentally compile embedded test sources.

## Meaningful Unity test structure

In `test/test_memory_native/test_main.cpp`, adapt to the project's **real component** (the following names are illustrative, not real APIs):

```cpp
#include <unity.h>
// #include <YourProductionComponent.h>

void setUp() {}
void tearDown() {}

void test_parse_rejects_truncated_payload_without_overread() {
    // Instantiate the ACTUAL decoder and pass a truncated input.
    // Assert its documented error result and unchanged/correct output.
    // With ASan/UBSan enabled, invalid access should fail execution.
    TEST_IGNORE_MESSAGE("Replace this scaffold with a real production-component test");
}

int main(int, char**) {
    UNITY_BEGIN();
    RUN_TEST(test_parse_rejects_truncated_payload_without_overread);
    return UNITY_END();
}
```

**Do not copy this scaffold as final coverage**: `TEST_IGNORE` is deliberately non-passing and must be replaced by a real assertion. Never count the ignored test as passing.

## Run

```bash
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
pio test -e native -f test_memory_native
```

If leak detection is unsupported or unavailable, state that explicitly. ASan catches many out-of-bounds and use-after-free errors, UBSan catches selected undefined behavior, and LSan identifies reachable/unreachable allocation leaks depending on runtime; **none** can guarantee absence of every memory bug.

## Test generation checklist

- Exercise realistic lifetime: construction, copy/move if applicable, repeated use, cleanup, destruction.
- Test boundary lengths, malformed input, truncated buffers, oversized length fields, zero length, NULL/nullptr where permitted.
- Check error branches: failed allocation or incomplete initialization must not leak partially constructed state.
- Use bounded randomized/fuzz-derived inputs with fixed seeds if useful. Do not require large dependency additions without approval.
- If code is tightly bound to hardware, prefer testing its platform-independent logic natively and cover the actual behavior separately on device.

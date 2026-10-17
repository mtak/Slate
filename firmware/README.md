# Firmware build and flash

The firmware targets the ESP32 DevKit V1 (`esp32dev`) with the Arduino
framework through PlatformIO. The PlatformIO CLI is pinned in
`requirements.txt`; the Espressif32 platform (including its framework and
compiler toolchain) is pinned in `platformio.ini`.

For the clean-checkout setup through physical display verification, follow the
[setup and commissioning guide](../docs/getting-started.md). This page keeps the
firmware-specific commands and configuration details.

## Setup

From this directory, run:

```sh
./scripts/setup.sh
cp include/slate_config.h.example include/slate_config.h
```

Edit `include/slate_config.h` and set the Wi-Fi credentials, HTTPS server base
URL, random device token, and PEM root CA. The file is included by the firmware
and ignored by Git. `SLATE_TLS_VERIFY` defaults to `true`; set it to `false`
only to test a self-signed certificate locally. The device sends the token in
an Authorization header and never includes it in its URL or serial output.

At boot, firmware attempts to connect as a Wi-Fi station and retries forever
with a delay that doubles from 1 second to a 30-second cap. The main loop
detects a dropped connection and starts the same retry sequence. A 60-second
ESP32 task watchdog restarts the device if the application stops making
progress. The firmware feeds it during connection waits and once per healthy
main-loop iteration. Check the serial monitor for connection and watchdog
messages when diagnosing a device.

## Build and flash

Run the host-side firmware checks locally with one command:

```sh
make test
```

This runs the existing frame tests and a separate ASan/UBSan memory suite
against the production frame renderer and frame-ingestion code. It uses the
system C++ compiler and does not require PlatformIO, an ESP32, an e-paper panel,
network access, or credentials. Leak detection is enabled where supported by
the host sanitizer runtime. Pull requests changing anything under firmware/
run this check in GitHub Actions.

The target memory test can be compiled in CI without uploading it to hardware:

```sh
make setup
make build-memory-test
```

This is a compile-only check. To execute the Unity memory test on a connected
ESP32, use the test environment and select its upload and serial ports:

```sh
./.venv/bin/pio test -e slate_esp32_memory_test \
  --upload-port /dev/ttyUSB0 --test-port /dev/ttyUSB0
```

The device test warms the ingestion path with three frames, then processes 64
alternating full-frame updates. It reports free 8-bit heap and largest free
8-bit block before and after the measured workload, and checks heap integrity.
The ingestion component itself uses a 100-byte row buffer and does not allocate
from the heap. These initial metrics are diagnostic; no byte threshold is set
until stable measurements are collected on the target setup. They do not cover
HTTPClient or TLS allocations because the test supplies rows through a local
reader seam and does not make network requests. The normal GitHub-hosted CI
builds this suite but does not run it on an ESP32.

```sh
make build
make upload PORT=/dev/ttyUSB0
make monitor PORT=/dev/ttyUSB0
make clean
```

On macOS, the serial port is commonly `/dev/cu.usbserial-*` or
`/dev/cu.SLAB_USBtoUART`; on Windows, use the device's `COM` port. Find the
correct port before flashing. `upload` and `monitor` require `PORT` so the
command cannot silently select a different attached device. Close the serial
monitor before uploading.

`make setup` runs the setup script. It creates a local `.venv` and installs the
pinned PlatformIO CLI. The first build downloads the pinned ESP32 platform and
toolchain into `.platformio/`; build outputs go into `.pio/`. Both directories
are ignored by Git.

The firmware displays the authenticated frame from the configured server. The
default `slate_esp32` environment uses Waveshare's `7.5V2` profile. The
`slate_esp32_v2_old` environment selects `7.5V2_old`, a tested alternative for
the documented panel. Both profiles use the same 800×480 frame contract and
busy-signal timeout. The first update is a full refresh, followed by the
configured partial/full cadence.

### Optional task-watchdog hardware demo

Build and flash the explicitly opt-in `slate_esp32_watchdog_demo` environment:

```sh
./.venv/bin/pio run -e slate_esp32_watchdog_demo
./.venv/bin/pio run -e slate_esp32_watchdog_demo --target upload --upload-port /dev/ttyUSB0
make monitor PORT=/dev/ttyUSB0
```

After opening the serial monitor, send `g` to arm the demo. This gate lets you
be ready to watch before the deliberate stall begins. The firmware prints a
15-second countdown, then stops feeding the 60-second task watchdog. Leave the
monitor connected through the automatic reset. After the task-watchdog reset,
the demo build recognizes the reset and continues normal startup without
repeating the stall; with local Wi-Fi configuration it should then report
`Wi-Fi connected`. Capture the gate, countdown, watchdog timeout/reset, and
successful connection. Sanitize logs before sharing them.

The normal `slate_esp32` environment does not define `SLATE_WATCHDOG_DEMO` and
cannot start the intentional stall. After capturing the demo, flash the normal
build again:

```sh
make upload PORT=/dev/ttyUSB0
make monitor PORT=/dev/ttyUSB0
```

This hardware check requires an attached ESP32 and configured local Wi-Fi; it
cannot be completed by the hardware-independent tests.

Build both frame-client profiles and the panel diagnostic profiles:

```sh
./.venv/bin/pio run -e slate_esp32
./.venv/bin/pio run -e slate_esp32_v2_old
./.venv/bin/pio run -e slate_esp32_partial_diag
./.venv/bin/pio run -e slate_esp32_partial_diag_v2_old
./.venv/bin/pio run -e slate_esp32_partial_diff_diag
./.venv/bin/pio run -e slate_esp32_partial_diff_diag_v2_old
```

The one-shot panel diagnostic environments each perform a full-frame baseline,
three 160×80 partial-window changes, and a final full refresh. To flash a
diagnostic, use `pio run -e <diagnostic-env> --target upload
--upload-port /dev/ttyUSB0`; then open the serial monitor. Close the monitor
before uploading another build. Record the profile, visible result, and serial
busy status. The regular `slate_esp32` and `slate_esp32_v2_old` environments
run the configured network frame client.

The `partial_diff_diag` environments exercise the same in-place row comparison
and strided partial-window sender used by the frame client. They display a
baseline, change two separated 24×16 black marks, compute the 104×16 bounding
window between them, then pause on the resulting image for visual inspection.
Before the partial update, they print an `ARMED` message and wait for the host
to send `g`, so the operator can prepare to watch. The serial log reports the
detected bounds and busy timeout status. The panel remains on the test image
until reset or another firmware is flashed; after inspection, run a full
refresh to clear residual ghosting.

Each profile has its own panel initialization and partial-refresh sequence.
Panel profile selection and hardware validation are recorded in
[hardware notes](../docs/hardware.md).

The device requests the authenticated v1 frame immediately at startup and then
polls at `SLATE_POLL_INTERVAL_SECONDS` (default 60). Set
`SLATE_MIN_REFRESH_INTERVAL_SECONDS` (default 60) to limit the interval between
panel updates. `SLATE_PARTIAL_REFRESHES_BEFORE_FULL` (default 2) controls how
many partial updates occur between full refreshes. The first displayed frame
is always a full refresh; then the firmware performs the configured number of
partial refreshes before each full refresh. Set it to `0` to disable partial
refreshes. Partial refreshes can leave ghosting, so the periodic full refresh
clears residual images. The server always returns the complete 48,000-byte
frame. During a partial update, firmware reads the new image one 100-byte row
at a time, compares each incoming byte with the existing framebuffer, and
overwrites it in place. It tracks the smallest rectangle containing all
changed bytes; its horizontal edges align to byte boundaries (eight pixels).
The partial display transfer reads rows from the full-frame stride, so no crop
buffer or second framebuffer is needed. Only the one 48,000-byte framebuffer
and a 100-byte scanline scratch buffer are used.

The client validates the frame media type and exact payload length, sends the
latest server ETag on later polls, skips 304 responses and unchanged frames,
and keeps a validated pending frame until the refresh interval permits an
update. A partial comparison is used only when the framebuffer is known to
match the displayed panel image. An interrupted download or failed panel
operation makes the next attempt a full refresh. The panel uses the normal
two-partials/one-full cadence. The V2 and V2-old panel profiles have separate
partial-refresh controller sequences; verify behavior on the attached panel.
Partial refreshes may flash within the updated window. A physical HTTPS test
requires Wi-Fi, a reachable HTTPS endpoint, and a valid root CA in the ignored
config file.

See [public repository hygiene](../docs/architecture.md#public-repository-hygiene)
for the project's rules on local configuration and secrets.

For network, certificate, frame, and display symptoms, see the
[troubleshooting guide](../docs/troubleshooting.md).

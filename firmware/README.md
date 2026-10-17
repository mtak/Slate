# Firmware build and flash

The firmware targets the ESP32 DevKit V1 (`esp32dev`) with the Arduino
framework through PlatformIO. The PlatformIO CLI is pinned in
`requirements.txt`; the Espressif32 platform (including its framework and
compiler toolchain) is pinned in `platformio.ini`.

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

Run the hardware-independent firmware tests locally with one command:

```sh
make test
```

This target uses the system C++ compiler and does not require PlatformIO, an
ESP32, an e-paper panel, network access, or credentials. It tests the frame
format and diagnostic renderer. Pull requests run the same command in GitHub
Actions.

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

The default `slate_esp32` environment runs the frame client with Waveshare's
`7.5V2` profile; `slate_esp32_v2_old` selects `7.5V2_old`. Both panel profiles
use the same 800×480 frame contract and busy-signal timeout. The initial frame
is a full refresh, followed by the configured partial/full cadence.

Build both frame-client profiles and both one-shot diagnostic profiles:

```sh
./.venv/bin/pio run -e slate_esp32
./.venv/bin/pio run -e slate_esp32_v2_old
./.venv/bin/pio run -e slate_esp32_partial_diag
./.venv/bin/pio run -e slate_esp32_partial_diag_v2_old
```

The one-shot panel diagnostic environments each perform a full-frame baseline,
three 160×80 partial-window changes, and a final full refresh. To flash a
diagnostic, use `pio run -e <diagnostic-env> --target upload
--upload-port /dev/ttyUSB0`; then open the serial monitor. Close the monitor
before uploading another build. Record the profile, visible result, and serial
busy status. The regular `slate_esp32` and `slate_esp32_v2_old` environments
run the configured network frame client.
Panel profile selection and attached-device results are tracked in
[hardware notes](../docs/hardware.md).

The device requests the authenticated v1 frame immediately at startup and then
polls at `SLATE_POLL_INTERVAL_SECONDS` (default 60). Set
`SLATE_MIN_REFRESH_INTERVAL_SECONDS` (default 60) to limit the interval between
panel updates. `SLATE_PARTIAL_REFRESHES_BEFORE_FULL` (default 2) controls how
many partial updates occur between full refreshes. The first displayed frame
is always a full refresh; then the firmware performs the configured number of
partial refreshes before each full refresh. Set it to `0` to disable partial
refreshes. Partial refreshes can leave ghosting, so the periodic full refresh
clears residual images. For a partial update, the client sends the ETag of the
displayed frame to the server. When that frame is still in the server's recent
history, the server returns a packed, byte-aligned crop covering the pixels
that changed; otherwise it returns the full frame as a safe fallback. The
ESP32 stores either response in its existing 48,000-byte frame buffer, so it
does not need a second full framebuffer. A history miss makes the client use a
full panel refresh and restart the partial counter; a delta is sent to the
panel using the normal 2-partials/1-full policy.

The client validates the media type, v1 format version, full 800×480 display
dimensions, region bounds and byte alignment, and the expected payload length
(48,000 bytes for a full frame or `Region-Width / 8 × Region-Height` for a
delta) before accepting an update. It sends the latest server ETag on later
polls, skips 304 responses and identical payloads, and keeps a validated
pending update until the refresh interval permits an update.
Transient connection or response failures leave the current panel image alone;
the next poll retries the request. The V2 and V2-old panel profiles have
separate partial-refresh driver sequences; verify partial-refresh behavior on
the attached panel. A physical HTTPS test requires Wi-Fi, a reachable HTTPS
endpoint, and a valid root CA in the ignored config file.
See [public repository hygiene](../docs/architecture.md#public-repository-hygiene)
for the project's rules on local configuration and secrets.

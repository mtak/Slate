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

The firmware displays the authenticated frame from the configured server. The
default `slate_esp32` environment uses Waveshare's `7.5V2` profile. The
`slate_esp32_v2_old` environment selects `7.5V2_old`, a tested alternative for
the documented panel. To build and flash the alternate profile:

```sh
make build
make upload PORT=/dev/ttyUSB0
make monitor PORT=/dev/ttyUSB0
./.venv/bin/pio run -e slate_esp32_v2_old
./.venv/bin/pio run -e slate_esp32_v2_old --target upload --upload-port /dev/ttyUSB0
```

Each profile has its own panel initialization and partial-refresh sequence.
Panel profile selection and hardware validation are recorded in the
[hardware notes](../docs/hardware.md).

The device requests the authenticated v1 frame immediately at startup and then
polls at `SLATE_POLL_INTERVAL_SECONDS` (default 60). Set
`SLATE_MIN_REFRESH_INTERVAL_SECONDS` (default 60) to limit the interval between
panel updates. `SLATE_PARTIAL_REFRESHES_BEFORE_FULL` (default 2) controls how
many partial updates occur between full refreshes. The first displayed frame
is always a full refresh; then the firmware performs the configured number of
partial refreshes before each full refresh. Set it to `0` to disable partial
refreshes. Partial refreshes can leave ghosting, so the periodic full refresh
clears residual images. Their visible behavior depends on panel revision; on
the attached V2 panel, partial and full updates still flashed similarly.

The client validates the media type, v1 format version, 800×480 dimensions, and
48,000-byte payload before it can replace the displayed frame. It sends the
server ETag on later polls, skips 304 responses and identical payloads, and
keeps a validated pending frame until the refresh interval permits an update.
Transient connection or response failures leave the current panel image alone;
the next poll retries the request. The V2 and V2-old panel profiles have
separate partial-refresh driver sequences; verify partial-refresh behavior on
the attached panel. A physical HTTPS test requires Wi-Fi, a reachable HTTPS
endpoint, and a valid root CA in the ignored config file.
See [public repository hygiene](../docs/architecture.md#public-repository-hygiene)
for the project's rules on local configuration and secrets.

For network, certificate, frame, and display symptoms, see the
[troubleshooting guide](../docs/troubleshooting.md).

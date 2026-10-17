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

Edit `include/slate_config.h` for local device settings when a later firmware
feature requires them. The current bootstrap does not use this file. Keep real
Wi-Fi passwords and server tokens in the local file; it is ignored by Git.
Never put third-party integration credentials in firmware.

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

The current sketch runs a one-shot display-profile diagnostic at boot. The
default `slate_esp32` environment uses Waveshare's `7.5V2` profile; the
`slate_esp32_v2_old` environment uses `7.5V2_old`. Both draw a labeled
800×480 test pattern and time out rather than waiting forever for the panel's
busy signal.

Build and flash each candidate separately:

```sh
make build
make upload PORT=/dev/ttyUSB0
make monitor PORT=/dev/ttyUSB0
./.venv/bin/pio run -e slate_esp32_v2_old
./.venv/bin/pio run -e slate_esp32_v2_old --target upload --upload-port /dev/ttyUSB0
```

The e-paper performs a full refresh for each diagnostic. Record the profile,
firmware revision, orientation, edge clipping, visible pattern/text, and whether
the serial monitor reports a busy timeout. Do not infer a successful profile
from compilation alone; the physical result decides which profile is selected.
Panel profile selection is tracked in [hardware notes](../docs/hardware.md).

Networking and frame-fetch behavior remain separate work.
See [public repository hygiene](../docs/architecture.md#public-repository-hygiene)
for the project's rules on local configuration and secrets.

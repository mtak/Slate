# Slate

Slate is an ESP32 driven, 800×480 monochrome e-paper information display. A
server combines data from independent providers, renders a frame, and serves it
to the display. The device checks for changes and updates the panel when needed.

The repository contains the firmware and server application. Production
deployment is environment-specific; this public repository documents the
application requirements and local development workflow without relying on a
particular home network or deployment platform.

## Get started

- [Setup and commissioning](docs/getting-started.md) — run a local preview,
  configure a device, and verify the full display path.
- [Troubleshooting](docs/troubleshooting.md) — resolve common setup and display
  problems.

## Project documentation

- [Server guide](server/README.md) — run the renderer, edit its sample layout,
  and add data providers.
- [Provider guides](docs/providers/README.md) — configure the sample and Google
  Calendar iCal providers.
- [Firmware guide](firmware/README.md) — configure, build, flash, and monitor
  the ESP32.
- [Architecture and frame format](docs/architecture.md) — service boundaries,
  image contract, authentication, and refresh behavior.
- [Hardware notes](docs/hardware.md) and [wiring](docs/wiring.jpeg) — validated
  board settings, wiring, and display profile.

## Hardware

The tested setup uses an ESP32 DevKit V1, Waveshare e-Paper Driver HAT Rev 2.2,
and a 7.5-inch black-and-white 800×480 panel. The working wiring and HAT
settings are recorded in the hardware notes.

## Public repository safety

Examples use placeholders. Keep Wi-Fi credentials, device tokens, certificates,
household data, and deployment-specific configuration in ignored local files or
private deployment configuration. Review changes before publishing them.

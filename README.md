# Slate

Slate is a kitchen-mounted home information display. A server gathers data from
pluggable sources, renders a monochrome 800×480 image, and serves it to an ESP32.
The ESP32 polls periodically and refreshes the e-paper only when the image has
changed.

Slate is intended to become a public project. Keep the repository safe and
presentable for public readers: never commit credentials, access tokens,
private household data, or unredacted configuration. Use ignored local
configuration files and sanitized examples.

## Hardware

- ESP32 (ESP-WROOM-32) on a DevKit V1
- Waveshare e-Paper Driver HAT Rev 2.2, configured for 0.47R and 4-wire SPI
- Waveshare 7.5-inch black-and-white display, 800×480
- Wiring: [docs/wiring.jpeg](docs/wiring.jpeg)

The wiring and HAT settings are validated. The panel's precise revision is not
identified; visible markings are `DEP607508NU790F30` and
`N2104P-0117-01-10`. Confirm a compatible initialization sequence during the
diagnostic display bring-up rather than changing the working wiring.

## Repository

- [firmware/](firmware/) — ESP32 client and device build/flash workflow
- [server/](server/) — renderer, integrations, and image endpoint
- [docs/project-outline.md](docs/project-outline.md) — initial scope and design
- [docs/architecture.md](docs/architecture.md) — image delivery and security
- [docs/hardware.md](docs/hardware.md) — confirmed wiring/settings and panel notes
- [docs/issue-backlog.md](docs/issue-backlog.md) — ordered GitHub issue plan

## First milestone

Bring up the display from a fresh firmware build, connect to Wi-Fi, fetch a
known test image from the server, and prove that unchanged images do not cause
unnecessary panel refreshes. Then add the first useful layout and integration.

## Status

This repository is at project bootstrap. See the [GitHub issues](https://github.com/mtak/Slate/issues)
for the implementation sequence. Hardware wiring is documented in
[`docs/wiring.jpeg`](docs/wiring.jpeg).

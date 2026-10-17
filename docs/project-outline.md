# Slate project outline

## Goal

Restore a dependable kitchen display using the existing ESP32 and Waveshare
hardware, then make it useful for household information such as a shared Google
Calendar and, later, home automation metrics and other sources.

Slate is intended to become a public repository. Committed documentation,
examples, and configuration must be clear to public readers and contain no
secrets, private household data, or private network configuration.

The existing wiring is validated. The HAT is set to 0.47R display configuration
and 4-line SPI. The exact panel revision is not identified; validate the driver
initialization profile with a diagnostic update.

## First release

1. Build and flash firmware through a scripted, repeatable local workflow.
2. Initialize the known 800×480 monochrome panel and show a diagnostic image.
3. Connect the ESP32 to Wi-Fi and fetch a rendered image from the server.
4. Poll on a configurable interval (initial target: 60 seconds).
5. Avoid a panel refresh when the fetched image has not changed.
6. Run a Python renderer and image endpoint with Docker Compose.
7. Allow the display layout and refresh period to be edited without changing
   integration code.
8. Protect image delivery with HTTPS and a per-device credential.

## Design constraints

- The panel is 800×480, black and white, and should not be refreshed more often
  than its supported rate (the supplied hardware description gives 0.2 Hz).
- The ESP32 should not contain service-specific integration logic.
- The server should remain useful for development by exposing the current image
  for browser preview.
- The initial system is for one household and one display; avoid unnecessary
  service decomposition or complex deployment machinery.
- Firmware changes that add or alter behavior should include deterministic,
  hardware-independent regression tests for that behavior. Keep hardware access
  behind small seams so core behavior can run in local tests and pull request
  CI without an ESP32, display, network service, credentials, or timing waits.

## Initial technology direction

- Firmware: ESP-IDF based project, built and flashed through a checked-in
  wrapper/Makefile. Keep Wi-Fi, TLS, polling, and display control explicit.
- Server: Python, Pillow for raster rendering, and a small HTTP API. Keep data
  sources behind simple provider interfaces and use a YAML/JSON layout
  description for positions and content blocks.
- Deployment: Docker Compose with configurable render cadence and a persistent
  configuration/secrets boundary.
- Image delivery: a compact 1-bit monochrome payload with a versioned header or
  documented format, HTTP ETag support, and conditional polling. Use HTTPS with
  certificate validation and a device token; never put tokens in the image URL.

These are starting choices, not requirements. Revisit them if a small hardware
prototype shows a practical limitation.

## Out of scope for first display bring-up

- Google OAuth and calendar presentation
- Home automation metrics integration
- Remote administration or a public-facing service
- Partial refresh optimization

These can follow once the end-to-end image path works.

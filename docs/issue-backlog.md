# Initial GitHub issue sequence

These issues define the first end-to-end milestone and the first useful content.
The GitHub tracker has been initialized with the following ordered issues:

1. [#1 Identify the display's compatible driver profile](https://github.com/mtak/Slate/issues/1) — use the known 800×480 specifications and a diagnostic update to select the compatible initialization sequence. Wiring, 0.47R, and 4-line SPI are already validated.
2. [#2 Bootstrap ESP32 firmware build and flash workflow](https://github.com/mtak/Slate/issues/2) — choose/pin the
   framework and toolchain; provide scripted setup, Makefile targets, and
   configuration examples.
3. [#3 Drive the e-paper panel with a diagnostic image](https://github.com/mtak/Slate/issues/3) — bring up 4-wire SPI,
   initialize the compatible panel profile, and show test patterns/text.
4. [#4 Add Wi-Fi configuration and watchdog recovery](https://github.com/mtak/Slate/issues/4) — support local secrets,
   reconnect behavior, and a hardware task watchdog.
5. [#5 Define the monochrome frame format and server preview](https://github.com/mtak/Slate/issues/5) — settle bit order,
   orientation, encoding, and browser preview behavior.
6. [#6 Build the modular Python renderer and editable layout](https://github.com/mtak/Slate/issues/6) — add provider
   interfaces, a sample provider, configurable layout, and 800×480 rendering.
7. [#7 Serve the latest frame with configurable refresh and ETags](https://github.com/mtak/Slate/issues/7) — add the
   image endpoint, conditional requests, browser preview, and Compose service.
8. [#8 Add HTTPS and device-token authentication](https://github.com/mtak/Slate/issues/8) — configure deployment TLS,
   validate certificates on-device, and keep the device credential out of URLs.
9. [#9 Fetch frames from the ESP32 and refresh only on changes](https://github.com/mtak/Slate/issues/9) — implement
   polling, frame validation, ETag/hash comparison, rate limiting, and retries.
10. [#10 Document local deployment and display commissioning](https://github.com/mtak/Slate/issues/10) — document setup,
    secrets, flashing, network access, troubleshooting, and recovery.
11. [#11 Add Google Calendar as the first household data provider](https://github.com/mtak/Slate/issues/11) — retrieve the
    shared calendar data and render upcoming events in the editable layout.
12. [#12 Keep the public repository presentable and free of sensitive data](https://github.com/mtak/Slate/issues/12) — review public readability and check committed docs, examples, and files for secrets or private household information.

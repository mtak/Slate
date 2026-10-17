# Firmware

The firmware connects the ESP32 DevKit V1 to Wi-Fi, downloads the current
monochrome frame from the Slate server, and updates the Waveshare e-paper panel
when the frame changes.

The project is being bootstrapped. See GitHub issues [#1](https://github.com/mtak/Slate/issues/1),
[#2](https://github.com/mtak/Slate/issues/2),
[#3](https://github.com/mtak/Slate/issues/3), and
[#4](https://github.com/mtak/Slate/issues/4) for driver-profile identification,
build/flash setup, panel bring-up, Wi-Fi, and watchdog work. The initial
framework choice and commands will be recorded as part of issue #2.

This is intended to be a public repository; follow the [public repository
hygiene notes](../docs/architecture.md#public-repository-hygiene). Device
configuration must be local and ignored by Git. Firmware must validate the
server certificate and must not contain any integration-service credentials.

# esp32-memory-tests

Reusable **Codex agent skill** that instructs Codex to generate meaningful PlatformIO C++ memory-safety and memory-resource tests for ESP32 projects. It is an instruction bundle, not a standalone test runner or a prebuilt test suite for arbitrary firmware.

## Install

Unzip `esp32-memory-tests.zip` into your personal skills directory:

```bash
mkdir -p ~/.agents/skills
unzip esp32-memory-tests.zip -d ~/.agents/skills/
```

Or install at repository scope instead:

```bash
mkdir -p .agents/skills
unzip esp32-memory-tests.zip -d .agents/skills/
```

You should then have `.agents/skills/esp32-memory-tests/SKILL.md` or `~/.agents/skills/esp32-memory-tests/SKILL.md`. If the skill is not discovered by the Codex instance you already have open, restart that instance.

## Invoke

Within the PlatformIO project:

> Use $esp32-memory-tests to inspect the project and create meaningful native sanitizer and ESP32 hardware memory tests. Run native tests, but do not flash the ESP32. Report test coverage, actual results and remaining gaps.

To exercise hardware tests, explicitly approve uploading to the connected board and provide/identify the existing PlatformIO environment and port.

## Contents

- `SKILL.md` – rules and full code-generation workflow.
- `references/native-testing.md` – portable code, ASan/UBSan/LSan and PlatformIO setup.
- `references/device-testing.md` – real board heap/stack tests and soak coverage.
- `references/quality-gates.md` – thresholds, evidence and report format.
- `assets/heap_probe.hpp` – optional ESP-IDF memory metrics helper.

## Limitations

Native tests only exercise portable code paths. Device tests require a physical ESP32 to produce real hardware evidence. Without access to the target project or board, the skill itself cannot generate project-specific tests or claim they pass.

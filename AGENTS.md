# Project guidance

Slate is a hobby home information display built around an ESP32 DevKit V1,
Waveshare e-Paper Driver HAT Rev 2.2, and an 800×480 black-and-white 7.5-inch
e-paper panel.

Slate is intended to become a public repository. Keep committed content
presentable to new contributors and safe for anyone to read. Never commit
credentials, tokens, private household data, private network details, or
machine-specific configuration. Use sanitized examples and ignored local
configuration files. Review new files and diffs for sensitive information
before committing.

## Repository layout

- `firmware/` contains the ESP32 firmware and its build/flash workflow.
- `server/` contains the image renderer, data integrations, and HTTP service.
- `docs/` contains wiring, architecture, and operational notes.

## Development expectations

- Keep the firmware small: it fetches a rendered image, checks whether it has
  changed, and updates the panel only when needed.
- Keep integrations on the server and implement them as independent modules.
- Keep secrets out of Git. Use local environment files that are ignored by Git
  and document required variables in examples.
- Preserve the display's 800×480, monochrome constraints in image contracts.
- Prefer straightforward hobby-scale solutions over infrastructure that needs
  ongoing maintenance.
- The existing wiring is validated. The HAT is configured for 0.47R display
  selection and 4-line SPI. The panel's exact revision is unknown; validate the
  driver initialization profile with a diagnostic update.
- Keep public-facing documentation clear and free of private household details.

## Validation

- Use Playwright MCP for browser interactions when validating local web previews;
  capture a screenshot when a visual artifact helps review the result.
- Firmware changes should at least compile; hardware/display changes should be
  checked on the attached device when practical.
- Server changes should be checked by rendering a sample image and viewing it
  in a browser.
- Document commands and any hardware-specific validation that cannot run in CI.

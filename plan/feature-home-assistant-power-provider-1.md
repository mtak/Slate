---
goal: Add an optional Home Assistant power provider and display tile
version: 1.0
date_created: 2026-10-19
last_updated: 2026-10-19
owner: Slate contributors
status: 'Completed'
tags: [feature, provider, home-assistant]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

This plan records the Home Assistant integration that reads one configured power sensor and displays its current reading in watts on Slate.

## 1. Requirements & Constraints

- **REQ-001**: Integrate as an optional independent server provider without replacing the existing primary provider.
- **REQ-002**: Convert supported `W` and `kW` values to whole watts and show unavailable readings clearly.
- **SEC-001**: Read the bearer token from environment configuration and avoid logging credentials or private URLs.
- **CON-001**: Preserve the 800×480 monochrome display contract.
- **PAT-001**: Follow the existing `get_data()` provider pattern and editable JSON layout.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Implement and document the Home Assistant power tile.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Add the optional Home Assistant REST state provider in `server/providers.py`. | ✅ | 2026-10-19 |
| TASK-002 | Merge power data in `server/app.py` and render a configurable power tile in `server/renderer.py` and `server/layout.json`. | ✅ | 2026-10-19 |
| TASK-003 | Pass sanitized optional environment settings through Compose and document setup in provider guides. | ✅ | 2026-10-19 |

## 3. Alternatives

- **ALT-001**: Replace the primary data provider with Home Assistant; not chosen because power data should compose with existing calendar or sample data.
- **ALT-002**: Add a new HTTP client dependency; not chosen because the server already uses `requests`.

## 4. Dependencies

- **DEP-001**: Home Assistant REST API and a configured power sensor using `W` or `kW`.
- **DEP-002**: Existing `requests` dependency.

## 5. Files

- **FILE-001**: `server/providers.py` — Home Assistant state retrieval and value normalization.
- **FILE-002**: `server/app.py` — optional provider composition.
- **FILE-003**: `server/renderer.py` and `server/layout.json` — power tile implementation and default placement.
- **FILE-004**: `compose.yaml`, `.env.example`, `server/README.md`, and `docs/providers/` — configuration and usage documentation.

## 6. Testing

- **TEST-001**: Verify Python modules compile and render a sample frame with the configured default layout.
- **TEST-002**: Hardware display and live Home Assistant connectivity require the user's Home Assistant instance and physical display.

## 7. Risks & Assumptions

- **RISK-001**: Sending a bearer token over plain HTTP exposes it to observers on that network; HTTPS is recommended.
- **ASSUMPTION-001**: One sensor entity is sufficient for the initial feature.
- **ASSUMPTION-002**: Unsupported units and network/API failures should result in an “Unavailable” tile instead of a failed frame.

## 8. Related Specifications / Further Reading

- [Issue #51](https://github.com/mtak/Slate/issues/51)
- [Home Assistant power provider guide](../docs/providers/home-assistant-power.md)

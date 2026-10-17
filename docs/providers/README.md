# Data providers

Slate providers fetch or supply data for the server renderer. The server uses
sample data when `SLATE_CALENDAR_ICAL_URL` is empty and Google Calendar iCal
when that URL is configured.

| Provider | Setup guide | Credentials |
| --- | --- | --- |
| Sample data | [Sample provider](sample.md) | None |
| Current date | [Current date provider](current-date.md) | None |
| Daily affirmation | [Daily affirmation provider](daily-affirmation.md) | None |
| Google Calendar iCal feed | [Google Calendar iCal feed](google-calendar-ical.md) | Secret HTTPS feed URL in local `.env` |

Every provider returns named values through `get_data()`. The renderer uses
these values with the editable [`server/layout.json`](../../server/layout.json)
layout. Provider integrations belong on the server; the ESP32 only downloads
the rendered frame.

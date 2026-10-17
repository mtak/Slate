# Data providers

Slate providers fetch or supply data for the server renderer. Configure the
calendar data source with `SLATE_CALENDAR_PROVIDER`; the default is `sample`.

| Provider | `SLATE_CALENDAR_PROVIDER` | Setup guide | Credentials |
| --- | --- | --- | --- |
| Sample data | `sample` | [Sample provider](sample.md) | None |
| Google Calendar iCal feed | `ical` | [Google Calendar iCal feed](google-calendar-ical.md) | Secret HTTPS feed URL in local `.env` |

Every provider returns named values through `get_data()`. The renderer uses
these values with the editable [`server/layout.json`](../../server/layout.json)
layout. Provider integrations belong on the server; the ESP32 only downloads
the rendered frame.

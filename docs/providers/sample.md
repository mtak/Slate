# Sample provider

The sample provider is used by default and needs no credentials or network
access. It supplies fictional display text and three example events so the
renderer, browser preview, and firmware can be used before a live integration
is configured. Keep `SLATE_CALENDAR_ICAL_URL` empty in `.env` to use sample
data.

The sample values are defined by `SampleProvider` in
[`server/providers.py`](../../server/providers.py). They contain no household
data. To try a live calendar, follow the
[Google Calendar iCal feed guide](google-calendar-ical.md).

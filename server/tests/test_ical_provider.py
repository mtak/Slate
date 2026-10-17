import os
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import requests

from providers import DailyAffirmationProvider, ICalendarProvider, SampleProvider, provider_from_environment


class FakeResponse:
    status_code = 200

    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


class ICalendarProviderTests(unittest.TestCase):
    def test_uses_sample_provider_when_feed_url_is_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            provider = provider_from_environment()

        self.assertIsInstance(provider, SampleProvider)

    def test_uses_ical_provider_when_feed_url_is_configured(self):
        with patch.dict(os.environ, {
            "SLATE_CALENDAR_ICAL_URL": "https://calendar.example.invalid/private.ics",
            "TZ": "UTC",
        }, clear=True):
            provider = provider_from_environment()

        self.assertIsInstance(provider, ICalendarProvider)
        self.assertEqual(provider.url, "https://calendar.example.invalid/private.ics")

    def test_reads_recurring_and_all_day_events_in_configured_window(self):
        start = datetime.now(timezone.utc) + timedelta(days=1)
        start_text = start.strftime("%Y%m%dT%H%M%SZ")
        all_day = (start + timedelta(days=1)).strftime("%Y%m%d")
        feed = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:weekly
DTSTART:{start_text}
DURATION:PT30M
RRULE:FREQ=DAILY;COUNT=3
SUMMARY:Household event
END:VEVENT
BEGIN:VEVENT
UID:all-day
DTSTART;VALUE=DATE:{all_day}
DTEND;VALUE=DATE:{(start + timedelta(days=2)).strftime('%Y%m%d')}
SUMMARY:All day event
END:VEVENT
END:VCALENDAR
""".encode()
        provider = ICalendarProvider("https://calendar.example.invalid/private.ics", "UTC")

        with patch("requests.get", return_value=FakeResponse(feed)) as get:
            data = provider.get_data()

        get.assert_called_once_with(
            "https://calendar.example.invalid/private.ics", timeout=15, allow_redirects=False
        )
        self.assertEqual(data["greeting"], "Calendar")
        self.assertEqual(data["headline"], "Upcoming events")
        self.assertEqual([event["title"] for event in data["events"]], [
            "Household event", "All day event", "Household event", "Household event",
        ])
        self.assertEqual(data["events"][1]["time"], "All day")

    def test_rejects_non_https_feed_url(self):
        with self.assertRaisesRegex(ValueError, "must use HTTPS"):
            ICalendarProvider("http://example.invalid/private.ics", "UTC")

    def test_feed_error_does_not_disclose_secret_url(self):
        secret_url = "https://example.invalid/private-secret-token/basic.ics"
        provider = ICalendarProvider(secret_url, "UTC")
        with patch("requests.get", side_effect=requests.Timeout(secret_url)):
            with self.assertRaisesRegex(RuntimeError, "Unable to read") as error:
                provider.get_data()
        self.assertNotIn(secret_url, str(error.exception))


class DailyAffirmationProviderTests(unittest.TestCase):
    def test_selects_the_same_affirmation_within_a_day_and_advances_the_next_day(self):
        first_day = date(2026, 10, 17)
        provider = DailyAffirmationProvider(today=lambda: first_day)
        first = provider.get_data()

        self.assertEqual(provider.get_data(), first)
        self.assertEqual(provider.get_data()["affirmation_heading"], "Listen b*tch")
        self.assertNotEqual(
            first["affirmation"],
            DailyAffirmationProvider(today=lambda: first_day + timedelta(days=1)).get_data()["affirmation"],
        )


if __name__ == "__main__":
    unittest.main()

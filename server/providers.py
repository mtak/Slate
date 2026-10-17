"""Small interfaces and integrations for server-side data sources."""

import os
from datetime import datetime, timedelta
from typing import Callable, Protocol
from zoneinfo import ZoneInfo

DEFAULT_DATE_FORMAT = "%A, %B %d"


class Provider(Protocol):
    """A source of named values consumed by the layout renderer."""

    def get_data(self) -> dict[str, object]:
        """Return the current values keyed by the names used in layout JSON."""


class SampleProvider:
    """Deterministic example data that needs no credentials or network access."""

    def get_data(self) -> dict[str, object]:
        return {
            "greeting": "Good morning",
            "date": "Saturday, October 17",
            "weekday": "Saturday",
            "day": "17",
            "month": "October",
            "headline": "Today",
            "message": "Your sample display is ready.",
            "events": [
                {"title": "Coffee with Alex", "date": "Today", "time": "10:30"},
                {"title": "Pick up groceries", "date": "Today", "time": "17:00"},
                {"title": "Family lunch", "date": "Tomorrow", "time": "12:00"},
            ],
        }


class CurrentDateProvider:
    """Provide the current local date in text and calendar-friendly parts."""

    def __init__(self, date_format: str = DEFAULT_DATE_FORMAT, now: Callable[[], datetime] | None = None):
        self.date_format = date_format
        self.now = now or (lambda: datetime.now().astimezone())

    def get_data(self) -> dict[str, str]:
        current = self.now()
        return {
            "date": current.strftime(self.date_format),
            "weekday": current.strftime("%A"),
            "day": current.strftime("%d").lstrip("0") or "0",
            "month": current.strftime("%B"),
        }


def _calendar_data(events: list[dict[str, str]], timezone: ZoneInfo) -> dict[str, object]:
    today = datetime.now(timezone).strftime("%A, %B %-d")
    return {
        "greeting": "Calendar",
        "date": today,
        "headline": "Upcoming events",
        "message": "From your shared calendar.",
        "events": events,
    }


class ICalendarProvider:
    """Read an HTTPS iCalendar feed URL kept private in deployment config."""

    def __init__(self, url: str, timezone: str, max_results: int = 6, days_ahead: int = 14):
        if not url.startswith("https://"):
            raise ValueError("SLATE_CALENDAR_ICAL_URL must use HTTPS")
        self.url = url
        self.timezone = ZoneInfo(timezone)
        self.max_results = max_results
        self.days_ahead = days_ahead

    def get_data(self) -> dict[str, object]:
        import requests
        import recurring_ical_events
        from icalendar import Calendar

        try:
            response = requests.get(self.url, timeout=15, allow_redirects=False)
            response.raise_for_status()
            calendar = Calendar.from_ical(response.content)
        except Exception:
            # Feed URLs can contain bearer secrets; never include request errors in logs.
            raise RuntimeError("Unable to read the configured iCalendar feed") from None

        now = datetime.now(self.timezone)
        end = now + timedelta(days=self.days_ahead)
        dated_events = []
        for item in recurring_ical_events.of(calendar).between(now, end):
            start_value = item.get("dtstart")
            if start_value is None:
                continue
            start = start_value.dt
            if isinstance(start, datetime):
                local_start = start.replace(tzinfo=self.timezone) if start.tzinfo is None else start.astimezone(self.timezone)
                event_date = local_start.date()
                event_time = local_start.strftime("%H:%M")
                sort_at = local_start
            else:
                event_date = start
                event_time = "All day"
                sort_at = datetime.combine(event_date, datetime.min.time(), self.timezone)
            date = "Today" if event_date == now.date() else (
                "Tomorrow" if (event_date - now.date()).days == 1
                else event_date.strftime("%a, %b %-d")
            )
            summary = str(item.get("summary") or "(Untitled event)")
            dated_events.append((sort_at, {"title": summary, "date": date, "time": event_time}))
        dated_events.sort(key=lambda event: event[0])
        events = [event for _, event in dated_events[:self.max_results]]
        return _calendar_data(events, self.timezone)


def provider_from_environment():
    """Use iCal when a feed URL is configured; otherwise use sample data."""
    url = os.environ.get("SLATE_CALENDAR_ICAL_URL")
    if not url:
        return SampleProvider()
    timezone = os.environ.get("TZ", "UTC")
    max_events = int(os.environ.get("SLATE_CALENDAR_MAX_EVENTS", "6"))
    days_ahead = int(os.environ.get("SLATE_CALENDAR_DAYS_AHEAD", "14"))
    return ICalendarProvider(url, timezone, max_events, days_ahead)

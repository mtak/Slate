"""Small interfaces and integrations for server-side data sources."""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
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
                {"title": "Example meeting", "date": "Today", "time": "10:30"},
                {"title": "Example reminder", "date": "Today", "time": "17:00"},
                {"title": "Example event", "date": "Tomorrow", "time": "12:00"},
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


class LiteralTextProvider:
    """Load user-authored string values from a local JSON configuration file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def get_data(self) -> dict[str, str]:
        try:
            with self.path.open(encoding="utf-8") as config_file:
                values = json.load(config_file)
        except FileNotFoundError:
            raise ValueError(f"literal text configuration file does not exist: {self.path}") from None
        except (OSError, UnicodeError) as error:
            raise ValueError(f"cannot read literal text configuration file {self.path}: {error}") from None
        except json.JSONDecodeError as error:
            raise ValueError(
                f"literal text configuration file {self.path} is not valid JSON: {error.msg} at line {error.lineno}"
            ) from None

        if not isinstance(values, dict):
            raise ValueError(f"literal text configuration file {self.path} must contain a JSON object")
        if any(not isinstance(key, str) or not key.strip() for key in values):
            raise ValueError(f"literal text configuration file {self.path} must use non-empty keys")
        if any(not isinstance(value, str) for value in values.values()):
            raise ValueError(f"literal text configuration file {self.path} must contain only string values")
        return values


class DailyAffirmationProvider:
    """Return one bundled affirmation selected for the current local date."""

    AFFIRMATIONS = (
        "You've handled worse. Handle this.",
        "You're building a life, not racing anyone.",
        "That doubt can sit down. You know your stuff.",
        "You deserve rest. Take the damn break.",
        "Take up space. Your ideas belong here.",
        "You can mess up and still be a badass.",
        "Changing your mind is allowed. That's growth.",
        "Stop shrinking your plans for their comfort.",
        "You deserve your own kindness, right now.",
        "One small step counts. Do the next damn thing.",
        "Your boundaries are valid. Keep them.",
        "You've made it through every hard day so far.",
        "Celebrate the win. Yes, even that one.",
        "Nobody else gets to set your worth.",
    )

    def __init__(self, today: Callable[[], date] | None = None):
        self.today = today or (lambda: datetime.now().astimezone().date())

    def get_data(self) -> dict[str, str]:
        day = self.today()
        return {
            "affirmation_heading": "Listen b*tch",
            "affirmation": self.AFFIRMATIONS[day.toordinal() % len(self.AFFIRMATIONS)],
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


def literal_text_provider_from_environment():
    """Enable literal text only when its local config path is explicitly set."""
    path = os.environ.get("SLATE_LITERAL_TEXT_FILE")
    return LiteralTextProvider(path) if path else None

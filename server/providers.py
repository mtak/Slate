"""Small interfaces and integrations for server-side data sources."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Protocol


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
            "headline": "Today",
            "message": "Your sample display is ready.",
            "events": [
                {"title": "Coffee with Alex", "date": "Today", "time": "10:30"},
                {"title": "Pick up groceries", "date": "Today", "time": "17:00"},
                {"title": "Family lunch", "date": "Tomorrow", "time": "12:00"},
            ],
        }


class GoogleCalendarProvider:
    """Read upcoming events from a calendar shared with a service account."""

    def __init__(self, credentials_path: str, calendar_id: str, timezone: str,
                 max_results: int = 6, days_ahead: int = 14):
        self.credentials_path = Path(credentials_path)
        self.calendar_id = calendar_id
        self.timezone = ZoneInfo(timezone)
        self.max_results = max_results
        self.days_ahead = days_ahead

    def get_data(self) -> dict[str, object]:
        # Imported only for the selected provider so sample mode stays lightweight.
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            str(self.credentials_path),
            scopes=["https://www.googleapis.com/auth/calendar.events.readonly"],
        )
        service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        now = datetime.now(self.timezone)
        response = service.events().list(
            calendarId=self.calendar_id,
            timeMin=now.isoformat(),
            timeMax=(now + timedelta(days=self.days_ahead)).isoformat(),
            maxResults=self.max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for item in response.get("items", []):
            start = item.get("start", {})
            if "dateTime" in start:
                event_start = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
                local_start = event_start.astimezone(self.timezone)
                date = "Today" if local_start.date() == now.date() else (
                    "Tomorrow" if (local_start.date() - now.date()).days == 1
                    else local_start.strftime("%a, %b %-d")
                )
                event_time = local_start.strftime("%H:%M")
            elif "date" in start:
                event_date = datetime.fromisoformat(start["date"]).date()
                date = "Today" if event_date == now.date() else (
                    "Tomorrow" if (event_date - now.date()).days == 1
                    else event_date.strftime("%a, %b %-d")
                )
                event_time = "All day"
            else:
                continue
            events.append({"title": item.get("summary") or "(Untitled event)",
                           "date": date, "time": event_time})
        return {"events": events}


class ICalendarProvider:
    """Read an HTTPS iCalendar feed URL kept private in deployment config."""

    def __init__(self, url: str, timezone: str, max_results: int = 6, days_ahead: int = 14):
        if not url.startswith("https://"):
            raise ValueError("SLATE_ICAL_URL must use HTTPS")
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
        return {"events": [event for _, event in dated_events[:self.max_results]]}


def provider_from_environment():
    """Build the configured provider, validating required private settings."""
    name = os.environ.get("SLATE_PROVIDER", "sample").lower()
    if name == "sample":
        return SampleProvider()
    timezone = os.environ.get("SLATE_TIMEZONE", "UTC")
    max_events = int(os.environ.get("SLATE_CALENDAR_MAX_EVENTS", "6"))
    days_ahead = int(os.environ.get("SLATE_CALENDAR_DAYS_AHEAD", "14"))
    if name == "ical":
        url = os.environ.get("SLATE_ICAL_URL")
        if not url:
            raise ValueError("SLATE_ICAL_URL is required when SLATE_PROVIDER=ical")
        return ICalendarProvider(url, timezone, max_events, days_ahead)
    if name != "google_calendar":
        raise ValueError("SLATE_PROVIDER must be sample, ical, or google_calendar")
    credentials = os.environ.get("SLATE_GOOGLE_CREDENTIALS")
    calendar_id = os.environ.get("SLATE_GOOGLE_CALENDAR_ID")
    if not credentials or not calendar_id:
        raise ValueError("SLATE_GOOGLE_CREDENTIALS and SLATE_GOOGLE_CALENDAR_ID are required")
    return GoogleCalendarProvider(
        credentials, calendar_id, timezone,
        max_results=max_events,
        days_ahead=days_ahead,
    )

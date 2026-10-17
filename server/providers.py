"""Small interfaces for server-side data sources."""

from datetime import datetime
from typing import Callable, Protocol

DEFAULT_DATE_FORMAT = "%A, %B %d"


class Provider(Protocol):
    """A source of named values consumed by the layout renderer."""

    def get_data(self) -> dict[str, str]:
        """Return the current values keyed by the names used in layout JSON."""


class SampleProvider:
    """Deterministic example data that needs no credentials or network access."""

    def get_data(self) -> dict[str, str]:
        return {
            "greeting": "Good morning",
            "date": "Saturday, October 17",
            "weekday": "Saturday",
            "day": "17",
            "month": "October",
            "headline": "Today",
            "message": "Your sample display is ready.",
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

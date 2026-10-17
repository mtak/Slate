"""Small interfaces for server-side data sources."""

from typing import Protocol


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
            "headline": "Today",
            "message": "Your sample display is ready.",
        }

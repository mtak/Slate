"""Small interfaces and integrations for server-side data sources."""

import math
import json
import os
from datetime import date, datetime, timedelta, timezone as datetime_timezone
from pathlib import Path
from typing import Callable, Protocol
from urllib.parse import quote
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
    """Provide one user-authored string under the layout key assigned to it."""

    def __init__(self, key: str, text: str):
        if not isinstance(key, str) or not key.strip():
            raise ValueError("literal text provider key must be a non-empty string")
        if not isinstance(text, str):
            raise ValueError("literal text provider content must be a string")
        self.key = key
        self.text = text

    def get_data(self) -> dict[str, str]:
        return {self.key: self.text}


def literal_text_providers_from_environment() -> list[LiteralTextProvider]:
    """Create one provider instance per named text in the configured JSON file."""
    path = os.environ.get("SLATE_LITERAL_TEXT_FILE")
    if not path:
        return []

    config_path = Path(path)
    try:
        with config_path.open(encoding="utf-8") as config_file:
            values = json.load(config_file)
    except FileNotFoundError:
        raise ValueError(f"literal text configuration file does not exist: {config_path}") from None
    except (OSError, UnicodeError) as error:
        raise ValueError(f"cannot read literal text configuration file {config_path}: {error}") from None
    except json.JSONDecodeError as error:
        raise ValueError(
            f"literal text configuration file {config_path} is not valid JSON: {error.msg} at line {error.lineno}"
        ) from None

    if not isinstance(values, dict):
        raise ValueError(f"literal text configuration file {config_path} must contain a JSON object")
    if any(not isinstance(key, str) or not key.strip() for key in values):
        raise ValueError(f"literal text configuration file {config_path} must use non-empty keys")
    if any(not isinstance(value, str) for value in values.values()):
        raise ValueError(f"literal text configuration file {config_path} must contain only string values")
    return [LiteralTextProvider(key, text) for key, text in values.items()]


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


class HomeAssistantPowerProvider:
    """Read one Home Assistant power sensor as an integer number of watts."""

    def __init__(self, base_url: str, token: str, entity_id: str):
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("SLATE_HOME_ASSISTANT_URL must use HTTP or HTTPS")
        if not token:
            raise ValueError("SLATE_HOME_ASSISTANT_TOKEN must not be empty")
        if not entity_id:
            raise ValueError("SLATE_HOME_ASSISTANT_POWER_CONSUMPTION_ENTITY must not be empty")
        self.url = f"{base_url.rstrip('/')}/api/states/{quote(entity_id, safe='')}"
        self.token = token

    def get_data(self) -> dict[str, object]:
        import requests

        try:
            response = requests.get(
                self.url,
                headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
                timeout=10,
                allow_redirects=False,
            )
            response.raise_for_status()
            sensor = response.json()
            state = float(sensor["state"])
            unit = sensor.get("attributes", {}).get("unit_of_measurement")
            if not math.isfinite(state) or unit not in ("W", "kW"):
                raise ValueError("unsupported power sensor reading")
            watts = round(state * (1000 if unit == "kW" else 1))
            return {"power_watts": watts}
        except Exception:
            # Keep tokens, local URLs, and Home Assistant response data out of logs.
            return {"power_watts": None}


def home_assistant_power_provider_from_environment() -> HomeAssistantPowerProvider | None:
    """Create the optional Home Assistant integration when all settings exist."""
    base_url = os.environ.get("SLATE_HOME_ASSISTANT_URL")
    token = os.environ.get("SLATE_HOME_ASSISTANT_TOKEN")
    entity_id = os.environ.get("SLATE_HOME_ASSISTANT_POWER_CONSUMPTION_ENTITY")
    if not any((base_url, token, entity_id)):
        return None
    if not all((base_url, token, entity_id)):
        raise ValueError(
            "SLATE_HOME_ASSISTANT_URL, SLATE_HOME_ASSISTANT_TOKEN, and "
            "SLATE_HOME_ASSISTANT_POWER_CONSUMPTION_ENTITY must be configured together"
        )
    return HomeAssistantPowerProvider(base_url, token, entity_id)


class OpenMeteoProvider:
    """Fetch a short hourly precipitation forecast from Open-Meteo."""

    DEFAULT_LATITUDE = 52.04
    DEFAULT_LONGITUDE = 4.33
    DEFAULT_TIMEZONE = "Europe/Amsterdam"
    DEFAULT_FORECAST_HOURS = 4
    DEFAULT_FORECAST_DAYS = 4
    API_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, latitude=DEFAULT_LATITUDE, longitude=DEFAULT_LONGITUDE,
                 timezone_name=DEFAULT_TIMEZONE, forecast_hours=DEFAULT_FORECAST_HOURS,
                 now: Callable[[], datetime] | None = None, forecast_days=DEFAULT_FORECAST_DAYS):
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        if not math.isfinite(self.latitude) or not -90 <= self.latitude <= 90:
            raise ValueError("SLATE_WEATHER_LATITUDE must be between -90 and 90")
        if not math.isfinite(self.longitude) or not -180 <= self.longitude <= 180:
            raise ValueError("SLATE_WEATHER_LONGITUDE must be between -180 and 180")
        self.timezone_name = timezone_name
        self.timezone = ZoneInfo(timezone_name)
        self.forecast_hours = int(forecast_hours)
        if not 1 <= self.forecast_hours <= 24:
            raise ValueError("SLATE_WEATHER_FORECAST_HOURS must be between 1 and 24")
        self.forecast_days = int(forecast_days)
        if not 1 <= self.forecast_days <= 7:
            raise ValueError("SLATE_WEATHER_FORECAST_DAYS must be between 1 and 7")
        self.now = now or (lambda: datetime.now(datetime_timezone.utc))

    def _first_forecast_hour(self) -> datetime:
        """Find the next local top-of-hour, including repeated DST hours."""
        current = self.now().astimezone(datetime_timezone.utc)
        candidate = current.replace(second=0, microsecond=0)
        if candidate <= current:
            candidate += timedelta(minutes=1)
        for _ in range(61):
            local = candidate.astimezone(self.timezone)
            if local.minute == 0:
                return candidate
            candidate += timedelta(minutes=1)
        raise ValueError("could not find the next local forecast hour")

    def get_data(self) -> dict[str, object]:
        try:
            import requests

            response = requests.get(
                self.API_URL,
                params={
                    "latitude": self.latitude,
                    "longitude": self.longitude,
                    "hourly": "precipitation_probability,precipitation",
                    "daily": "precipitation_probability_max,precipitation_sum",
                    "timezone": "UTC",
                    "forecast_hours": self.forecast_hours + 2,
                    "forecast_days": self.forecast_days,
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            hourly = response.json()["hourly"]
            times = hourly["time"]
            probabilities = hourly["precipitation_probability"]
            amounts = hourly["precipitation"]
            if not (len(times) == len(probabilities) == len(amounts)):
                raise ValueError("forecast arrays have different lengths")

            by_time = {
                datetime.fromisoformat(timestamp).replace(tzinfo=datetime_timezone.utc): (probability, amount)
                for timestamp, probability, amount in zip(times, probabilities, amounts)
            }
            first = self._first_forecast_hour()
            forecast = []
            for index in range(self.forecast_hours):
                slot = first + timedelta(hours=index)
                values = by_time.get(slot)
                if values is None:
                    raise ValueError("forecast does not include all requested hours")
                probability, amount = values
                if probability is not None:
                    probability = float(probability)
                    if not math.isfinite(probability) or not 0 <= probability <= 100:
                        raise ValueError("invalid precipitation probability")
                if amount is not None:
                    amount = float(amount)
                    if not math.isfinite(amount) or amount < 0:
                        raise ValueError("invalid precipitation amount")
                forecast.append({
                    "hour": slot.astimezone(self.timezone).strftime("%H:%M"),
                    "probability": probability,
                    "amount": amount,
                })
            daily = response.json()["daily"]
            daily_times = daily["time"]
            daily_probabilities = daily["precipitation_probability_max"]
            daily_amounts = daily["precipitation_sum"]
            if not (len(daily_times) == len(daily_probabilities) == len(daily_amounts)) or len(daily_times) < self.forecast_days:
                raise ValueError("daily forecast arrays have different lengths")
            daily_forecast = []
            for timestamp, probability, amount in zip(
                daily_times[:self.forecast_days],
                daily_probabilities[:self.forecast_days],
                daily_amounts[:self.forecast_days],
            ):
                if probability is not None:
                    probability = float(probability)
                    if not math.isfinite(probability) or not 0 <= probability <= 100:
                        raise ValueError("invalid daily precipitation probability")
                if amount is not None:
                    amount = float(amount)
                    if not math.isfinite(amount) or amount < 0:
                        raise ValueError("invalid daily precipitation amount")
                daily_forecast.append({
                    "day": datetime.fromisoformat(timestamp).strftime("%a"),
                    "probability": probability,
                    "amount": amount,
                })
            return {
                "precipitation_forecast": forecast,
                "precipitation_daily_forecast": daily_forecast,
            }
        except Exception:
            # Keep network and response details out of logs and the public frame.
            return {"precipitation_forecast": None, "precipitation_daily_forecast": None}


def open_meteo_provider_from_environment() -> OpenMeteoProvider:
    """Create the weather integration using optional local configuration."""
    return OpenMeteoProvider(
        os.environ.get("SLATE_WEATHER_LATITUDE", OpenMeteoProvider.DEFAULT_LATITUDE),
        os.environ.get("SLATE_WEATHER_LONGITUDE", OpenMeteoProvider.DEFAULT_LONGITUDE),
        os.environ.get("SLATE_WEATHER_TIMEZONE", OpenMeteoProvider.DEFAULT_TIMEZONE),
        os.environ.get("SLATE_WEATHER_FORECAST_HOURS", OpenMeteoProvider.DEFAULT_FORECAST_HOURS),
        forecast_days=os.environ.get("SLATE_WEATHER_FORECAST_DAYS", OpenMeteoProvider.DEFAULT_FORECAST_DAYS),
    )


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

# Open-Meteo precipitation forecasts

Slate fetches hourly precipitation probability and amounts from the
Open-Meteo forecast API. The default location is Rijswijk, The Netherlands.
Both the standard and Nightwave layouts show the next four hours, with each
cell displaying the time, precipitation chance, and amount in millimeters.

The amount includes rain, showers, and snow. If the request fails or the
response is incomplete, the display says “Forecast unavailable”.

## Configure the location and window

Set these variables in the local `.env` file or deployment environment:

| Variable | Default | Meaning |
| --- | --- | --- |
| `SLATE_WEATHER_LATITUDE` | `52.04` | Latitude in decimal degrees |
| `SLATE_WEATHER_LONGITUDE` | `4.33` | Longitude in decimal degrees |
| `SLATE_WEATHER_TIMEZONE` | `Europe/Amsterdam` | IANA timezone used for forecast labels |
| `SLATE_WEATHER_FORECAST_HOURS` | `4` | Number of hourly entries to show (1–24) |

The `forecast_hours` block uses `precipitation_forecast`. Nightwave sets four
columns in its left panel. Adjust the amount, chance, and time sizes in the
layout JSON as needed.

No API key is needed for Open-Meteo's free non-commercial service. Its data is
licensed under CC BY 4.0 and requires attribution. Disabling the on-screen
credit does not remove that requirement; provide attribution elsewhere, for
example with the literal text provider. Check [Open-Meteo's terms](https://open-meteo.com/en/terms)
before using the free endpoint for commercial purposes.

If the service is unavailable, Slate keeps rendering the rest of the frame and
shows the forecast unavailable message. The server refresh interval controls
how often it requests a new forecast.

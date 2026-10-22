# Open-Meteo hourly precipitation forecast

Slate fetches hourly precipitation probability and amount from the Open-Meteo
forecast API. The default location is Rijswijk, The Netherlands. Each forecast
row shows the local hour, chance of precipitation, and precipitation amount in
millimeters. The default window shows the next four local hourly entries,
starting at the next full hour.

The values are for the hour ending at the displayed time: Open-Meteo reports
precipitation probability and total precipitation for the preceding hour. The
amount includes rain, showers, and snow. If the request fails or the response
does not contain every requested hour, the display says “Forecast unavailable”.

## Configure the location and window

Set these variables in the local `.env` file or deployment environment:

| Variable | Default | Meaning |
| --- | --- | --- |
| `SLATE_WEATHER_LATITUDE` | `52.04` | Latitude in decimal degrees |
| `SLATE_WEATHER_LONGITUDE` | `4.33` | Longitude in decimal degrees |
| `SLATE_WEATHER_TIMEZONE` | `Europe/Amsterdam` | IANA timezone used for hour labels and the next-hour boundary |
| `SLATE_WEATHER_FORECAST_HOURS` | `4` | Number of future hourly entries to show (1–24) |

The default layout uses the `forecast_hours` block with the provider key
`precipitation_forecast`. The amount, chance, and time text sizes are configured
independently with `amount_size`, `chance_size`, and `time_size` in the layout
JSON. Open-Meteo attribution is enabled by default; `attribution_size` defaults
to 8 pixels. Set `show_attribution` to `false` to hide it on screen. The server
logs a warning when attribution is disabled. Move, resize, or remove the block in
`server/layout.json` to change the display. The renderer keeps the forecast in
the same 800×480, 1-bit frame as the rest of the layout. If the configured
forecast has more entries than fit across the block, increase its width and
move nearby blocks as needed.

No API key is needed for Open-Meteo's free non-commercial service. Its data is
licensed under CC BY 4.0 and requires attribution. Disabling the on-screen
credit does not remove that requirement; provide attribution elsewhere, for
example with the literal text provider. Check [Open-Meteo's terms](https://open-meteo.com/en/terms)
before using the free endpoint for commercial purposes.

If the service is unavailable, Slate keeps rendering the rest of the frame and
shows the forecast unavailable message. The server refresh interval controls
how often it requests a new forecast.

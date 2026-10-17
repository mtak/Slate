# Google Calendar iCal feed provider

The `ical` provider reads events from Google's secret iCal feed URL. It does
not need a Google Cloud project or service-account key. The server fetches the
feed over HTTPS, expands recurring events, and converts event times to the
configured timezone.

## Get the secret feed address

In Google Calendar on a computer:

1. Open **Settings**.
2. Under **Settings for my calendars**, select the calendar to display.
3. Open **Integrate calendar** and copy **Secret address in iCal format**.

Treat this URL as a password: anyone who has it can read the calendar. Do not
paste it into chat, commit it, include it in screenshots, or share logs that
contain it. Store it only in the local `.env` file. If it is exposed, reset the
secret address in Google Calendar to invalidate it.

## Configure the server

From the repository root, create the ignored local environment file:

```sh
cp .env.example .env
openssl rand -hex 32
```

Copy the random value printed by `openssl` into `SLATE_DEVICE_TOKEN`. Edit
`.env` and set these values. Paste the real URL only into the local file:

```dotenv
SLATE_DEVICE_TOKEN=<generated-random-token>
SLATE_REQUIRE_HTTPS=false
SLATE_CALENDAR_ICAL_URL=<secret-https-ical-address>
TZ=Europe/Amsterdam
SLATE_CALENDAR_MAX_EVENTS=6
SLATE_CALENDAR_DAYS_AHEAD=14
```

Use an IANA timezone such as `Europe/Amsterdam`. The provider requests events
from now through the configured number of days ahead, up to the configured
event limit. All-day events display as “All day”. The server refreshes its
cached frame according to `SLATE_REFRESH_SECONDS` (60 seconds by default).

`SLATE_REQUIRE_HTTPS=false` is for the loopback browser preview only. A device
deployment must use a reachable HTTPS endpoint with certificate validation
enabled in firmware. See [setup and commissioning](../getting-started.md).

## Run and preview

Start the server from the repository root:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

Open <http://127.0.0.1:8000/preview> and enter the same `SLATE_DEVICE_TOKEN`
configured in `.env`. The frame contains event titles, dates, and times using
the layout in `server/layout.json`. Adjust the `events` block's `count`,
`row_height`, text sizes, and `max_width` to fit the display.

The iCal URL is fetched only by the server and is not included in application
error logs. Redirects are disabled for feed requests. Provider errors produce a
generic failed frame response; check the server log without sharing the URL.

The local environment file is ignored by Git. Verify this before committing
configuration changes:

```sh
git check-ignore .env
```

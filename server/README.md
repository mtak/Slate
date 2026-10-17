# Server

The server combines data providers with an editable layout, renders an 800×480
1-bit monochrome frame, and serves it to the ESP32. The browser preview shows
the same frame that the device receives. The version 1 byte format is described
in the [image contract](../docs/architecture.md#image-contract). For the
end-to-end setup sequence, see [setup and commissioning](../docs/getting-started.md).

## Run locally

```sh
cd server
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export SLATE_DEVICE_TOKEN="$(openssl rand -hex 32)"
export SLATE_REQUIRE_HTTPS=false
python3 app.py
```

Open <http://127.0.0.1:8000/preview> to see the sample layout. The raw frame is
available at <http://127.0.0.1:8000/api/frame/v1>. The endpoint requires
`Authorization: Bearer <device-token>`. The preview asks for the token in a
password field and keeps it in browser memory only. The token is never accepted
in a URL or written to server logs.

## Edit the layout

[`layout.json`](layout.json) controls the sample screen. It contains a fixed
800×480 canvas and an ordered `blocks` list. Blocks are drawn in list order on a
white background; positions are pixel coordinates from the top-left corner.
Black is used for text and shapes.

The layout supports these block types:

| Type | Required fields | Optional fields | Effect |
| --- | --- | --- | --- |
| `text` | `key` | `x`, `y`, `size` | Draw the provider value named by `key`. Defaults: position `(0, 0)`, size `24`. |
| `line` | `x2`, `y2` | `x`, `y`, `width` | Draw from `(x, y)` to `(x2, y2)`. Defaults: start `(0, 0)`, width `2`. |
| `rectangle` | `width`, `height` | `x`, `y`, `stroke` | Draw an outline from `(x, y)` to `(x + width, y + height)`. Defaults: position `(0, 0)`, stroke `2`. |
| `events` | — | `key`, `x`, `y`, `count`, `row_height`, `title_size`, `detail_size` | Draw event titles, dates, and times from a provider list. Defaults: key `events`, count `6`, row height `48`. |

For example, this block displays the value for `greeting` at pixel `(48, 48)` in
a 42-pixel font:

```json
{"type": "text", "key": "greeting", "x": 48, "y": 48, "size": 42}
```

Change a block's `x` and `y` to move it, `size` to resize text, or the shape
fields to adjust lines and rectangles. The JSON canvas must remain 800×480 to
match the display and frame contract. The server notices changes to the layout
file and renders an updated frame on the next request; the open preview polls
every five seconds and redraws when the frame changes. When running with
Docker Compose, edit the host copy of `server/layout.json`.

![Rendered sample frame from the editable layout](../docs/frame-preview.png)

## Providers and layout keys

A provider supplies the values used by text blocks. The interface is the
`Provider` protocol in [`providers.py`](providers.py): implement
`get_data()` and return a dictionary whose keys are names used by the layout.
Text values are strings; an event list contains title, date, and time fields.
For example:

```python
class SampleProvider:
    def get_data(self) -> dict[str, object]:
        return {
            "greeting": "Good morning",
            "date": "Saturday, October 17",
            "events": [{"title": "Coffee", "date": "Today", "time": "10:30"}],
        }
```

The layout's `"key": "greeting"` looks up the `greeting` entry and draws its
value, `Good morning`, in the image. The sample provider also returns
`headline` and `message`, which are used by the other text blocks in
`layout.json`. A text block with a key missing from the provider data is an
error, so keep the layout keys and provider keys in sync.

To add another data source, create a provider with the same `get_data()`
interface, then wire it into the server in `app.py` in place of
`SampleProvider`. Keep each integration independent of rendering and keep its
credentials in local or deployment configuration, never in source control.
Editing provider code requires restarting the server; editing only
`layout.json` does not.

## Google Calendar

For the simplest setup, use Google's secret iCal address as a private feed
URL. Anyone who obtains that URL can read the calendar, so do not send it in
chat, add it to source control, or include it in screenshots or logs. You can
revoke it by resetting the secret address in Google Calendar. Keep it in the
ignored local `.env` file instead:

```dotenv
SLATE_PROVIDER=ical
SLATE_ICAL_URL=https://calendar.google.com/calendar/ical/REDACTED/private-REDACTED/basic.ics
SLATE_TIMEZONE=Europe/Amsterdam
SLATE_CALENDAR_MAX_EVENTS=6
SLATE_CALENDAR_DAYS_AHEAD=14
```

Use the address shown under **Settings → Integrate calendar → Secret address
in iCal format**. The feed is fetched over HTTPS with redirects disabled, and
its URL is never written to server logs. The provider expands recurring events
and converts event times to the configured IANA timezone. `.env` is ignored by
Git; never insert the real URL into `.env.example` or share it in support logs.

If you prefer not to use a bearer URL, the service-account setup below provides
read-only Google API access limited by sharing to a specific calendar.

The first live integration uses a Google service account with read-only access
to one calendar. This suits a private household server: no user sign-in or
refresh token is stored, and Google credentials stay on the server. Create a
Google Cloud project, enable the Google Calendar API, create a service account,
and download its JSON key. Share the chosen calendar with the service account's
email address and grant **See all event details** (viewer access). Do not share
your whole Google account or add the key to Git.

For Docker Compose, put the downloaded key at an ignored local path such as
`secrets/google-calendar-service-account.json` (restrict it to your account,
for example with `chmod 600`), set these values in `.env`, then restart the
service:

```dotenv
SLATE_PROVIDER=google_calendar
SLATE_GOOGLE_CREDENTIALS_DIR=./secrets
SLATE_GOOGLE_CALENDAR_ID=your-calendar-id@group.calendar.google.com
SLATE_TIMEZONE=Europe/Amsterdam
SLATE_CALENDAR_MAX_EVENTS=6
SLATE_CALENDAR_DAYS_AHEAD=14
```

Find the calendar ID in Google Calendar under **Settings → Integrate calendar**.
Use an IANA timezone name such as `Europe/Amsterdam`; it controls displayed
event times and the 14-day query window. All-day events display as “All day”.
The sample provider remains the default and supplies three fictional events for
previewing the layout without credentials. Google API failures are reported as
a failed frame render; check server logs and the calendar sharing settings.

## Frame refresh and conditional requests

The server caches a rendered frame for `SLATE_REFRESH_SECONDS` (default 60),
then renders it again on the next request. Frame responses include a strong
SHA-256 ETag. Send it as `If-None-Match` to receive `304 Not Modified` while
the frame is unchanged:

```sh
curl -D headers.txt -o frame.bin \
  -H "Authorization: Bearer $SLATE_DEVICE_TOKEN" \
  http://127.0.0.1:8000/api/frame/v1
etag=$(awk 'tolower($1) == "etag:" { print $2 }' headers.txt)
curl -i -H "Authorization: Bearer $SLATE_DEVICE_TOKEN" \
  -H "If-None-Match: $etag" http://127.0.0.1:8000/api/frame/v1
```

The ETag is the quoted hexadecimal SHA-256 digest of the 48,000 frame bytes.
When the frame changes, the server returns `200 OK`, a new ETag, and the full
frame. A request after the render interval expires can trigger rendering before
the server compares ETags.

## Docker Compose

From the repository root, start the service with:

```sh
cp .env.example .env
openssl rand -hex 32
# Set SLATE_DEVICE_TOKEN in .env to the generated value.
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

Open <http://127.0.0.1:8000/preview>. Compose reads `SLATE_PORT`,
`SLATE_REFRESH_SECONDS`, `SLATE_DEVICE_TOKEN`, and `SLATE_REQUIRE_HTTPS` from
`.env`. The sample sets HTTPS enforcement off for a private local demo; keep
it on in production. It mounts
`server/` read-only so layout edits stay on the host; the container can read
but cannot change the layout. Mounting the whole directory also keeps atomic
file saves visible inside the container, unlike mounting only `layout.json`.
The server checks `layout.json` on each frame request, and the preview polls
every five seconds. The sample layout and provider contain no
household-specific data.

### Production deployment

The included Compose files support local development. A deployment that serves
a physical device must expose an HTTPS endpoint, keep the application port
behind its trusted network boundary, and configure the ESP32 to validate the
endpoint certificate. If `SLATE_REQUIRE_HTTPS=true`, the TLS proxy must send a
correct forwarded scheme value, and the application must only trust that value
from the controlled proxy network. Configure proxy routing, secret storage, and
network exposure in the deployment environment's private operations guide.
Never disable ESP32 certificate validation for a deployed device.

This is intended to be a public repository; follow the [public repository
hygiene notes](../docs/architecture.md#public-repository-hygiene). Secrets
belong in deployment configuration outside source control.

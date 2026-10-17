# Server

The server gathers household data through independent providers, renders an
800×480 1-bit frame using an editable layout, and serves the latest frame to the
ESP32. It also provides a browser preview for layout development.

The version 1 byte layout is defined in [the image
contract](../docs/architecture.md#image-contract). The renderer uses Pillow
and reads its positions, text sizes, and block types from `layout.json`. Data
sources implement `Provider.get_data()` and return a mapping of names to
values; `SampleProvider` supplies deterministic example values and
`CurrentDateProvider` supplies the current local date.

Install the server dependency and run the sample server:

```sh
cd server
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python3 app.py
```

Open <http://127.0.0.1:8000/preview> to inspect the sample. The raw frame is
available at <http://127.0.0.1:8000/api/frame/v1>. The server caches the frame
for `SLATE_REFRESH_SECONDS` (default 60), then renders it again on the next
request. Frame responses include a strong SHA-256 ETag; send it as
`If-None-Match` to receive `304 Not Modified` while the frame is unchanged.

An ETag is the quoted hexadecimal SHA-256 digest of the 48,000 frame bytes.
Save it from a `200 OK` response and send it on the next poll. For example:

```sh
curl -D headers.txt -o frame.bin http://127.0.0.1:8000/api/frame/v1
etag=$(awk 'tolower($1) == "etag:" { print $2 }' headers.txt)
curl -i -H "If-None-Match: $etag" http://127.0.0.1:8000/api/frame/v1
```

When the frame is unchanged, the second request returns `304 Not Modified`
with no frame body. When it has changed, the server returns `200 OK`, the new
ETag, and the full frame. A conditional request made after the render interval
has expired can trigger a new render before the server compares ETags.

## Docker Compose

From the repository root, start the service with:

```sh
cp .env.example .env
docker compose up --build
```

Then open <http://127.0.0.1:8000/preview>. Compose reads `SLATE_PORT`,
`SLATE_REFRESH_SECONDS`, and `SLATE_DATE_FORMAT` from `.env` (defaults 8000,
60 seconds, and `%A, %B %d`). It mounts
`server/` into the container as read-only, so layout edits remain on the host
and cannot be changed from inside the container. Mounting the directory keeps
atomic file saves from being hidden behind a stale single-file mount. The
server checks `layout.json` on each frame request and renders a new frame when
it changes. The open browser preview polls every five seconds and redraws only
when the ETag changes. The sample layout and provider contain no
household-specific data.

To add a data source, implement the small `Provider` interface in
`providers.py`; keep service credentials in local or deployment configuration.
To rearrange the sample content, edit `layout.json`. Supported blocks are
`text` (with a provider `key`, x/y position, and font `size`), `line` (x/y and
x2/y2 endpoints, optional `width`), `rectangle` (x/y, `width`, `height`,
optional `stroke`), and `calendar`. A calendar block draws the provider's
`weekday`, `day`, and `month` values inside a calendar icon. Change its
position, dimensions, outline, and weekday/day/month font sizes in
`layout.json`. The date format defaults to `%A, %B %d`; set `SLATE_DATE_FORMAT`
to any Python `strftime` format string to change it. Weekday and month names
follow the server's locale. The canvas size is fixed at 800×480 to match the
frame contract.

![Rendered sample frame from the editable layout](../docs/frame-preview.png)

This is intended to be a public repository; follow the [public repository
hygiene notes](../docs/architecture.md#public-repository-hygiene). Secrets
belong in deployment configuration outside source control. Providers must
remain server-side and return data through a small common interface.

# Server

The server combines data providers with an editable layout, renders an 800×480
1-bit monochrome frame, and serves it to the ESP32. The browser preview shows
the same frame that the device receives. The version 1 byte format is described
in the [image contract](../docs/architecture.md#image-contract).

## Run locally

```sh
cd server
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python3 app.py
```

Open <http://127.0.0.1:8000/preview> to see the sample layout. The raw frame is
available at <http://127.0.0.1:8000/api/frame/v1>.

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
`get_data()` and return a dictionary whose keys are names and whose values are
strings. For example:

```python
class SampleProvider:
    def get_data(self) -> dict[str, str]:
        return {
            "greeting": "Good morning",
            "date": "Saturday, October 17",
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

## Frame refresh and conditional requests

The server caches a rendered frame for `SLATE_REFRESH_SECONDS` (default 60),
then renders it again on the next request. Frame responses include a strong
SHA-256 ETag. Send it as `If-None-Match` to receive `304 Not Modified` while
the frame is unchanged:

```sh
curl -D headers.txt -o frame.bin http://127.0.0.1:8000/api/frame/v1
etag=$(awk 'tolower($1) == "etag:" { print $2 }' headers.txt)
curl -i -H "If-None-Match: $etag" http://127.0.0.1:8000/api/frame/v1
```

The ETag is the quoted hexadecimal SHA-256 digest of the 48,000 frame bytes.
When the frame changes, the server returns `200 OK`, a new ETag, and the full
frame. A request after the render interval expires can trigger rendering before
the server compares ETags.

## Docker Compose

From the repository root, start the service with:

```sh
cp .env.example .env
docker compose up --build
```

Then open <http://127.0.0.1:8000/preview>. Compose reads `SLATE_PORT` and
`SLATE_REFRESH_SECONDS` from `.env` (defaults 8000 and 60 seconds). It mounts
`server/` read-only so layout edits stay on the host; the container can read
but cannot change the layout. Mounting the whole directory also keeps atomic
file saves visible inside the container, unlike mounting only `layout.json`.
The server checks `layout.json` on each frame request, and the preview polls
every five seconds. The sample layout and provider contain no
household-specific data.

This is intended to be a public repository; follow the [public repository
hygiene notes](../docs/architecture.md#public-repository-hygiene). Secrets
belong in deployment configuration outside source control.

# Server

The server gathers household data through independent providers, renders an
800×480 1-bit frame using an editable layout, and serves the latest frame to the
ESP32. It also provides a browser preview for layout development.

The version 1 byte layout is defined in [the image
contract](../docs/architecture.md#image-contract). The renderer uses Pillow
and reads its positions, text sizes, and block types from `layout.json`. Data
sources implement `Provider.get_data()` and return a mapping of names to
values; `SampleProvider` supplies deterministic example values.

Install the server dependency and run the sample server:

```sh
cd server
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export SLATE_DEVICE_TOKEN="$(openssl rand -hex 32)"
export SLATE_REQUIRE_HTTPS=false
python3 app.py
```

Open <http://127.0.0.1:8000/preview> to inspect the sample. The raw frame is
available at <http://127.0.0.1:8000/api/frame/v1>. The server caches the frame
for `SLATE_REFRESH_SECONDS` (default 60), then renders it again on the next
request. Frame responses include a strong SHA-256 ETag; send it as
`If-None-Match` to receive `304 Not Modified` while the frame is unchanged.
The frame endpoint requires `Authorization: Bearer <device-token>`. Set
`SLATE_DEVICE_TOKEN` in the process environment before starting the server. The
preview page asks for the token in a password field and keeps it in browser
memory only. The token is never accepted in a URL or written to server logs.

An ETag is the quoted hexadecimal SHA-256 digest of the 48,000 frame bytes.
Save it from a `200 OK` response and send it on the next poll. For example:

```sh
curl -D headers.txt -o frame.bin \
  -H "Authorization: Bearer $SLATE_DEVICE_TOKEN" \
  http://127.0.0.1:8000/api/frame/v1
etag=$(awk 'tolower($1) == "etag:" { print $2 }' headers.txt)
curl -i -H "Authorization: Bearer $SLATE_DEVICE_TOKEN" \
  -H "If-None-Match: $etag" http://127.0.0.1:8000/api/frame/v1
```

When the frame is unchanged, the second request returns `304 Not Modified`
with no frame body. When it has changed, the server returns `200 OK`, the new
ETag, and the full frame. A conditional request made after the render interval
has expired can trigger a new render before the server compares ETags.

## Docker Compose

From the repository root, start the service with:

```sh
cp .env.example .env
openssl rand -hex 32
# Set SLATE_DEVICE_TOKEN in .env to the generated value.
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

Generate a token with `openssl rand -hex 32` and set `SLATE_DEVICE_TOKEN` in
the ignored `.env` file, then open <http://127.0.0.1:8000/preview>. Compose
reads `SLATE_PORT`, `SLATE_REFRESH_SECONDS`, `SLATE_DEVICE_TOKEN`, and
`SLATE_REQUIRE_HTTPS` from `.env`. The sample sets HTTPS enforcement off for a
private local demo; keep it on in production. It mounts
`server/` into the container as read-only, so layout edits remain on the host
and cannot be changed from inside the container. Mounting the directory keeps
atomic file saves from being hidden behind a stale single-file mount. The
server checks `layout.json` on each frame request and renders a new frame when
it changes. The open browser preview polls every five seconds and redraws only
when the ETag changes. The sample layout and provider contain no
household-specific data.

### Production TLS with Traefik

Set `SLATE_REQUIRE_HTTPS=true` in the server environment. Terminate TLS in
Traefik and configure it to overwrite `X-Forwarded-Proto` with the external
scheme. The production `compose.yaml` does not publish the app port; attach the
Traefik container to the Compose network and route to `slate-server:8000` so
clients cannot bypass Traefik. The development override publishes the port for
local preview only. The server trusts this header only because that network
boundary is controlled. The ESP32 uses an `https://` base URL and validates the server
certificate with `SLATE_ROOT_CA` from its ignored local config. Set
`SLATE_TLS_VERIFY=false` only for local testing with a self-signed certificate;
do not use that setting in production.

To add a data source, implement the small `Provider` interface in
`providers.py`; keep service credentials in local or deployment configuration.
To rearrange the sample content, edit `layout.json`. Supported blocks are
`text` (with a provider `key`, x/y position, and font `size`), `line` (x/y and
x2/y2 endpoints, optional `width`), and `rectangle` (x/y, `width`, `height`,
optional `stroke`). The canvas size is fixed at 800×480 to match the frame
contract.

![Rendered sample frame from the editable layout](../docs/frame-preview.png)

This is intended to be a public repository; follow the [public repository
hygiene notes](../docs/architecture.md#public-repository-hygiene). Secrets
belong in deployment configuration outside source control. Providers must
remain server-side and return data through a small common interface.

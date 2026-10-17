# Initial architecture

```text
Data providers (calendar, home automation, later sources)
                  │
                  ▼
        Python renderer + layout config
                  │  current monochrome frame
                  ▼
       HTTP frame endpoint / browser preview
                  ▲
                  │ conditional poll (ETag)
                  │
 ESP32: Wi-Fi → TLS/auth → compare frame → refresh panel if changed
```

## Responsibilities

The server owns integrations, formatting, layout, image generation, and the
latest rendered frame. Providers should return data in a small common form and
must not know about the display hardware. Layout/rendering code should accept
provider data and produce an 800×480, 1-bit image.

The renderer's provider interface is `get_data()`, returning named values for
layout blocks. The current date provider supplies a configurable formatted
date plus weekday, day, and month values for the calendar block. The JSON
layout defines block type, position, and style. Pillow converts the result to
the v1 raw frame bytes.

The ESP32 owns Wi-Fi connectivity, authenticated image retrieval, change
detection, and panel driving. It should hold no calendar or home automation
credentials. A hardware watchdog should recover from a stalled firmware task.

## Public repository hygiene

The repository is intended to be public. Keep documentation and examples
polished for new readers, use placeholder values in examples, and never commit
service credentials, device tokens, household calendar/event data, private IP
addresses, or machine-specific settings. Local secret/config files must be
ignored by Git. Review staged changes for accidental sensitive content before
publishing them.

## Image contract

Version 1 is a raw, uncompressed 48,000-byte payload at `GET /api/frame/v1`.
The versioned path identifies the format; the payload has no header. It encodes
an 800×480, 1-bit monochrome frame in row-major order, beginning at the top-left
and proceeding left-to-right, then top-to-bottom. Within each byte, the
leftmost pixel is the most significant bit (bit 7). A zero bit is black and a
one bit is white. Each row is exactly 100 bytes, so there is no row padding.
These are the same byte and pixel conventions used by the firmware frame
buffer and Waveshare display driver.

The server exposes `/preview`, which draws the bytes from the v1 endpoint into
an 800×480 browser canvas using the same origin, row, bit, and polarity rules.
The built-in sample frame marks all four corners and draws an asymmetric
upper-left L to make orientation errors visible.

Each `GET /api/frame/v1` response includes a strong ETag: the quoted
hexadecimal SHA-256 digest of the exact 48,000 frame bytes. A client saves the
ETag from its response and sends it on its next request as `If-None-Match`. If
the current frame still has that ETag, the server responds with
`304 Not Modified` and an empty body. If the frame has changed, the server
returns `200 OK`, the new ETag, and the complete frame. The firmware can then
skip transferring and drawing an unchanged frame.

## Security

Serve the device endpoint over HTTPS. The ESP32 must validate the server
certificate using a trust anchor or supported certificate bundle. Authenticate
the device with a randomly generated token sent in an authorization header, not
in a URL. Keep the token in deployment configuration, out of source control,
and avoid logging it. One device token is sufficient for the initial deployment;
rotation and multiple devices can be added if needed.

## Refresh behavior

The Compose deployment sets the server render cadence with
`SLATE_REFRESH_SECONDS` (default 60 seconds). The service renders on first
request, then keeps those bytes and their ETag until the interval expires. On
the next frame request after expiry, it renders again and derives a new ETag.
An edit to the mounted layout file invalidates the cached frame immediately,
so the next frame request renders the edited layout without restarting the
container.
The firmware's polling cadence is a separate setting: it can poll more often
than the server renders, using `If-None-Match` to avoid receiving duplicate
bytes. Keep panel updates at or above the panel's minimum refresh interval even
if the server output changes frequently. On boot, fetch and display the current
frame. On network failure, keep the existing image and retry with a bounded
backoff.

## Deployment

Docker Compose runs the renderer/API as one service initially. It bind-mounts
the host's `server/` directory read-only, so layout edits persist outside the
image and atomic file saves are visible inside the container. The service
detects layout edits on frame requests. `/preview` polls every five seconds and
redraws when the ETag changes. `.env` can set `SLATE_PORT` and
`SLATE_REFRESH_SECONDS` and is kept local. Expose the browser preview and
authenticated device endpoint on the trusted home network; TLS termination may
be provided by an existing reverse proxy, provided the ESP32 connects to the
authenticated HTTPS endpoint and validates its certificate. The built-in
server itself uses plain HTTP, suitable for local development behind a trusted
network or a TLS-terminating proxy.

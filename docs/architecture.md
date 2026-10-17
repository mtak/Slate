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
layout text blocks. The JSON layout defines block type, position, and style;
the initial renderer supports text, lines, and outlined rectangles. Pillow
converts the result to the v1 raw frame bytes.

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

### Changed-area frame responses

The frame endpoint has an opt-in delta protocol for the ESP32. These headers
are used only by the device; requests without them continue to receive the
full-frame response described above.

| Header | Direction | Meaning |
| --- | --- | --- |
| `X-Slate-Refresh-Mode: full` or `partial` | Request | Tells the server whether the next panel update requires a complete frame or may use a changed-area crop. |
| `X-Slate-Displayed-ETag: <etag>` | Request | For partial mode, identifies the complete frame currently shown on the panel. The value is the quoted ETag previously returned by the server. |
| `X-Slate-Payload-Type: full` or `delta` | Response | Identifies whether the body is the full 800×480 frame or a packed rectangular crop. |
| `X-Slate-Region-X`, `X-Slate-Region-Y`, `X-Slate-Region-Width`, `X-Slate-Region-Height` | Response | Gives the crop origin and dimensions in pixels. A full payload uses `(0, 0, 800, 480)`. |
| `X-Slate-Fallback` | Response | Present with a full payload when a partial request cannot produce a delta; values identify the reason. |

`If-None-Match` tracks the most recently downloaded frame and avoids a repeated
download. `X-Slate-Displayed-ETag` tracks the frame currently visible on the
panel; it can lag behind `If-None-Match` while an update is waiting for the
minimum refresh interval or after a display failure. Keep these two values
separate, and advance the displayed ETag only after the panel update succeeds.

Every changed-frame response uses `200 OK` and retains the same media type,
format version, full display dimensions, and ETag headers. `If-None-Match` is
checked first: if the current frame is unchanged, the response is `304 Not
Modified` with no body, regardless of refresh mode. In partial mode, the server
looks up the displayed ETag among the eight most recently rendered frames. If
found, it compares the 48,000-byte frames and returns the smallest bounding
rectangle that contains every changed byte. Its left edge and width are
aligned to byte boundaries (multiples of eight pixels); the rectangle can
therefore include unchanged pixels at either horizontal edge.
Rows are packed with no padding: each row contains `Region-Width / 8` bytes,
starting at `Region-X / 8` in the full frame. Body length must equal
`(Region-Width / 8) × Region-Height`.

If the displayed ETag is absent or has expired from history, the server returns
`X-Slate-Payload-Type: full`, full-screen region metadata, and the complete
48,000-byte frame, plus `X-Slate-Fallback` explaining why. The device uses this
fallback to perform a full panel refresh and resets the partial counter. This
exception avoids applying an incomplete delta and does not require a second
framebuffer. A planned full refresh also requests and receives the full
payload. For a delta, the ESP32 downloads the crop into its existing
48,000-byte buffer and passes the crop coordinates to the panel partial-window
driver.

The refresh policy chooses the mode before fetching: the first update is full,
then up to two successful partial updates are followed by a full update (the
count is configurable). Failed downloads or panel updates do not advance that
counter. An unchanged frame does not consume a refresh. This policy bounds
ghosting while allowing the controller to update only the region whose content
changed.

## Security

Serve the device endpoint over HTTPS. The ESP32 must validate the server
certificate using a trust anchor or supported certificate bundle. Authenticate
the device with a randomly generated token sent in an authorization header, not
in a URL. Keep the token in deployment configuration, out of source control,
and avoid logging it. One device token is sufficient for the initial deployment;
rotation and multiple devices can be added if needed.
The server requires a Bearer token and supports `SLATE_REQUIRE_HTTPS` to reject
device requests that do not arrive with `X-Forwarded-Proto: https` from the
trusted TLS proxy. In the Traefik deployment, keep the app port private and
route to it over the Compose network.

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
redraws when the ETag changes. `.env` can set `SLATE_REFRESH_SECONDS`,
`SLATE_DEVICE_TOKEN`, and `SLATE_REQUIRE_HTTPS` and is kept local. The base
Compose file does not publish the app port; Traefik can reach `slate-server:8000`
on the Compose network. For a local demo only, `compose.dev.yaml` publishes the
port and `.env` can set `SLATE_PORT`. The built-in server uses plain HTTP behind
the TLS-terminating proxy; the device connects to the proxy's HTTPS endpoint
and validates its certificate.

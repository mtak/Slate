# Initial architecture

```text
Data providers (calendar, home automation, later sources)
                  │
                  ▼
        Python renderer + layout config
                  │  current monochrome frame
                  ▼
       HTTPS image endpoint / browser preview
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

The development server exposes `/preview`, which draws the bytes from the v1
endpoint into an 800×480 browser canvas using the same origin, row, bit, and
polarity rules. The built-in sample frame marks all four corners and draws an
asymmetric upper-left L to make orientation errors visible. Issue #7 will add
an ETag derived from the exact frame bytes; an unchanged conditional request
will return `304 Not Modified` without sending the frame again.

## Security

Serve the device endpoint over HTTPS. The ESP32 must validate the server
certificate using a trust anchor or supported certificate bundle. Authenticate
the device with a randomly generated token sent in an authorization header, not
in a URL. Keep the token in deployment configuration, out of source control,
and avoid logging it. One device token is sufficient for the initial deployment;
rotation and multiple devices can be added if needed.

## Refresh behavior

Poll at a configurable interval, initially around 60 seconds. The server's
render cadence and the firmware polling cadence are separate settings. Avoid
refreshing the panel when the frame hash is unchanged, and enforce the panel's
minimum refresh interval even if the server output changes frequently. On boot,
fetch and display the current frame. On network failure, keep the existing
image and retry with a bounded backoff.

## Deployment

Docker Compose runs the renderer/API as one service initially. Persist editable
layout/configuration separately from the container image. Expose the browser
preview and authenticated device endpoint on the trusted home network; TLS
termination may be provided by an existing reverse proxy, provided the ESP32
connects to the authenticated HTTPS endpoint and validates its certificate.

# Troubleshooting

Start by checking the server preview and the ESP32 serial monitor separately.
The preview checks rendering; the serial output shows whether the device can
connect, authenticate, download a valid frame, and update the panel.

## Server does not start

- Check that `.env` exists and `SLATE_DEVICE_TOKEN` is set to a non-empty
  random value. Compose requires this value even for the local preview.
- Check whether the configured local port is already in use. Set `SLATE_PORT`
  in `.env` to another available port and open that port's `/preview` URL.
- Inspect container output with:

  ```sh
  docker compose -f compose.yaml -f compose.dev.yaml logs
  ```

## Preview is blank or does not update

- Open the browser developer console for a failed frame request.
- Check the server logs and confirm `/api/frame/v1` returns a frame. The
  browser preview does not require the device token.
- Confirm `server/layout.json` is valid JSON and that each text block key exists
  in the active provider's data. The server notices layout edits on the next
  frame request.
- If a recently edited file is not reflected, save it and reload the preview.

## ESP32 does not connect to Wi-Fi

- Check the SSID and password in the ignored
  `firmware/include/slate_config.h` file, including capitalization.
- Confirm the device is within range of the configured network and has a
  supported 2.4 GHz Wi-Fi network available.
- Watch the serial monitor for `Connecting to Wi-Fi` and retry messages. The
  firmware retries with increasing delays, up to 30 seconds.

## HTTPS or authentication fails

- Check that `SLATE_SERVER_BASE_URL` starts with `https://`, names the deployed
  endpoint, and has no trailing slash.
- Confirm the token in the device config exactly matches the server's
  `SLATE_DEVICE_TOKEN`. Tokens are sent in an Authorization header and should
  not be added to URLs or shared in logs.
- Confirm the CA in `SLATE_ROOT_CA` validates the certificate presented by the
  device-facing endpoint. A private CA requires that CA's root certificate.
- If the server rejects an HTTPS request, check the deployment's TLS proxy and
  its trusted forwarding of the external scheme. The server should trust
  forwarded scheme information only from the controlled proxy network.
- Do not disable TLS verification as a permanent fix. Correct the endpoint or
  CA configuration instead.

## Panel is blank, clipped, noisy, or reports a timeout

- Confirm the ESP32 reports a successful frame download before investigating
  the panel. Check that the preview shows the expected frame.
- Confirm the documented wiring, 0.47R display selection, and 4-line SPI
  setting in the [hardware notes](hardware.md). The wiring photograph is also
  available [here](wiring.jpeg).
- The default `7.5V2` and alternate `7.5V2_old` profiles have both been tested
  with this 800×480 panel. The panel revision is unknown; do not infer it from
  markings alone. If testing the alternate profile, build environment
  `slate_esp32_v2_old` and compare its serial output and visible frame.
- A profile is working when the full frame is correctly oriented, the edges
  are visible, black and white areas are distinct, and the serial monitor has
  no busy timeout. See the [hardware diagnostic notes](hardware.md#driver-profile-diagnostic)
  for the tested pattern and results.
- Avoid repeatedly flashing or refreshing a panel that shows persistent
  abnormal behavior. Recheck power and wiring before continuing.

## Device shows an older frame

- The device polls every 60 seconds by default, and the server also caches a
  rendered frame for up to 60 seconds. Allow for both intervals after changing
  provider data.
- Confirm the server preview has updated. If it has, check serial output for
  Wi-Fi, HTTPS, authentication, and frame validation messages.
- A valid changed frame can wait until the configured minimum panel refresh
  interval has elapsed. The current image remains displayed if a request or
  panel initialization fails.

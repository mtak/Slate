# Setup and commissioning

This guide takes a clean checkout through a local server preview and the steps
needed to commission a display. It uses only sample data. A private deployment
may use a different host, network, TLS proxy, or container orchestrator; use
that deployment's instructions for the HTTPS server address and CA certificate.

## 1. Run the local server preview

Install Docker Compose, then from the repository root create a local
configuration and a random device token:

```sh
cp .env.example .env
openssl rand -hex 32
```

Put the generated value in `SLATE_DEVICE_TOKEN` in `.env`. Keep `.env` local; it
is ignored by Git. Start the server with the development override, which makes
the preview available only on the local machine by default:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

Open <http://127.0.0.1:8000/preview> and enter the device token when prompted.
The preview requests the current sample frame and refreshes when its content
changes. Stop the service with Ctrl-C.
See the [server guide](../server/README.md) to run without Docker or edit the
layout and providers.

This local preview is for development. The public server application speaks
plain HTTP internally; a production deployment must provide HTTPS at the
device-facing endpoint, validate the certificate on the ESP32, and keep the
application port reachable only through the trusted deployment network. The
private deployment instructions should explain how its proxy communicates the
external HTTPS scheme to the application when HTTPS enforcement is enabled.

## 2. Configure the device

Use the HTTPS base URL and CA certificate supplied by the deployment. The ESP32
does not connect to the local HTTP preview. From `firmware/`:

```sh
./scripts/setup.sh
cp include/slate_config.h.example include/slate_config.h
```

Edit `include/slate_config.h` and set:

- `SLATE_WIFI_SSID` and `SLATE_WIFI_PASSWORD` for the network the device can
  reach.
- `SLATE_SERVER_BASE_URL` to the deployment's HTTPS origin, without a trailing
  slash (for example, `https://display.example.invalid`).
- `SLATE_DEVICE_TOKEN` to the same random token configured for the server.
- `SLATE_ROOT_CA` to the PEM CA certificate that validates the server
  certificate.

### Prepare the CA certificate for the firmware

Get the trust CA certificate from the deployment instructions or the
organization that manages the endpoint. For a public certificate, use the root
CA certificate published by its certificate authority. For a private
certificate, use the private root CA certificate supplied by the deployment
operator. The certificate served by the endpoint is usually the device/server
certificate, and a TLS server often does not send its root CA; do not assume
that the endpoint will provide its root CA. The quick setup below uses the
currently presented server certificate as a pinned certificate instead.

For a quick home setup, you can capture the certificate currently presented by
the endpoint on its first connection. From `firmware/`, set the host name and
save the first certificate in the presented chain as `server-ca.pem`:

```sh
server_host=display.example.invalid
openssl s_client -connect "${server_host}:443" -servername "$server_host" \
  -showcerts </dev/null 2>/dev/null | openssl x509 -outform PEM > server-ca.pem
```

This trusts the certificate received during that connection; it does not
independently confirm that the certificate belongs to your server. Run it only
when you trust the network and endpoint you are connecting to. If the server
certificate changes or renews, capture the new certificate and update the
firmware configuration. Obtaining the CA from the deployment operator or its
certificate authority avoids pinning an individual server certificate.

Save the CA certificate in PEM format as `server-ca.pem`. It should contain a
`BEGIN CERTIFICATE` line, the base64 certificate data, and an `END CERTIFICATE`
line. From `firmware/`, convert it to the C string literal format used in
`slate_config.h`:

```sh
awk 'BEGIN { printf "\"" } { sub(/\r$/, ""); printf "%s\\n", $0 } END { printf "\"" }' server-ca.pem
```

The output is one quoted C string with `\n` escapes. Replace the example value
of `SLATE_ROOT_CA` with that output, keeping it on one line. If the CA file
contains multiple certificates, use the specific CA certificate that issued
the endpoint chain, as documented by the deployment operator.

Keep this file private. It is ignored by Git. Leave `SLATE_TLS_VERIFY` enabled;
disabling certificate checks is only for temporary local diagnosis and is not
appropriate for a deployed display.

## 3. Build, flash, and verify

Connect the ESP32 by USB and identify its serial port. From `firmware/`, run:

```sh
make build
make upload PORT=/dev/ttyUSB0
make monitor PORT=/dev/ttyUSB0
```

Replace the example port with the one for your computer. On macOS it is often a
`/dev/cu.*` device; on Windows use the matching `COM` port. The monitor runs at
115200 baud. On startup, confirm the serial output reports that Wi-Fi connects,
the frame downloads over HTTPS, and the panel initializes without a timeout.
The panel should show the frame served by the configured Slate instance.

The default firmware profile uses Waveshare's `7.5V2` driver profile. Both it
and `7.5V2_old` have been verified on the documented panel. Keep the wiring and
HAT settings from the [hardware notes](hardware.md); do not change them to
diagnose software or network problems.

## 4. Confirm updates

The device polls the frame endpoint every 60 seconds by default. The server
renders on its own 60-second cadence, and the panel enforces a 60-second minimum
between updates. An unchanged frame does not trigger a panel refresh. Change a
sample layout value or provider value, wait for the next poll, and confirm the
new frame appears. The preview is useful for checking the server output
independently of the physical display.

For hardware-independent firmware checks, run `make test` from `firmware/`.
These checks do not require an ESP32 or panel.

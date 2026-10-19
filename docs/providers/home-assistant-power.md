# Home Assistant power provider

The optional Home Assistant integration reads one state entity and displays
its current electrical power in watts in the default layout's **Power** tile.
It uses Home Assistant's authenticated REST state endpoint and does not require
additional Python packages.

## Configure

Create a Home Assistant long-lived access token from your user profile. Keep
the token private: it grants access to your Home Assistant instance. Set all
three values in the ignored local `.env` file:

```dotenv
SLATE_HOME_ASSISTANT_URL=https://home-assistant.example.invalid
SLATE_HOME_ASSISTANT_TOKEN=<long-lived-access-token>
SLATE_HOME_ASSISTANT_ENTITY=sensor.example_power
```

Use the base URL only (without `/api`), and replace the example hostname and
entity with your own values. The entity must be a power sensor whose unit is
`W` or `kW`; kilowatt readings are converted to watts. Configure the full
`http://` or `https://` URL reachable from the Slate server. Prefer HTTPS so
the bearer token is protected in transit. If using HTTP on a trusted local
network, restrict access to that network.

When running with Docker Compose, the three variables are passed through to
the server. Restart the service after changing its environment. The server
polls Home Assistant when the cached frame is refreshed, once per
`SLATE_REFRESH_SECONDS` interval (60 seconds by default). If Home Assistant is
unreachable, the entity is missing, or the reading has an unsupported unit,
the tile shows “Unavailable”. Request failures do not log the token or URL.

The default tile is at the top right of `server/layout.json`. Move or resize
its `power` block to fit a customized screen layout.

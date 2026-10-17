# Server

The server gathers household data through independent providers, renders an
800×480 1-bit frame using an editable layout, and serves the latest frame to the
ESP32. It also provides a browser preview for layout development.

The project is being bootstrapped. The version 1 byte layout is defined in
[the image contract](../docs/architecture.md#image-contract). A minimal
development server currently serves an orientation sample and browser preview;
the renderer and editable layout are tracked by
[#6](https://github.com/mtak/Slate/issues/6). See issues
[#7](https://github.com/mtak/Slate/issues/7), and
[#8](https://github.com/mtak/Slate/issues/8) for conditional delivery,
Compose service, and HTTPS/authentication.

Run the sample server with Python 3 (no third-party packages required):

```sh
cd server
python3 app.py
```

Open <http://127.0.0.1:8000/preview> to inspect the sample. The raw frame is
available at <http://127.0.0.1:8000/api/frame/v1>.

This is intended to be a public repository; follow the [public repository
hygiene notes](../docs/architecture.md#public-repository-hygiene). Secrets
belong in deployment configuration outside source control. Providers must
remain server-side and return data through a small common interface.

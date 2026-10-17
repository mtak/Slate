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
python3 app.py
```

Open <http://127.0.0.1:8000/preview> to inspect the sample. The raw frame is
available at <http://127.0.0.1:8000/api/frame/v1>. The frame is rendered from
the sample provider and editable layout each time it is requested.

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

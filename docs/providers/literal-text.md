# Literal text provider

The literal text provider supplies text that you write yourself. It needs no
network access or credentials. Configure it with a local JSON file containing
a mapping of layout keys to strings.

## Configure literal text

Copy the generic example to a local file in `server/`:

```sh
cp server/literal-text.example.json server/literal-text.json
```

Set `SLATE_LITERAL_TEXT_FILE` to that file path when starting the server. For a
local run from `server/`, use:

```sh
export SLATE_LITERAL_TEXT_FILE=literal-text.json
```

For Docker Compose, set `SLATE_LITERAL_TEXT_FILE` in the root `.env` file to
`/config/literal-text.json`. Compose mounts the `server/` directory read-only
at `/config`, so the local file is available to the service. Keep the real
file private; Git ignores `server/literal-text.json`.

Edit the local JSON file to change the text. It must be a JSON object whose
values are strings:

```json
{
  "display_heading": "A note for today",
  "display_message": "Take a moment to enjoy the little things."
}
```

The provider reads the file again when rendering, and changes to it trigger a
new frame. If the path is set but the file is missing, unreadable, malformed,
or contains non-string values, the server reports a clear error. Literal text
keys must not duplicate values supplied by the selected data provider, current
date, or daily affirmation providers.

## Display and style the text

Add blocks for the configured keys to `server/layout.json`. The provider supplies
the words; the layout controls position and appearance. For example:

```json
{"type": "text", "key": "display_heading", "x": 48, "y": 48, "size": 42, "bold": true}
{"type": "wrapped_text", "key": "display_message", "x": 48, "y": 120, "size": 28, "max_width": 680, "max_lines": 3}
```

`text` draws a single line. `wrapped_text` wraps at word boundaries and clips
excess lines with an ellipsis. See the [layout guide](../../server/README.md#edit-the-layout)
for all options.

## Preview the example

From the repository root, copy the example and run the server on port `18045`:

```sh
cp server/literal-text.example.json server/literal-text.json
cd server
export SLATE_LITERAL_TEXT_FILE=literal-text.json
export SLATE_LAYOUT_PATH=literal-text-demo-layout.json
export SLATE_DEVICE_TOKEN=demo-token
export SLATE_REQUIRE_HTTPS=false
export SLATE_PORT=18045
python3 app.py
```

Open <http://127.0.0.1:18045/preview> and enter `demo-token` to view the
800×480 monochrome frame. The demo layout shows a large bold heading and a
wrapped message. To return to the normal sample layout, unset
`SLATE_LAYOUT_PATH` and restart the server.

![Preview of the literal text example with a bold heading and wrapped message](literal-text-demo.png)

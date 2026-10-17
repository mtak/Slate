# Literal text provider

The literal text provider supplies text that you write yourself. It needs no
network access or credentials. Configure it with a local JSON file containing
one or more named strings. Each entry creates a provider instance for one text
value, which a layout block can display.

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

Edit the local JSON file to change the message. It must be a JSON object whose
keys are layout keys and whose values are strings:

```json
{
  "literal_message": "Take a moment to enjoy the little things."
}
```

If you also want a heading, add a second entry such as
`"literal_heading": "A note for today"` and add a second text block that uses
the `literal_heading` key. That entry becomes another provider instance; there
is no special heading or message behavior.

The provider reads the file again when rendering, and changes to it trigger a
new frame. If the path is set but the file is missing, unreadable, malformed,
or contains non-string values, the server reports a clear error. Literal text
keys must not duplicate values supplied by the selected data provider, current
date, or daily affirmation providers.

## Display and style the text

Add a block for the configured key to `server/layout.json`. The provider
supplies the words; the layout controls position and appearance. For example:

```json
{"type": "wrapped_text", "key": "literal_message", "x": 48, "y": 120, "size": 28, "max_width": 680, "max_lines": 3}
```

For a single-line heading or other short text, use a `text` block and set its
`size` and `bold` options as needed. A second configured entry can supply its
key.

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
800×480 monochrome frame. The demo layout shows one wrapped message. To return
to the normal sample layout, unset
`SLATE_LAYOUT_PATH` and restart the server.

![Preview of the literal text example with one wrapped message](literal-text-demo.png)

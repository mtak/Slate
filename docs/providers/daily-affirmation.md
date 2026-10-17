# Daily affirmation provider

`DailyAffirmationProvider` supplies `affirmation_heading` and `affirmation` to
the renderer. It chooses an item from a bundled list based on the server's
local calendar date. The same item is used throughout one day, and the list
advances on the next day. It has no credentials or online dependency.

The default layout renders the heading and affirmation near the bottom of the
frame. The affirmation uses a `wrapped_text` block with a maximum width and
line count, so longer content cannot run across adjacent display sections.
Adjust its position and size in [`server/layout.json`](../../server/layout.json)
if the layout changes.

To add or revise affirmations, edit the `AFFIRMATIONS` tuple in
[`server/providers.py`](../../server/providers.py). Keep entries original,
short, cheeky, and readable in the 800×480 monochrome preview. The current set
uses an intentionally blunt, sweary tough-love voice.

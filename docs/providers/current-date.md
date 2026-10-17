# Current date provider

The server adds the current local date to the data returned by the selected
provider. It needs no credentials or network access and supplies four values
for the layout:

| Key | Value |
| --- | --- |
| `date` | Formatted date text. Defaults to `%A, %B %d`, such as `Saturday, October 17`. |
| `weekday` | Full weekday name, such as `Saturday`. |
| `day` | Day of the month without a leading zero, such as `17`. |
| `month` | Full month name, such as `October`. |

## Configure the date format

For Docker Compose, set `SLATE_DATE_FORMAT` in the local `.env` file. For a
direct local run, export it before starting the server. It accepts Python
[`strftime` format codes](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes).
For example, `%A %d %B` formats a date as `Saturday 17 October`. Weekday and
month names use the server process locale.

Set `TZ` to an IANA timezone such as `Europe/Amsterdam` to control which local
date is displayed. Compose defaults to `UTC`; local server runs use the
machine's timezone.

## Display the date

The sample layout uses a `text` block for the formatted `date` value and a
`calendar` block for the weekday, day, and month. Edit `server/layout.json` to
move, resize, or remove the calendar icon. See the
[layout guide](../../server/README.md#edit-the-layout) for all calendar block
options.

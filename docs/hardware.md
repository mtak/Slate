# Hardware notes

## Confirmed setup

- ESP32 (ESP-WROOM-32) on a DevKit V1
- Waveshare e-Paper Driver HAT Rev 2.2
- HAT display configuration: **0.47R**
- HAT interface configuration: **4-line SPI**
- 7.5-inch black-and-white panel, **800×480**
- Wiring is tested and known to work; see [wiring.jpeg](wiring.jpeg).

Visible panel markings: `DEP607508NU790F30` and `N2104P-0117-01-10`. These have
not been matched to a public Waveshare revision label or controller profile.
The wiring photograph also shows `FPC-8612` printed on the flex cable; that
marking has not been mapped to a controller profile either. The confirmed
control wiring is BUSY 4, RST 21, DC 22, CS 5, CLK 18, and DIN 23. Keep the
existing wiring and HAT switch settings.

## Identifying the panel revision

Waveshare's 7.5-inch manual describes V1 as 640×384 and V2 as 800×480. It says
to look for a `V2` label on the back of the panel; production revisions and
their example programs can differ. If a label is hidden by the mounted HAT,
inspect the exposed back/edge only if it can be done without stressing the
panel's fragile flex cable. There is no need to dismantle the assembly just to
read a revision label: a diagnostic firmware test can validate a suitable
800×480 profile against the working hardware. The panel is currently enclosed
in a case, and the case will not be removed to expose hidden markings. No
reliable non-destructive evidence currently identifies the exact panel revision
or its sale date, so leave both unknown.

The 0.47R resistor and 4-line SPI selections are already known and validated,
so they are not unresolved wiring questions.

## Driver-profile diagnostic

Waveshare's [7.5-inch HAT manual](https://www.waveshare.com/wiki/7.5inch_e-Paper_HAT_Manual)
identifies V2 as 800×480 and V1 as 640×384. It also distinguishes two V2
program variants: `7.5V2` for versions sold after September 2023 and
`7.5V2_old` for versions sold before then. This makes the V2 family the
candidate family for this panel, but resolution alone does not identify its
controller revision or manufacture/sale date. Both example profiles have
since been tested against this panel.

Do not infer that `N2104` is a date code without evidence from Waveshare. The
diagnostic confirmed both profile variants work, so the default newer profile
is selected; exact panel revision remains unidentified.

The firmware contains a one-shot diagnostic build for both Waveshare profiles.
It uses the confirmed ESP32 wiring (BUSY 4, RST 21, DC 22, CS 5, CLK 18,
DIN 23) and a labeled 800×480 pattern with black/white blocks, a checkerboard,
and corner marks. The tested sources are Waveshare's
`EPD_7in5_V2` and `EPD_7in5_V2_old` implementations; the local SPI adapter uses
a 60-second busy timeout.

From `firmware/`, build and flash the default `slate_esp32` environment, then
repeat with `slate_esp32_v2_old`. Each is a full refresh. Record the profile
name, firmware revision, visible result, and serial busy status. A profile
passes if the full frame is correctly oriented, both pixel colors and text are
clear, the edges are not clipped, and refresh completes without a busy timeout.
Keep the existing HAT settings and wiring unchanged. Stop if either profile
produces persistent noise or abnormal behavior.

### Hardware test results (2026-10-17)

The initial profile runs used incorrect control GPIO mappings and timed out;
those results are invalid. With the confirmed wiring (BUSY 4, RST 21, DC 22,
CS 5, CLK 18, DIN 23), both the `slate_esp32_v2_old` and `slate_esp32` builds
displayed their complete diagnostic frames. The user confirmed that both
frames were correctly oriented and that the blocks, checkerboard, and all
four corner marks were visible. Both `7.5V2_old` and `7.5V2` are therefore
compatible with the panel.

The default `7.5V2` profile is selected for firmware use; the panel revision
and sale date remain unknown, so the test does not identify which controller
revision is inside. The `7.5V2_old` environment remains available as a tested
alternative. The 0.47R and 4-line SPI settings were not changed. The user's
approximate 3.3 V measurement at HAT VCC/GND is also recorded.

The profile sources are pinned and attributed in
[`firmware/vendor/waveshare/README.md`](../firmware/vendor/waveshare/README.md).
Both profiles are confirmed compatible with the panel. Keep `7.5V2` as the
default and retain `7.5V2_old` as a validated alternative.

### Partial-refresh comparison (2026-10-17)

A first controlled comparison used four high-contrast full-screen frames, with
two partial updates between full updates. Serial output confirmed the partial
updates ran, but the user saw no clear difference in flashing. A follow-up used
a 160×80 partial window over a static diagnostic frame. The user observed
flashing in the subwindow followed by the checkerboard appearing there. This
confirms the small-window update works and confines the visible activity to
that window, although it still flashes locally. The test then performed a full
refresh to restore the baseline and clear ghosting. Both `7.5V2` and
`7.5V2_old` diagnostic builds compiled; the user-visible small-window result
was observed with `7.5V2`. This does not identify the panel revision. The
device's saved original firmware was restored after the diagnostic.

A local changed-region diagnostic then displayed the static baseline, compared
incoming rows in place, and sent the detected window through the same strided
partial-transfer routine as the frame client. The firmware reported the
expected 104×16 window at x=80, y=286, and completed without a busy timeout.
The user observed two separate black bars at those positions on the panel and
reported that the smaller region flashed a couple of times, only within that
region. This confirms the local diff and strided partial update produced the
intended visible marks and confined the observed activity to its computed
window. The pre-test firmware image was restored afterward.

This result differs from Waveshare's [7.5-inch HAT manual](https://www.waveshare.com/wiki/7.5inch_e-Paper_HAT_Manual),
which says a full refresh flashes several times to clear afterimages and a
partial refresh has no flickering effect. The manual lists approximate refresh
times of 4 seconds full and 0.4 seconds partial, with actual results varying.
The Waveshare manual describes partial refresh as having no flickering effect;
on this panel the small-window result shows that this should be interpreted as
avoiding the full-screen flash, not as guaranteeing a completely flash-free
changed region. A full refresh after partial updates remains useful for clearing
ghosting, as Waveshare recommends after several partial updates. The exact
panel revision remains unknown because its markings are concealed by the case,
which the user does not want to remove.

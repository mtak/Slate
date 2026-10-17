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
800×480 profile against the working hardware.

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

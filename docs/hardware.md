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
Keep the existing wiring and HAT switch settings. Use the initial diagnostic
image to confirm the appropriate driver initialization profile before adding
higher-level behavior.

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
controller or initialization sequence. The markings above have not been
matched to a profile or manufacture/sale date; neither variant is confirmed.

If a V2 label or reliable sale/revision evidence is visible without stressing
the panel or flex cable, use it to choose the first candidate. Otherwise,
compare the Waveshare `7.5V2` and `7.5V2_old` profiles one at a time. Do not
infer that `N2104` is a date code without evidence from Waveshare.

When the firmware build is available, test only a driver profile documented
for an 800×480 black-and-white 7.5-inch panel. Record the profile name and
source alongside the result. Keep the validated wiring and HAT settings fixed
while testing. The diagnostic should initialize the panel, clear it, and draw
a simple pattern with distinct black and white blocks plus readable text. A
successful result has the correct orientation, complete image, no persistent
noise or clipped areas, and a clean return from refresh/busy handling. If a
profile fails any of these checks, stop and investigate the panel markings and
driver support before trying another initialization sequence.

The selected profile remains **unconfirmed** until this diagnostic has been
run on the physical display. Record the firmware revision, profile, observed
result, and any limitations here after hardware validation.

Waveshare's [official driver repository](https://github.com/waveshareteam/e-Paper)
contains the profile implementations and example diagnostics; use the
ESP32/Arduino implementation when the firmware framework is established.

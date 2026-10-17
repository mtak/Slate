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

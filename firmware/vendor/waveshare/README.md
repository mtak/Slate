# Waveshare driver source

`e-Paper/EPD_7in5_V2.cpp` and `EPD_7in5_V2.h`, plus the corresponding
`_old` files, are from Waveshare's official
[e-Paper repository](https://github.com/waveshareteam/e-Paper),
`Arduino_R4/src/e-Paper`, commit
[`a794fbc39656b0f93938d1ffb3fdc77eaed9e9fc`](https://github.com/waveshareteam/e-Paper/tree/a794fbc39656b0f93938d1ffb3fdc77eaed9e9fc).
The upstream permission and warranty notices are retained in each source file.

The `Config` files are Slate's ESP32 Arduino adapter for the existing DevKit
wiring. The busy wait in each driver source has been bounded at 60 seconds so a
failed profile or connection cannot leave the diagnostic stuck indefinitely.

#pragma once

#include <Arduino.h>
#include <SPI.h>
#include <stdint.h>

using UBYTE = uint8_t;
using UWORD = uint16_t;
using UDOUBLE = uint32_t;

// GPIO mapping from the documented ESP32 DevKit V1 wiring.
#define EPD_SCK_PIN 18
#define EPD_MOSI_PIN 23
#define EPD_CS_PIN 15
#define EPD_DC_PIN 27
#define EPD_RST_PIN 26
#define EPD_BUSY_PIN 25

#define DEV_Digital_Write(pin, value) digitalWrite((pin), (value) ? HIGH : LOW)
#define DEV_Digital_Read(pin) digitalRead(pin)
#define DEV_Delay_ms(ms) delay(ms)

extern bool slateEpdBusyTimeout;

UBYTE DEV_Module_Init(void);
void DEV_Module_Exit(void);
void DEV_SPI_WriteByte(UBYTE data);
void DEV_SPI_Write_nByte(UBYTE *data, UDOUBLE length);

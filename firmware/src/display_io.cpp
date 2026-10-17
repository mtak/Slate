#include <SPI.h>

#include "../vendor/waveshare/Config/DEV_Config.h"

bool slateEpdBusyTimeout = false;

UBYTE DEV_Module_Init(void) {
  pinMode(EPD_BUSY_PIN, INPUT);
  pinMode(EPD_RST_PIN, OUTPUT);
  pinMode(EPD_DC_PIN, OUTPUT);
  pinMode(EPD_CS_PIN, OUTPUT);
  digitalWrite(EPD_CS_PIN, HIGH);

  SPI.begin(EPD_SCK_PIN, -1, EPD_MOSI_PIN, EPD_CS_PIN);
  SPI.beginTransaction(SPISettings(2000000, MSBFIRST, SPI_MODE0));
  return 0;
}

void DEV_SPI_WriteByte(UBYTE data) {
  SPI.transfer(data);
}

void DEV_SPI_Write_nByte(UBYTE *data, UDOUBLE length) {
  for (UDOUBLE index = 0; index < length; ++index) {
    DEV_SPI_WriteByte(data[index]);
  }
}

void DEV_Module_Exit(void) {
  SPI.endTransaction();
  SPI.end();
}

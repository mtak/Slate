#pragma once

#include "frame.h"

// Include after the selected Waveshare driver implementation in this
// translation unit so its static SPI helpers remain available.
inline void slateDisplayStridedPartial(UBYTE *image, UDOUBLE xStart,
                                       UDOUBLE yStart, UDOUBLE xEnd,
                                       UDOUBLE yEnd) {
  const UDOUBLE widthBytes = (xEnd - xStart) / 8;
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  EPD_SendCommand(0x91);
  EPD_SendCommand(0x90);
  EPD_SendData((xStart >> 8) & 0xFF);
  EPD_SendData(xStart & 0xFF);
  EPD_SendData(((xEnd - 1) >> 8) & 0xFF);
  EPD_SendData((xEnd - 1) & 0xFF);
  EPD_SendData((yStart >> 8) & 0xFF);
  EPD_SendData(yStart & 0xFF);
  EPD_SendData(((yEnd - 1) >> 8) & 0xFF);
  EPD_SendData((yEnd - 1) & 0xFF);
#else
  EPD_SendCommand(0x50);
  EPD_SendData(0xA9);
  EPD_SendData(0x07);
  EPD_SendCommand(0x91);
  EPD_SendCommand(0x90);
  EPD_SendData(xStart / 256);
  EPD_SendData(xStart % 256);
  EPD_SendData(xEnd / 256);
  EPD_SendData(xEnd % 256 - 1);
  EPD_SendData(yStart / 256);
  EPD_SendData(yStart % 256);
  EPD_SendData(yEnd / 256);
  EPD_SendData(yEnd % 256 - 1);
#endif
  EPD_SendData(0x01);
  EPD_SendCommand(0x13);
  for (UDOUBLE y = yStart; y < yEnd; ++y) {
    EPD_SendData2(image + y * slate::kBytesPerRow + xStart / 8, widthBytes);
  }
  EPD_7IN5_V2_TurnOnDisplay();
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  EPD_SendCommand(0x92);
#endif
}

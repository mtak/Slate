#pragma once

#include "frame.h"
#include "panel_window.h"

// Include after the selected Waveshare driver implementation in this
// translation unit so its static SPI helpers remain available.
inline void slateDisplayStridedPartial(UBYTE *image, UDOUBLE xStart,
                                       UDOUBLE yStart, UDOUBLE xEnd,
                                       UDOUBLE yEnd) {
  const UDOUBLE widthBytes = (xEnd - xStart) / 8;
  const slate::panel::CoordinateBytes xEndBytes =
      slate::panel::encodeInclusiveEnd(xEnd);
  const slate::panel::CoordinateBytes yEndBytes =
      slate::panel::encodeInclusiveEnd(yEnd);
#if defined(SLATE_EPD_PROFILE_V2_OLD)
  EPD_SendCommand(0x91);
  EPD_SendCommand(0x90);
  EPD_SendData((xStart >> 8) & 0xFF);
  EPD_SendData(xStart & 0xFF);
  EPD_SendData(xEndBytes.high);
  EPD_SendData(xEndBytes.low);
  EPD_SendData((yStart >> 8) & 0xFF);
  EPD_SendData(yStart & 0xFF);
  EPD_SendData(yEndBytes.high);
  EPD_SendData(yEndBytes.low);
#else
  EPD_SendCommand(0x50);
  EPD_SendData(0xA9);
  EPD_SendData(0x07);
  EPD_SendCommand(0x91);
  EPD_SendCommand(0x90);
  EPD_SendData(xStart / 256);
  EPD_SendData(xStart % 256);
  EPD_SendData(xEndBytes.high);
  EPD_SendData(xEndBytes.low);
  EPD_SendData(yStart / 256);
  EPD_SendData(yStart % 256);
  EPD_SendData(yEndBytes.high);
  EPD_SendData(yEndBytes.low);
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

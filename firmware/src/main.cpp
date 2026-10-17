#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  Serial.println("Slate firmware bootstrap");
}

void loop() {
  delay(1000);
}

// ESP32-S3 USB CDC <-> UART1 transparent bridge for the hoverboard's USART3.
// S3 GPIO17 (TX) -> board RX (PB11), S3 GPIO18 (RX) <- board TX (PB10), GND -> GND.
// Never connect the sideboard cable's 15 V wire.
// Safety: if the PC sends nothing for 200 ms, PC->board forwarding stops and any
// buffered partial frame is dropped; the board's own ~0.8 s serial timeout then zeroes torque.
#include <Arduino.h>

static const int UART_TX_PIN = 17;
static const int UART_RX_PIN = 18;
static const uint32_t BAUD = 115200;
static const uint32_t PC_SILENCE_MS = 200;

static uint32_t lastPcByteMs = 0;

void setup() {
  Serial.begin(BAUD);  // USB CDC (baud ignored)
  Serial1.begin(BAUD, SERIAL_8N1, UART_RX_PIN, UART_TX_PIN);
}

void loop() {
  uint8_t buf[64];

  // PC -> board
  int n = Serial.available();
  if (n > 0) {
    if (n > (int)sizeof(buf)) n = sizeof(buf);
    n = Serial.readBytes(buf, n);
    lastPcByteMs = millis();
    Serial1.write(buf, n);
  } else if (millis() - lastPcByteMs > PC_SILENCE_MS) {
    // PC went quiet: forward nothing further (nothing queued on our side).
    while (Serial.available()) Serial.read();
  }

  // board -> PC
  n = Serial1.available();
  if (n > 0) {
    if (n > (int)sizeof(buf)) n = sizeof(buf);
    n = Serial1.readBytes(buf, n);
    Serial.write(buf, n);
  }
}

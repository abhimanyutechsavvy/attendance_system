#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9

MFRC522 rfid(SS_PIN, RST_PIN);
const String targetID = "922422290";

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ;
  }

  SPI.begin();
  rfid.PCD_Init();
  Serial.println("RFID bridge ready");
}

void loop() {
  if (!rfid.PICC_IsNewCardPresent()) {
    delay(100);
    return;
  }

  if (!rfid.PICC_ReadCardSerial()) {
    return;
  }

  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uid += String(rfid.uid.uidByte[i], DEC);
  }

  Serial.print("UID:");
  Serial.println(uid);

  if (uid == targetID) {
    Serial.println("ACCESS_GRANTED");
  } else {
    Serial.println("ACCESS_DENIED");
  }

  rfid.PICC_HaltA();
  delay(500);
}

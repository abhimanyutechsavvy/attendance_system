#include <SPI.h>
#include <MFRC522.h>

const int SS_PIN = 10;
const int RST_PIN = 9;

const int JOYSTICK_X_PIN = A0;
const int JOYSTICK_Y_PIN = A1;
const int JOYSTICK_BUTTON_PIN = 2;

const unsigned long JOYSTICK_REPORT_INTERVAL_MS = 80;
const unsigned long RFID_COOLDOWN_MS = 1200;

MFRC522 rfid(SS_PIN, RST_PIN);

unsigned long lastJoystickReportAt = 0;
unsigned long lastUidSentAt = 0;
String lastUid = "";

void setup() {
  Serial.begin(9600);
  pinMode(JOYSTICK_BUTTON_PIN, INPUT_PULLUP);

  SPI.begin();
  rfid.PCD_Init();

  Serial.println("SYSTEM:ARDUINO_BRIDGE_READY");
}

void sendJoystickState() {
  if (millis() - lastJoystickReportAt < JOYSTICK_REPORT_INTERVAL_MS) {
    return;
  }

  int x = analogRead(JOYSTICK_X_PIN);
  int y = analogRead(JOYSTICK_Y_PIN);
  int button = digitalRead(JOYSTICK_BUTTON_PIN);

  Serial.print("JOY:");
  Serial.print(x);
  Serial.print(",");
  Serial.print(y);
  Serial.print(",");
  Serial.println(button);

  lastJoystickReportAt = millis();
}

String readUidString() {
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  return uid;
}

void sendRfidState() {
  if (!rfid.PICC_IsNewCardPresent()) {
    return;
  }

  if (!rfid.PICC_ReadCardSerial()) {
    return;
  }

  String uid = readUidString();
  bool cooldownActive = (uid == lastUid) && (millis() - lastUidSentAt < RFID_COOLDOWN_MS);

  if (!cooldownActive) {
    Serial.print("RFID:");
    Serial.println(uid);
    lastUid = uid;
    lastUidSentAt = millis();
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

void loop() {
  sendJoystickState();
  sendRfidState();
}

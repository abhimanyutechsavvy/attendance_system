const int xPin = A0;
const int yPin = A1;
const int buttonPin = 2;
const unsigned long reportIntervalMs = 80;

unsigned long lastReportAt = 0;

void setup() {
  Serial.begin(9600);
  pinMode(buttonPin, INPUT_PULLUP);
  Serial.println("SYSTEM:JOYSTICK_READY");
}

void loop() {
  if (millis() - lastReportAt < reportIntervalMs) {
    return;
  }

  int x = analogRead(xPin);
  int y = analogRead(yPin);
  int btn = digitalRead(buttonPin);

  Serial.print("JOY:");
  Serial.print(x);
  Serial.print(",");
  Serial.print(y);
  Serial.print(",");
  Serial.println(btn);

  lastReportAt = millis();
}

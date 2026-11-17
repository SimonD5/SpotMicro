#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

#define OE_PIN 2 // Broche OE sur D2 (Active-LOW : HIGH = sorties coupées)

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

void setup() {
  // 1. Coupure immédiate des sorties PWM via OE (D2 -> HIGH)
  digitalWrite(OE_PIN, HIGH);
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH);

  Serial.begin(9600);
  while (!Serial && millis() < 4000);

  Serial.println("\n=========================================");
  Serial.println(" ARRET DE SECURITE SERVOS (OE -> HIGH)   ");
  Serial.println("=========================================");

  // 2. Mise au repos des registres du PCA9685 tout en maintenant OE à HIGH
  if (!pwm.begin()) {
    return; // OE reste HIGH, meme si le PCA9685 ne repond pas.
  }
  for (uint8_t ch = 0; ch < 16; ch++) {
    pwm.setPWM(ch, 0, 4096);
  }
  digitalWrite(OE_PIN, HIGH);

  Serial.println("[OK] Broche OE (D2) a HIGH -> Sorties servos coupees.");
}

void loop() {
  digitalWrite(OE_PIN, HIGH);
  delay(1000);
}

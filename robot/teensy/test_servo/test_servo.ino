#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

#define OE_PIN 2            // Broche OE (Output Enable) reliée à D2 sur le Teensy
#define SERVO_CHANNEL 0     // Canal du servo à tester

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);
bool pwmReady = false;

// Plage d'impulsion des servos DS3218MG (50 Hz = période de 20 000 µs)
#define US_MIN  500   // 0°
#define US_MAX  2500  // 180°

int currentAngle = 90;

void setServoAngle(uint8_t channel, int angle) {
  if (channel >= 16) {
    return;
  }
  angle = constrain(angle, 0, 180);
  int us = map(angle, 0, 180, US_MIN, US_MAX);
  us = constrain(us, US_MIN, US_MAX);
  int ticks = map(us, 0, 20000, 0, 4095);
  pwm.setPWM(channel, 0, ticks);
}

void moveSlow(uint8_t channel, int targetAngle, int stepDelayMs = 30) {
  targetAngle = constrain(targetAngle, 0, 180);
  if (stepDelayMs < 0) {
    stepDelayMs = 0;
  }
  if (targetAngle > currentAngle) {
    for (int a = currentAngle; a <= targetAngle; a++) {
      setServoAngle(channel, a);
      delay(stepDelayMs);
    }
  } else {
    for (int a = currentAngle; a >= targetAngle; a--) {
      setServoAngle(channel, a);
      delay(stepDelayMs);
    }
  }
  currentAngle = targetAngle;
}

void setup() {
  // 1. Maintenir la broche OE (Active LOW) à HIGH pendant l'initialisation
  digitalWrite(OE_PIN, HIGH);
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH);

  Serial.begin(9600);
  while (!Serial && millis() < 4000);

  Serial.println("\n=======================================");
  Serial.println("   TEST PCA9685 + SERVO (OE sur D2)    ");
  Serial.println("=======================================");

  // 2. Test direct de communication I2C avec le PCA9685
  Wire.begin();
  Wire.beginTransmission(0x40);
  byte error = Wire.endTransmission();
  if (error == 0) {
    Serial.println("[OK] PCA9685 repond bien a l'adresse I2C 0x40");
  } else {
    Serial.print("[ERREUR] PCA9685 ne repond pas sur I2C (Code : ");
    Serial.print(error);
    Serial.println(")");
  }

  // 3. Initialisation du driver PWM et remise à zéro des canaux avant OE=LOW
  if (!pwm.begin()) {
    Serial.println("[ERREUR] PCA9685 indisponible, OE reste HIGH.");
    return;
  }
  pwm.setPWMFreq(50);
  delay(10);
  for (uint8_t ch = 0; ch < 16; ch++) {
    if (pwm.setPWM(ch, 0, 4096) != 0) {
      Serial.println("[ERREUR] Initialisation PWM incomplete, OE reste HIGH.");
      return;
    }
  }

  pwmReady = true;

  // Calage initial doux à 90°
  Serial.println("--> Prise de position initiale (90 degres)");
  setServoAngle(SERVO_CHANNEL, 90);
  currentAngle = 90;

  // 4. Activation des sorties PWM (OE Active LOW)
  digitalWrite(OE_PIN, LOW);
  Serial.println("[OK] Broche OE (D2) forcee a LOW -> Sorties PWM activees");
  delay(1000);
}

void loop() {
  if (!pwmReady) {
    delay(1000);
    return;
  }
  Serial.println("--> Balayage lent vers 80 degres");
  moveSlow(SERVO_CHANNEL, 80, 30);
  delay(500);

  Serial.println("--> Balayage lent vers 100 degres");
  moveSlow(SERVO_CHANNEL, 100, 30);
  delay(500);

  Serial.println("--> Retour au neutre (90 degres)");
  moveSlow(SERVO_CHANNEL, 90, 30);
  delay(2000);
}

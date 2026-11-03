#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

#define OE_PIN 2         // Broche OE sur D2 (Active-LOW)

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

// Impulsions DS3218MG (50 Hz -> période de 20 000 µs)
#define US_MIN  500   // 0°
#define US_MAX  2500  // 180°

// Structure de cartographie des canaux du PCA9685
struct ServoConfig {
  uint8_t channel;
  const char* label;
};

const ServoConfig SERVOS[] = {
  {0,  "Avant Gauche - Pied"},
  {1,  "Avant Gauche - Genou"},
  {2,  "Avant Gauche - Epaule"},
  {4,  "Avant Droit - Pied"},
  {5,  "Avant Droit - Genou"},
  {6,  "Avant Droit - Epaule"},
  {8,  "Arriere Gauche - Pied"},
  {9,  "Arriere Gauche - Genou"},
  {10, "Arriere Gauche - Epaule"},
  {12, "Arriere Droit - Pied"},
  {13, "Arriere Droit - Genou"},
  {14, "Arriere Droit - Epaule"}
};

const uint8_t NUM_SERVOS = sizeof(SERVOS) / sizeof(SERVOS[0]);

void setServoAngle(uint8_t channel, int angle) {
  angle = constrain(angle, 0, 180);
  int us = map(angle, 0, 180, US_MIN, US_MAX);
  int ticks = map(us, 0, 20000, 0, 4095);
  pwm.setPWM(channel, 0, ticks);
}

void setup() {
  Serial.begin(9600);
  while (!Serial && millis() < 4000);

  Serial.println("\n=========================================");
  Serial.println(" CALAGE PROGRESSIF PAR CANAL MAPPÉ A 90° ");
  Serial.println("=========================================");

  // 1. Activer le PCA9685 via OE (D2 -> LOW)
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, LOW);
  Serial.println("[OK] OE force a LOW -> PCA9685 active.\n");

  // 2. Initialiser le driver PWM
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(100);

  // 3. Activer chaque servo un par un selon le mapping réel
  for (uint8_t i = 0; i < NUM_SERVOS; i++) {
    uint8_t ch = SERVOS[i].channel;
    const char* name = SERVOS[i].label;

    Serial.print("--> Canal ");
    if (ch < 10) Serial.print("0");
    Serial.print(ch);
    Serial.print(" [");
    Serial.print(name);
    Serial.println("] -> 90 degres");

    setServoAngle(ch, 90);

    // Pause de 500 ms pour étaler l'appel de courant
    delay(500);
  }

  Serial.println("\n[OK] Les 12 servos sont cales et maintenus a 90 degres.");
}

void loop() {
  delay(1000);
}
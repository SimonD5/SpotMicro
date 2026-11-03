#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

#define OE_PIN 2

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

// Impulsions DS3218MG (50 Hz -> période de 20 000 µs)
#define US_MIN  500   // 0°
#define US_MAX  2500  // 180°

// Hard-limit de sécurité absolue : aucun servo ne pourra dépasser cette plage [85°, 95°]
#define SAFETY_MIN  85
#define SAFETY_MAX  95

// Mapping des 12 canaux PCA9685
// Ordre : FL(Pied, Genou, Epaule), FR(Pied, Genou, Epaule), RL(Pied, Genou, Epaule), RR(Pied, Genou, Epaule)
const uint8_t CHANNELS[12] = {0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14};

int currentAngles[12] = {90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90};

void setServoAngle(uint8_t channel, int angle) {
  // Verrou de sécurité
  angle = constrain(angle, SAFETY_MIN, SAFETY_MAX);
  
  int us = map(angle, 0, 180, US_MIN, US_MAX);
  int ticks = map(us, 0, 20000, 0, 4095);
  pwm.setPWM(channel, 0, ticks);
}

// Déplacement simultané et fluide des 12 servos vers des angles cibles
void moveAllSmooth(const int targetAngles[12], int stepDelayMs = 30) {
  bool moving = true;
  while (moving) {
    moving = false;
    for (int i = 0; i < 12; i++) {
      int target = constrain(targetAngles[i], SAFETY_MIN, SAFETY_MAX);
      
      if (currentAngles[i] < target) {
        currentAngles[i]++;
        moving = true;
      } else if (currentAngles[i] > target) {
        currentAngles[i]--;
        moving = true;
      }
      setServoAngle(CHANNELS[i], currentAngles[i]);
    }
    delay(stepDelayMs); // Pause en ms entre chaque degré pour ajuster la vitesse
  }
}

void setup() {
  Serial.begin(9600);
  while (!Serial && millis() < 4000);

  Serial.println("\n=========================================");
  Serial.println(" MICRO-MARCHE SECURISEE (+/- 5° MAX) ");
  Serial.println("=========================================");

  // Activation du PCA9685 via OE (D2 -> LOW)
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, LOW);

  pwm.begin();
  pwm.setPWMFreq(50);
  delay(100);

  // Position neutre de départ : 90° sur toutes les articulations
  int neutral[12] = {90, 90, 90,  90, 90, 90,  90, 90, 90,  90, 90, 90};
  moveAllSmooth(neutral, 15);
  
  Serial.println("[OK] Robot cale au neutre (90 degres). Attente 2s...");
  delay(2000);
}

void loop() {
  int neutral[12] = {90, 90, 90,  90, 90, 90,  90, 90, 90,  90, 90, 90};

  // 1. Lever léger du couple diagonal 1 (Avant-Gauche + Arrière-Droit) & micro-avance (-3° pied/genou, +3° épaule)
  Serial.println("--> Micro-pas : Diagonale 1 (FL + RR)...");
  int stepDiag1[12] = {
    87, 87, 93,   // FL: Leve de 3° + Avance de 3°
    90, 90, 90,   // FR: Fixe au sol
    90, 90, 90,   // RL: Fixe au sol
    87, 87, 93    // RR: Leve de 3° + Avance de 3°
  };
  moveAllSmooth(stepDiag1, 35); // Vitesse lente (35ms par degré)
  delay(300);

  // Pose des pieds & retour au neutre
  moveAllSmooth(neutral, 35);
  delay(500);

  // 2. Lever léger du couple diagonal 2 (Avant-Droit + Arrière-Gauche) & micro-avance (-3° pied/genou, +3° épaule)
  Serial.println("--> Micro-pas : Diagonale 2 (FR + RL)...");
  int stepDiag2[12] = {
    90, 90, 90,   // FL: Fixe au sol
    87, 87, 93,   // FR: Leve de 3° + Avance de 3°
    87, 87, 93,   // RL: Leve de 3° + Avance de 3°
    90, 90, 90    // RR: Fixe au sol
  };
  moveAllSmooth(stepDiag2, 35);
  delay(300);

  // Pose des pieds & retour au neutre
  moveAllSmooth(neutral, 35);
  delay(1000);
}
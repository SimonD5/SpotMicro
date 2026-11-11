#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

#define OE_PIN 2

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

#define US_MIN  500   // 0°
#define US_MAX  2500  // 180°

struct Joint {
  uint8_t channel;
  const char* label;
  int currentAngle;
  int minAngle;
  int maxAngle;
};

Joint joints[12] = {
  {0,  "AV-G [0] Pied/Genou_bas", 90, 90, 90},
  {1,  "AV-G [1] Cuisse/Genou_haut", 90, 90, 90},
  {2,  "AV-G [2] Epaule", 90, 90, 90},
  {4,  "AV-D [3] Pied/Genou_bas", 90, 90, 90},
  {5,  "AV-D [4] Cuisse/Genou_haut", 90, 90, 90},
  {6,  "AV-D [5] Epaule", 90, 90, 90},
  {8,  "AR-G [6] Pied/Genou_bas", 90, 90, 90},
  {9,  "AR-G [7] Cuisse/Genou_haut", 90, 90, 90},
  {10, "AR-G [8] Epaule", 90, 90, 90},
  {12, "AR-D [9] Pied/Genou_bas", 90, 90, 90},
  {13, "AR-D [10] Cuisse/Genou_haut", 90, 90, 90},
  {14, "AR-D [11] Epaule", 90, 90, 90}
};

int activeJointIdx = -1; // -1 = Aucun servo sélectionné

void setAngleDirect(uint8_t channel, int angle) {
  angle = constrain(angle, 0, 180);
  int us = map(angle, 0, 180, US_MIN, US_MAX);
  int ticks = map(us, 0, 20000, 0, 4095);
  pwm.setPWM(channel, 0, ticks);
}

void moveJointSmooth(int idx, int targetAngle, int stepDelayMs = 15) {
  targetAngle = constrain(targetAngle, 0, 180);
  int current = joints[idx].currentAngle;

  if (targetAngle > current) {
    for (int a = current; a <= targetAngle; a++) {
      setAngleDirect(joints[idx].channel, a);
      delay(stepDelayMs);
    }
  } else {
    for (int a = current; a >= targetAngle; a--) {
      setAngleDirect(joints[idx].channel, a);
      delay(stepDelayMs);
    }
  }

  joints[idx].currentAngle = targetAngle;
  if (targetAngle < joints[idx].minAngle) joints[idx].minAngle = targetAngle;
  if (targetAngle > joints[idx].maxAngle) joints[idx].maxAngle = targetAngle;
}

void printMenu() {
  Serial.println("\n==================================================");
  Serial.println("     TEST AMPLITUDE & CALIBRATION DES SERVOS     ");
  Serial.println("==================================================");
  Serial.println("LISTE DES SERVOS (Saisir un numéro 0 à 11) :");
  for (int i = 0; i < 12; i++) {
    Serial.print("  [");
    if (i < 10) Serial.print(" ");
    Serial.print(i);
    Serial.print("] Canal PCA ");
    if (joints[i].channel < 10) Serial.print(" ");
    Serial.print(joints[i].channel);
    Serial.print(" : ");
    Serial.print(joints[i].label);
    Serial.print(" (Actuel: ");
    Serial.print(joints[i].currentAngle);
    Serial.println("°)");
  }
  Serial.println("\nCOMMANDES GLOBALES :");
  Serial.println("  'r' : Afficher le tableau récapitulatif des Min/Max enregistrés");
  Serial.println("  'all90' : Remettre tous les servos à 90°");
  Serial.println("--------------------------------------------------");
  Serial.print("Choisissez un servo (0 à 11) > ");
}

void printReport() {
  Serial.println("\n==================================================");
  Serial.println("   TABLEAU RECAPITULATIF DES AMPLITUDES MESUREES  ");
  Serial.println("==================================================");
  Serial.println("Index | Canal | Articulation             | MIN  | MAX  | Amplitude");
  Serial.println("------+-------+--------------------------+------+------+----------");
  for (int i = 0; i < 12; i++) {
    Serial.print("  ");
    if (i < 10) Serial.print(" ");
    Serial.print(i);
    Serial.print("  |   ");
    if (joints[i].channel < 10) Serial.print(" ");
    Serial.print(joints[i].channel);
    Serial.print("  | ");
    
    char labelBuf[26];
    snprintf(labelBuf, sizeof(labelBuf), "%-24s", joints[i].label);
    Serial.print(labelBuf);
    
    Serial.print(" | ");
    if (joints[i].minAngle < 100) Serial.print(" ");
    if (joints[i].minAngle < 10) Serial.print(" ");
    Serial.print(joints[i].minAngle);
    Serial.print("° | ");
    if (joints[i].maxAngle < 100) Serial.print(" ");
    if (joints[i].maxAngle < 10) Serial.print(" ");
    Serial.print(joints[i].maxAngle);
    Serial.print("° | ");
    Serial.print(joints[i].maxAngle - joints[i].minAngle);
    Serial.println("°");
  }
  Serial.println("==================================================\n");
}

void setup() {
  Serial.begin(9600);
  while (!Serial && millis() < 4000);

  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, LOW); // Active OE PCA9685

  pwm.begin();
  pwm.setPWMFreq(50);
  delay(100);

  // Positionner tous les servos à 90° au démarrage
  for (int i = 0; i < 12; i++) {
    setAngleDirect(joints[i].channel, 90);
    delay(100);
  }

  printMenu();
}

void processInput(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  // 1. Commandes d'action globale
  if (cmd == "r" || cmd == "report") {
    printReport();
    if (activeJointIdx == -1) printMenu();
    return;
  }

  if (cmd == "all90") {
    Serial.println("--> Remise de tous les servos à 90°...");
    for (int i = 0; i < 12; i++) {
      moveJointSmooth(i, 90, 10);
    }
    Serial.println("[OK] Tous les servos sont à 90°.");
    if (activeJointIdx != -1) {
      Serial.print("Servo actif : ");
      Serial.println(joints[activeJointIdx].label);
    } else {
      printMenu();
    }
    return;
  }

  // 2. Mode SELECTION DU SERVO (activeJointIdx == -1)
  if (activeJointIdx == -1) {
    int inputVal = cmd.toInt();
    int foundIdx = -1;

    // Recherche par index (0..11) ou par numéro de canal (0,1,2,4,5,6,8,9,10,12,13,14)
    if (inputVal >= 0 && inputVal <= 11 && cmd != "00") {
      foundIdx = inputVal;
    } else {
      for (int i = 0; i < 12; i++) {
        if (joints[i].channel == inputVal) {
          foundIdx = i;
          break;
        }
      }
    }

    if (foundIdx != -1) {
      activeJointIdx = foundIdx;
      Serial.println("\n--------------------------------------------------");
      Serial.print(">>> SERVO ACTIF : [");
      Serial.print(activeJointIdx);
      Serial.print("] ");
      Serial.println(joints[activeJointIdx].label);
      Serial.print("    Angle actuel : ");
      Serial.print(joints[activeJointIdx].currentAngle);
      Serial.println("°");
      Serial.println("    CONSIGNES :");
      Serial.println("    - Saisir un angle direct (ex: 45, 90, 120)");
      Serial.println("    - Saisir des pas relatifs (ex: +5, -5, +1, -1, +, -)");
      Serial.println("    - Saisir 'q' pour quitter ce servo et en choisir un autre");
      Serial.println("--------------------------------------------------");
    } else {
      Serial.println(" Erreur: Servo ou canal inconnu. Reessayez.");
    }
    return;
  }

  // 3. Mode CONTRÔLE DU SERVO ACTIF (activeJointIdx != -1)
  if (cmd == "q" || cmd == "quit") {
    Serial.print("<<< Quitter le servo : ");
    Serial.println(joints[activeJointIdx].label);
    Serial.print("    Plage enregistrée pour ce servo : [ ");
    Serial.print(joints[activeJointIdx].minAngle);
    Serial.print("° -- ");
    Serial.print(joints[activeJointIdx].maxAngle);
    Serial.println("° ]\n");
    
    activeJointIdx = -1;
    printMenu();
    return;
  }

  // Calcul du nouvel angle selon la commande (+, -, +5, -5, angle direct)
  int targetAngle = joints[activeJointIdx].currentAngle;

  if (cmd == "+") targetAngle += 5;
  else if (cmd == "-") targetAngle -= 5;
  else if (cmd.startsWith("+")) targetAngle += cmd.substring(1).toInt();
  else if (cmd.startsWith("-")) targetAngle -= cmd.substring(1).toInt();
  else targetAngle = cmd.toInt();

  targetAngle = constrain(targetAngle, 0, 180);

  Serial.print("--> Déplacement de [");
  Serial.print(joints[activeJointIdx].label);
  Serial.print("] vers ");
  Serial.print(targetAngle);
  Serial.println("°...");

  moveJointSmooth(activeJointIdx, targetAngle, 15);

  Serial.print(" [OK] Position: ");
  Serial.print(joints[activeJointIdx].currentAngle);
  Serial.print("° | Min: ");
  Serial.print(joints[activeJointIdx].minAngle);
  Serial.print("° | Max: ");
  Serial.print(joints[activeJointIdx].maxAngle);
  Serial.println("°");
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    processInput(input);
  }
}
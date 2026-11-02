#include <Wire.h>

void setup() {
  Wire.begin(); // SDA = Broche 18, SCL = Broche 19 sur Teensy 4.0
  Serial.begin(9600);
  while (!Serial && millis() < 4000); // Attente connexion série USB
  Serial.println("\n=================================");
  Serial.println("   SCANNER I2C TEENSY 4.0       ");
  Serial.println("=================================");
}

void loop() {
  byte error, address;
  int nDevices = 0;

  for (address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();

    if (error == 0) {
      Serial.print("Appareil I2C detecte a l'adresse 0x");
      if (address < 16) Serial.print("0");
      Serial.print(address, HEX);

      if (address == 0x40) {
        Serial.print(" <-- PCA9685 (Servos)");
      }
      Serial.println();
      nDevices++;
    }
  }

  if (nDevices == 0) {
    Serial.println("Aucun composant I2C n'a repondu.");
  } else {
    Serial.println("Scan termine.");
  }

  Serial.println("---------------------------------");
  delay(3000);
}
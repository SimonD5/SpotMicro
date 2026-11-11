#include <Wire.h>
#include <math.h>

#define MPU6050_ADDR 0x68

void setup() {
  Serial.begin(9600);
  while (!Serial && millis() < 4000);

  Serial.println("\n=========================================");
  Serial.println("  VERIFICATION RECEPTION MPU6050 (0x68)  ");
  Serial.println("=========================================");

  Wire.begin();
  Wire.setClock(400000); // I2C Fast Mode (400 kHz)

  // Sortie du mode veille (registre PWR_MGMT_1 à 0x00)
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x6B);
  Wire.write(0x00);
  byte err = Wire.endTransmission();

  if (err != 0) {
    Serial.print("[ERREUR] Echec d'activation I2C (Code: ");
    Serial.print(err);
    Serial.println(")");
    while (1) delay(1000);
  }

  Serial.println("[OK] MPU6050 active sur 0x68.");
  Serial.println("Calcul en temps reel : Pitch, Roll, Temperature et Gyro Z\n");
}

void loop() {
  // Envoi de l'adresse du registre de depart (ACCEL_XOUT_H = 0x3B)
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);

  // Requete de 14 octets consécutifs (Accel: 6b, Temp: 2b, Gyro: 6b)
  Wire.requestFrom((uint8_t)MPU6050_ADDR, (uint8_t)14, (uint8_t)true);

  if (Wire.available() >= 14) {
    int16_t rawAX = (Wire.read() << 8) | Wire.read();
    int16_t rawAY = (Wire.read() << 8) | Wire.read();
    int16_t rawAZ = (Wire.read() << 8) | Wire.read();
    int16_t rawTemp = (Wire.read() << 8) | Wire.read();
    int16_t rawGX = (Wire.read() << 8) | Wire.read();
    int16_t rawGY = (Wire.read() << 8) | Wire.read();
    int16_t rawGZ = (Wire.read() << 8) | Wire.read();

    // Conversion en unites physiques (Plage par defaut : Accel +/-2g, Gyro +/-250°/s)
    float ax = rawAX / 16384.0;
    float ay = rawAY / 16384.0;
    float az = rawAZ / 16384.0;

    float gz = rawGZ / 131.0;
    float tempC = (rawTemp / 340.0) + 36.53;

    // Calcul de l'inclinaison (Pitch et Roll en degres)
    float roll  = atan2(ay, az) * 180.0 / M_PI;
    float pitch = atan2(-ax, sqrt(ay * ay + az * az)) * 180.0 / M_PI;

    // Affichage des donnees
    Serial.print("Pitch: ");
    if (pitch >= 0) Serial.print(" ");
    Serial.print(pitch, 1);
    Serial.print("° | Roll: ");
    if (roll >= 0) Serial.print(" ");
    Serial.print(roll, 1);
    Serial.print("° | Temp: ");
    Serial.print(tempC, 1);
    Serial.print("°C | Gyro Z: ");
    if (gz >= 0) Serial.print(" ");
    Serial.print(gz, 1);
    Serial.println(" °/s");
  } else {
    Serial.println("[ATTENTION] Trame I2C incomplete");
  }

  delay(100); // 10 mesures par seconde
}
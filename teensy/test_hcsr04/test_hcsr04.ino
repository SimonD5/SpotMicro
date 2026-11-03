#define TRIG_PIN 3
#define ECHO_PIN 4

void setup() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);
  
  Serial.begin(9600);
  while (!Serial && millis() < 4000); // Attente connexion série USB
  
  Serial.println("\n=================================");
  Serial.println("   TEST CAPTEUR ULTRASON HC-SR04 ");
  Serial.println("=================================");
}

void loop() {
  // S'assurer que TRIG est bas
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  // Envoi d'une impulsion HIGH de 10 microsecondes sur TRIG
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Mesure de la durée de l'impulsion HIGH sur ECHO (timeout de 30 ms ~ 5m max)
  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000);

  if (duration == 0) {
    Serial.println("Distance : Hors de portee / Pas de retour");
  } else {
    // Calcul de la distance en cm : (durée * vitesse du son 0.0343 cm/µs) / 2
    float distance_cm = duration * 0.0343 / 2.0;
    Serial.print("Distance : ");
    Serial.print(distance_cm, 1);
    Serial.println(" cm");
  }

  delay(500); // 2 mesures par seconde
}
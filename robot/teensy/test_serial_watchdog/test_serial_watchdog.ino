#include <Arduino.h>
#include <string.h>

constexpr int OE_PIN = 2;
constexpr int TRIG_PIN = 3;
constexpr int ECHO_PIN = 4;
constexpr uint32_t WATCHDOG_MS = 1000;
constexpr uint32_t DISTANCE_INTERVAL_MS = 500;
constexpr unsigned long ECHO_TIMEOUT_US = 30000;
char command[16];
size_t commandLength = 0;
bool discardLine = false;
bool armed = false;
bool timedOut = false;
const char *intent = "STOP";
uint32_t lastHeartbeat = 0;
uint32_t lastDistance = 0;

void checkWatchdog() {
  if (armed && uint32_t(millis() - lastHeartbeat) >= WATCHDOG_MS) {
    armed = false;
    timedOut = true;
    intent = "STOP";
  }
}

void handleCommand() {
  checkWatchdog();
  if (strcmp(command, "PING") == 0) {
    Serial.println("PONG SPOT_BENCH_V3");
  } else if (strcmp(command, "STATUS") == 0) {
    Serial.println(armed ? "ARMED" : (timedOut ? "DISARMED TIMEOUT" : "DISARMED"));
  } else if (strcmp(command, "ARM") == 0) {
    armed = true;
    timedOut = false;
    intent = "STOP";
    lastHeartbeat = millis();
    Serial.println("OK ARM");
  } else if (strcmp(command, "KEEPALIVE") == 0) {
    if (!armed) {
      Serial.println("ERR DISARMED");
      return;
    }
    lastHeartbeat = millis();
    Serial.println("OK KEEPALIVE");
  } else if (strcmp(command, "INTENT?") == 0) {
    Serial.print("INTENT ");
    Serial.println(intent);
  } else if (strcmp(command, "INTENT LEFT") == 0 ||
             strcmp(command, "INTENT RIGHT") == 0 ||
             strcmp(command, "INTENT STOP") == 0) {
    if (!armed) {
      Serial.println("ERR DISARMED");
      return;
    }
    // Le texte est mémorisé pour le banc, sans action sur le PCA9685.
    intent = strcmp(command, "INTENT LEFT") == 0 ? "LEFT" :
             (strcmp(command, "INTENT RIGHT") == 0 ? "RIGHT" : "STOP");
    lastHeartbeat = millis();
    Serial.print("OK INTENT ");
    Serial.println(intent);
  } else if (strcmp(command, "DISARM") == 0) {
    armed = false;
    timedOut = false;
    intent = "STOP";
    Serial.println("OK DISARM");
  } else {
    Serial.println("ERR COMMAND");
  }
}

void publishDistance() {
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  const unsigned long echoTime = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  checkWatchdog();

  if (echoTime == 0) {
    Serial.println("Distance : Hors de portee / Pas de retour");
  } else {
    Serial.print("Distance : ");
    Serial.print(echoTime * 0.0343f / 2.0f, 1);
    Serial.println(" cm");
  }
}

void setup() {
  // Armement simulé : OE reste haut pendant tout le test.
  digitalWrite(OE_PIN, HIGH);
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);
  Serial.begin(9600);
}

void loop() {
  checkWatchdog();
  const uint32_t now = millis();
  if (Serial && uint32_t(now - lastDistance) >= DISTANCE_INTERVAL_MS) {
    lastDistance = now;
    publishDistance();
  }
  if (Serial.available() == 0) return;

  const char byte = Serial.read();
  if (byte == '\n') {
    if (discardLine) {
      Serial.println("ERR LINE");
    } else {
      if (commandLength > 0 && command[commandLength - 1] == '\r') --commandLength;
      command[commandLength] = '\0';
      handleCommand();
    }
    commandLength = 0;
    discardLine = false;
  } else if (!discardLine) {
    if (commandLength == sizeof(command) - 1 || byte == '\0') {
      discardLine = true;
    } else {
      command[commandLength++] = byte;
    }
  }
}

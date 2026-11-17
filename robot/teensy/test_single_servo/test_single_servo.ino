#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

constexpr int OE_PIN = 2;
constexpr uint8_t SERVO_CHANNEL = 0;
constexpr uint16_t PWM_FULL_OFF = 4096;
constexpr uint32_t WATCHDOG_MS = 1000;
constexpr uint32_t POSE_CHANNEL_INTERVAL_MS = 600;
// Suspendu après l'incident électrique lors de l'essai des 12 servos.
constexpr bool SUPPORTED_POSE_ENABLED = false;

struct Joint {
  uint8_t channel;
  uint8_t start;
  uint8_t center;
};

// Références de consigne du tableau Amplitude.xlsx, à vérifier sur support.
constexpr Joint JOINTS[] = {
  {0, 50, 90}, {1, 80, 90}, {2, 85, 93},
  {4, 130, 90}, {5, 100, 90}, {6, 95, 87},
  {8, 50, 90}, {9, 80, 90}, {10, 85, 93},
  {12, 130, 90}, {13, 100, 90}, {14, 95, 87},
};

Adafruit_PWMServoDriver pwm(0x40);
const Joint *activeJoint = nullptr;
int activeAngle = 0;
bool driverReady = false;
bool armed = false;
bool timedOut = false;
bool poseMode = false;
uint16_t poseChannels = 0;
uint32_t lastPoseChannel = 0;
uint32_t lastHeartbeat = 0;
char command[16];
size_t commandLength = 0;
bool discardLine = false;

void disableOutputs(bool expired) {
  digitalWrite(OE_PIN, HIGH);
  armed = false;
  timedOut = expired;
  activeJoint = nullptr;
  poseMode = false;
  poseChannels = 0;
}

void checkWatchdog() {
  if (armed && uint32_t(millis() - lastHeartbeat) >= WATCHDOG_MS) {
    disableOutputs(true);
  }
}

bool writeServo(uint8_t channel, int angle) {
  // DS3218MG : 500 a 2500 us sur 180 degres, a 50 Hz.
  const uint32_t pulseUs = 500 + (uint32_t(angle) * 2000 + 90) / 180;
  const uint16_t ticks = (pulseUs * 4096 + 10000) / 20000;
  if (pwm.setPWM(channel, 0, ticks) == 0) return true;
  disableOutputs(false);
  driverReady = false;
  Serial.println("ERR PWM");
  return false;
}

const Joint *findJoint(const char *number) {
  if (*number < '0' || *number > '9') return nullptr;
  char *end;
  const long channel = strtol(number, &end, 10);
  if (*end != '\0') return nullptr;
  for (const Joint &joint : JOINTS) {
    if (joint.channel == channel) return &joint;
  }
  return nullptr;
}

bool prepareArm() {
  if (!driverReady) {
    Serial.println("ERR PWM");
    return false;
  }
  if (armed) {
    Serial.println("ERR ALREADY ARMED");
    return false;
  }
  // Une sélection neuve efface aussi la consigne de l'articulation précédente.
  for (uint8_t channel = 0; channel < 16; ++channel) {
    if (pwm.setPWM(channel, 0, PWM_FULL_OFF) != 0) {
      driverReady = false;
      Serial.println("ERR PWM");
      return false;
    }
  }
  return true;
}

void armServo(const Joint *joint) {
  if (!prepareArm()) return;
  if (!writeServo(joint ? joint->channel : SERVO_CHANNEL, joint ? joint->start : 90)) return;
  activeJoint = joint;
  activeAngle = joint ? joint->start : 90;
  lastHeartbeat = millis();
  timedOut = false;
  armed = true;
  digitalWrite(OE_PIN, LOW);
  Serial.println("OK ARM");
}

void armPose() {
  if (!SUPPORTED_POSE_ENABLED) {
    Serial.println("ERR POSE DISABLED");
    return;
  }
  if (!prepareArm()) return;
  poseMode = true;
  lastHeartbeat = millis();
  timedOut = false;
  armed = true;
  // OE reste haut jusqu'à la première consigne écrite sur le PCA9685.
  Serial.println("OK ARM POSE");
}

void addPoseJoint(const Joint *joint) {
  if (!armed || !poseMode) {
    Serial.println("ERR POSE NOT ARMED");
    return;
  }
  if (!joint) {
    Serial.println("ERR CHANNEL");
    return;
  }
  const uint16_t bit = uint16_t(1) << joint->channel;
  if (poseChannels & bit) {
    Serial.println("ERR ALREADY SET");
    return;
  }
  if (poseChannels && uint32_t(millis() - lastPoseChannel) < POSE_CHANNEL_INTERVAL_MS) {
    Serial.println("ERR WAIT");
    return;
  }
  if (!writeServo(joint->channel, joint->start)) return;
  checkWatchdog();
  if (!armed) {
    Serial.println("ERR DISARMED");
    return;
  }
  poseChannels |= bit;
  lastPoseChannel = millis();
  digitalWrite(OE_PIN, LOW);
  Serial.println("OK ADD");
}

void moveJoint(int angle) {
  const int low = min(activeJoint->start, activeJoint->center);
  const int high = max(activeJoint->start, activeJoint->center);
  if (angle < low || angle > high || abs(angle - activeAngle) > 2) {
    Serial.println("ERR RANGE");
    return;
  }
  if (writeServo(activeJoint->channel, angle)) {
    activeAngle = angle;
    checkWatchdog();
    Serial.println(armed ? "OK JOINT" : "ERR DISARMED");
  }
}

void handleCommand() {
  checkWatchdog();
  if (strcmp(command, "PING") == 0) {
    Serial.println("PONG SPOT_SERVO_BENCH_V4");
  } else if (strcmp(command, "STATUS") == 0) {
    Serial.println(armed ? "ARMED" : (timedOut ? "DISARMED TIMEOUT" : "DISARMED"));
  } else if (strcmp(command, "DISARM") == 0) {
    disableOutputs(false);
    Serial.println("OK DISARM");
  } else if (strcmp(command, "ARM") == 0) {
    armServo(nullptr);
  } else if (strcmp(command, "ARM POSE") == 0) {
    armPose();
  } else if (strncmp(command, "ARM ", 4) == 0) {
    const Joint *joint = findJoint(command + 4);
    if (joint) armServo(joint);
    else Serial.println("ERR CHANNEL");
  } else if (strncmp(command, "ADD ", 4) == 0) {
    addPoseJoint(findJoint(command + 4));
  } else if (strncmp(command, "INFO ", 5) == 0) {
    const Joint *joint = findJoint(command + 5);
    if (joint) {
      char reply[40];
      snprintf(reply, sizeof(reply), "JOINT %u START %u CENTER %u", unsigned(joint->channel),
               unsigned(joint->start), unsigned(joint->center));
      Serial.println(reply);
    } else {
      Serial.println("ERR CHANNEL");
    }
  } else if (strcmp(command, "KEEPALIVE") == 0) {
    if (!armed) {
      Serial.println("ERR DISARMED");
      return;
    }
    lastHeartbeat = millis();
    Serial.println("OK KEEPALIVE");
  } else if (strcmp(command, "STEP") == 0 || strcmp(command, "RETURN") == 0 ||
             strncmp(command, "JOG ", 4) == 0) {
    if (!armed || !activeJoint) {
      Serial.println("ERR JOINT NOT ARMED");
      return;
    }
    int angle = activeJoint->start;
    if (strcmp(command, "STEP") == 0) {
      angle += activeJoint->center > activeJoint->start ? 2 : -2;
    } else if (strncmp(command, "JOG ", 4) == 0) {
      const char *number = command + 4;
      char *end;
      const long requested = strtol(number, &end, 10);
      if (*number < '0' || *number > '9' || *end != '\0' || requested > 180) {
        Serial.println("ERR COMMAND");
        return;
      }
      angle = static_cast<int>(requested);
    }
    moveJoint(angle);
  } else if (strcmp(command, "SET 85") == 0 || strcmp(command, "SET 90") == 0 ||
             strcmp(command, "SET 95") == 0) {
    if (!armed) {
      Serial.println("ERR DISARMED");
      return;
    }
    if (activeJoint || poseMode) {
      Serial.println("ERR JOINT MODE");
      return;
    }
    const int angle = (command[4] - '0') * 10 + (command[5] - '0');
    if (writeServo(SERVO_CHANNEL, angle)) {
      checkWatchdog();
      Serial.println(armed ? "OK SET" : "ERR DISARMED");
    }
  } else {
    Serial.println("ERR COMMAND");
  }
}

void setup() {
  digitalWrite(OE_PIN, HIGH);
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH);
  Serial.begin(9600);
  if (!pwm.begin()) return;
  pwm.setPWMFreq(50);
  driverReady = true;
}

void loop() {
  checkWatchdog();
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

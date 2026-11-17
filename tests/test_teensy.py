"""Compile and execute the real sketches against a recording Arduino/PCA9685 stub.
Run from a C++ developer prompt (MSVC), or with g++ / clang++ on PATH.
These checks do not validate electrical behavior or Teensy cross-compilation.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

TEENSY_DIR = Path(__file__).resolve().parent.parent / "robot" / "teensy"

class TestTeensyFirmwares(unittest.TestCase):
    def _read_sketch(self, name):
        return (TEENSY_DIR / name / (name + ".ino")).read_text(encoding="utf-8")

    def test_cpp_stub_execution_if_compiler_available(self) -> None:
        cxx = shutil.which("g++") or shutil.which("clang++") or shutil.which("cl")
        if not cxx:
            self.skipTest("Aucun compilateur C++ (g++/clang++/cl) disponible dans l'environnement")

        arduino_mock = r"""
#pragma once
#include <stdint.h>
#include <stdio.h>
#include <vector>
#include <string>

#define HIGH 1
#define LOW 0
#define OUTPUT 1
#define INPUT 0
#define HEX 16

struct Event {
    std::string type;
    int a;
    int b;
    int c;
};

extern std::vector<Event> g_events;
extern unsigned long g_pulse_return;
extern bool g_begin_success;
extern int g_failed_channel;

inline void pinMode(int pin, int mode) {
    g_events.push_back({"pinMode", pin, mode, 0});
}
inline void digitalWrite(int pin, int val) {
    g_events.push_back({"digitalWrite", pin, val, 0});
}
inline void delay(unsigned long ms) {
    g_events.push_back({"delay", (int)ms, 0, 0});
}
inline void delayMicroseconds(unsigned int us) {
    g_events.push_back({"delayMicroseconds", (int)us, 0, 0});
}
inline unsigned long millis() { return 0; }
inline unsigned long pulseIn(uint8_t pin, uint8_t state, unsigned long timeout) {
    g_events.push_back({"pulseIn", (int)pin, (int)state, (int)timeout});
    return g_pulse_return;
}
inline int constrain(int x, int a, int b) {
    return (x < a) ? a : ((x > b) ? b : x);
}
inline long map(long x, long in_min, long in_max, long out_min, long out_max) {
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

struct FakeSerial {
    void begin(long) {}
    void print(...) {}
    void println(...) {}
    operator bool() const { return true; }
};
extern FakeSerial Serial;
"""
        wire_mock = r"""
#pragma once
#include "Arduino.h"
typedef uint8_t byte;
struct FakeWire {
    void begin() { g_events.push_back({"Wire.begin", 0, 0, 0}); }
    void beginTransmission(uint8_t addr) { g_events.push_back({"Wire.beginTransmission", addr, 0, 0}); }
    uint8_t endTransmission() { return 0; }
};
extern FakeWire Wire;
"""
        pca_mock = r"""
#pragma once
#include "Arduino.h"
class Adafruit_PWMServoDriver {
public:
    Adafruit_PWMServoDriver(uint8_t addr = 0x40) : _addr(addr) {}
    bool begin() { g_events.push_back({"pwm.begin", _addr, 0, 0}); return g_begin_success; }
    void setPWMFreq(float f) { g_events.push_back({"pwm.setPWMFreq", (int)f, 0, 0}); }
    uint8_t setPWM(uint8_t ch, uint16_t on, uint16_t off) {
        g_events.push_back({"pwm.setPWM", ch, on, off});
        return ch == g_failed_channel ? 1 : 0;
    }
private:
    uint8_t _addr;
};
"""
        harness = r"""
#include "Arduino.h"
#include "Wire.h"
#include "Adafruit_PWMServoDriver.h"
#include <assert.h>

std::vector<Event> g_events;
unsigned long g_pulse_return = 1000;
bool g_begin_success = true;
int g_failed_channel = -1;
FakeSerial Serial;
FakeWire Wire;

namespace ns_stop {
#include "stop_servos.ino"
}
namespace ns_set90 {
#include "set_all_90.ino"
}
namespace ns_walk {
#include "walk_demo.ino"
}
namespace ns_servo {
#include "test_servo.ino"
}
namespace ns_hcsr04 {
#include "test_hcsr04.ino"
}

void check_startup(void (*setup_fn)(), int expected_servos) {
    g_events.clear();
    setup_fn();
    assert(!g_events.empty());
    assert(g_events[0].type == "digitalWrite" && g_events[0].a == 2 && g_events[0].b == HIGH);
    bool cleared[16] = {};
    bool enabled = false;
    int pulses = 0;
    bool pause_since_pulse = true;
    for (const auto& ev : g_events) {
        if (ev.type == "pwm.setPWM" && ev.c == 4096) cleared[ev.a] = true;
        if (ev.type == "digitalWrite" && ev.a == 2 && ev.b == LOW) {
            for (bool off : cleared) assert(off);
            enabled = true;
        }
        if (ev.type == "delay" && ev.a >= 500) pause_since_pulse = true;
        if (ev.type == "pwm.setPWM" && ev.c > 0 && ev.c < 4096) {
            if (expected_servos > 1) { assert(enabled); assert(pause_since_pulse); }
            pause_since_pulse = false;
            ++pulses;
        }
    }
    assert(enabled && pulses == expected_servos);
}
void check_disabled(void (*setup_fn)(), void (*loop_fn)()) {
    g_events.clear();
    setup_fn();
    loop_fn();
    for (const auto& ev : g_events) {
        if (ev.type == "digitalWrite" && ev.a == 2) assert(ev.b == HIGH);
        if (ev.type == "pwm.setPWM") assert(ev.c == 4096);
    }
}
int main() {
    check_startup(ns_servo::setup, 1);
    check_startup(ns_set90::setup, 12);
    check_startup(ns_walk::setup, 12);
    check_disabled(ns_stop::setup, ns_stop::loop);
    g_begin_success = false;
    ns_servo::pwmReady = ns_set90::pwmReady = ns_walk::pwmReady = false;
    check_disabled(ns_servo::setup, ns_servo::loop);
    check_disabled(ns_set90::setup, ns_set90::loop);
    check_disabled(ns_walk::setup, ns_walk::loop);
    check_disabled(ns_stop::setup, ns_stop::loop);
    g_begin_success = true;
    g_failed_channel = 5;
    check_disabled(ns_servo::setup, ns_servo::loop);
    check_disabled(ns_set90::setup, ns_set90::loop);
    check_disabled(ns_walk::setup, ns_walk::loop);
    g_failed_channel = -1;
    g_events.clear();
    ns_walk::setServoAngle(0, 0);
    ns_walk::setServoAngle(0, 180);
    ns_walk::setServoAngle(20, 90);
    assert(g_events.size() == 2);
    assert(g_events[0].c >= 295 && g_events[0].c <= 300);
    assert(g_events[1].c >= 315 && g_events[1].c <= 320);
    g_events.clear();
    ns_servo::currentAngle = 90;
    ns_servo::moveSlow(0, 200, -10);
    assert(ns_servo::currentAngle == 180);
    for (const auto& ev : g_events) if (ev.type == "delay") assert(ev.a == 0);
    return 0;
}
"""
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "Arduino.h").write_text(arduino_mock, encoding="utf-8")
            (tmp / "Wire.h").write_text(wire_mock, encoding="utf-8")
            (tmp / "Adafruit_PWMServoDriver.h").write_text(pca_mock, encoding="utf-8")
            for name in ("stop_servos", "set_all_90", "walk_demo", "test_servo", "test_hcsr04"):
                src = self._read_sketch(name)
                (tmp / f"{name}.ino").write_text(src, encoding="utf-8")
            main_cpp = tmp / "main.cpp"
            main_cpp.write_text(harness, encoding="utf-8")
            exe = tmp / ("runner.exe" if os.name == "nt" else "runner")
            if Path(cxx).stem.lower() == "cl":
                command = [cxx, "/nologo", "/EHsc", "/std:c++17", "/utf-8", "/I" + str(tmp), str(main_cpp), "/Fe:" + str(exe), "/Fo:" + str(tmp / "main.obj")]
            else:
                command = [cxx, "-std=c++17", "-I", str(tmp), str(main_cpp), "-o", str(exe)]
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, f"Erreur de compilation du stub C++:\n{proc.stdout}\n{proc.stderr}")
            run_proc = subprocess.run([str(exe)], capture_output=True, text=True, check=False)
            self.assertEqual(run_proc.returncode, 0, f"Echec d'execution du stub C++:\n{run_proc.stderr}")


if __name__ == "__main__":
    unittest.main()

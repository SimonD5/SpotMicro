"""Vérifie la liaison USB et le watchdog avec un firmware de banc."""

import argparse
from contextlib import suppress
import math
import time

ARTICULATION_CHANNELS = (0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14)
SERVO_BENCH_REPLY = "PONG SPOT_SERVO_BENCH_V4"
# Suspendu jusqu'à la validation de la distribution électrique sur le robot.
SUPPORTED_POSE_ENABLED = False


def expect(link, command, reply, distances=None, *, on_distance=None):
    link.write((command + "\n").encode("ascii"))
    deadline = time.monotonic() + 1.0
    received = ""
    while time.monotonic() < deadline:
        raw = link.read_until(size=64)
        received = raw.decode("ascii", errors="replace").rstrip("\r\n")
        if not raw.endswith(b"\n"):
            break
        if received.startswith("Distance : "):
            if on_distance is not None:
                on_distance(received)
            if distances is not None and received.endswith(" cm"):
                try:
                    value = float(received.removeprefix("Distance : ").removesuffix(" cm"))
                except ValueError:
                    continue
                if math.isfinite(value) and value > 0:
                    distances.append(value)
            continue
        if reply is None or received == reply:
            return received
        break
    raise RuntimeError(f"{command} : attendu {reply!r}, reçu {received!r}")


def check_link(link):
    expect(link, "PING", "PONG SPOT_BENCH_V3")
    try:
        expect(link, "DISARM", "OK DISARM")
        expect(link, "STATUS", "DISARMED")
        expect(link, "ARM", "OK ARM")
        distances = []
        for _ in range(6):
            time.sleep(0.2)
            expect(link, "KEEPALIVE", "OK KEEPALIVE", distances)
        expect(link, "STATUS", "ARMED", distances)
        print("OK : la Teensy reste armée pendant la réception des messages.")
        for direction in ("LEFT", "STOP", "RIGHT"):
            expect(link, f"INTENT {direction}", f"OK INTENT {direction}")
            expect(link, "INTENT?", f"INTENT {direction}")
        print("OK : directions reçues et mémorisées par la Teensy.")

        # Garder le câble branché et simuler une perte de communication.
        time.sleep(1.3)
        expect(link, "STATUS", "DISARMED TIMEOUT")
        expect(link, "INTENT?", "INTENT STOP")
        expect(link, "INTENT LEFT", "ERR DISARMED")
        expect(link, "KEEPALIVE", "ERR DISARMED")
        print("OK : désarmement automatique et refus du maintien sans réarmement.")
        if not distances:
            raise RuntimeError("Aucun écho ultrason valide pendant le test. Place un carton devant le capteur.")
        print(f"OK : {len(distances)} mesure(s) ultrason reçue(s), dernière à {distances[-1]:.1f} cm.")
    finally:
        with suppress(OSError, RuntimeError):
            expect(link, "DISARM", "OK DISARM")


def check_single_servo(link):
    expect(link, "PING", SERVO_BENCH_REPLY)
    try:
        expect(link, "DISARM", "OK DISARM")
        expect(link, "STATUS", "DISARMED")
        expect(link, "SET 85", "ERR DISARMED")
        print("Le servo du canal 0 va se centrer à 90°.", flush=True)
        expect(link, "ARM", "OK ARM")
        for angle in (90, 85, 90, 95, 90):
            expect(link, f"SET {angle}", "OK SET")
            print(f"Consigne acceptée : {angle}°.", flush=True)
            for _ in range(3):
                time.sleep(0.2)
                expect(link, "KEEPALIVE", "OK KEEPALIVE")
        print("Pause des messages pour tester la coupure PWM.", flush=True)
        time.sleep(1.3)
        expect(link, "STATUS", "DISARMED TIMEOUT")
        expect(link, "SET 85", "ERR DISARMED")
        print("OK : la Teensy signale le désarmement et refuse une nouvelle consigne.")
    finally:
        with suppress(OSError, RuntimeError):
            expect(link, "DISARM", "OK DISARM")


def jog_joint(link, angle, target):
    while angle != target:
        angle += max(-2, min(2, target - angle))
        expect(link, f"JOG {angle}", "OK JOINT")
        time.sleep(0.2)
        expect(link, "KEEPALIVE", "OK KEEPALIVE")


def joint_reference(link, channel):
    reference = expect(link, f"INFO {channel}", None).split()
    if (len(reference) != 6 or reference[:3] != ["JOINT", str(channel), "START"]
            or reference[4] != "CENTER" or not reference[3].isdigit() or not reference[5].isdigit()):
        raise RuntimeError(f"Référence inattendue pour le canal {channel} : {' '.join(reference)}")
    return int(reference[3]), int(reference[5])


def check_joint(link, channel, verify_center=False):
    expect(link, "PING", SERVO_BENCH_REPLY)
    expect(link, "DISARM", "OK DISARM")
    expect(link, "STATUS", "DISARMED")
    start, center = joint_reference(link, channel)
    step = start + (2 if center > start else -2)
    test_target = center if verify_center else step
    print(f"Canal {channel} : départ {start}°, centre du tableau {center}°. Essai {start}° -> {test_target}° -> {start}°.")
    answer = input("Robot calé, pattes dégagées et articulation déjà proche du départ ? Tape OUI pour activer : ")
    if answer.strip().upper() != "OUI":
        print("Essai annulé. Sorties désactivées.")
        return

    try:
        expect(link, f"ARM {channel}", "OK ARM")
        if verify_center:
            jog_joint(link, start, center)
            print(f"Consigne de centre {center}° acceptée. Observe la position.", flush=True)
            for _ in range(10):
                time.sleep(0.2)
                expect(link, "KEEPALIVE", "OK KEEPALIVE")
            jog_joint(link, center, start)
        else:
            for command, reply in (("STATUS", "ARMED"), ("STEP", "OK JOINT"), ("RETURN", "OK JOINT")):
                expect(link, command, reply)
                for _ in range(3):
                    time.sleep(0.2)
                    expect(link, "KEEPALIVE", "OK KEEPALIVE")
        time.sleep(1.3)
        expect(link, "STATUS", "DISARMED TIMEOUT")
        print(f"OK : canal {channel}, consignes acceptées et watchdog déclenché.")
    finally:
        with suppress(OSError, RuntimeError):
            expect(link, "DISARM", "OK DISARM")


def check_supported_pose(link):
    if not SUPPORTED_POSE_ENABLED:
        raise RuntimeError("Essai de pose suspendu après l'incident du PCA9685.")
    expect(link, "PING", SERVO_BENCH_REPLY)
    expect(link, "DISARM", "OK DISARM")
    expect(link, "STATUS", "DISARMED")
    starts = [(channel, joint_reference(link, channel)[0]) for channel in ARTICULATION_CHANNELS]
    print("Positions de départ : " + ", ".join(f"CH{channel}={angle}°" for channel, angle in starts))
    answer = input("Spot calé, pattes dégagées et proches du départ ? Tape OUI pour tester la pose sur support : ")
    if answer.strip().upper() != "OUI":
        print("Essai annulé. Sorties désactivées.")
        return

    try:
        expect(link, "ARM POSE", "OK ARM POSE")
        for channel, angle in starts:
            print(f"Activation du canal {channel} à {angle}°.", flush=True)
            expect(link, f"ADD {channel}", "OK ADD")
            for _ in range(4):
                time.sleep(0.2)
                expect(link, "KEEPALIVE", "OK KEEPALIVE")
        print("Pose complète. Observe les quatre pieds pendant deux secondes.", flush=True)
        for _ in range(10):
            time.sleep(0.2)
            expect(link, "KEEPALIVE", "OK KEEPALIVE")
    finally:
        with suppress(OSError, RuntimeError):
            expect(link, "DISARM", "OK DISARM")
    expect(link, "STATUS", "DISARMED")
    print("OK : 12 consignes acceptées, sorties désactivées. Vérifie la pose observée.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/ttyACM0", help="port USB de la Teensy")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--servo-libre-canal-0", action="store_true",
                      help="essai réel avec un seul servo hors du robot, sans tringlerie, sur le canal 0")
    mode.add_argument("--canal-articulation", type=int, choices=ARTICULATION_CHANNELS,
                      help="essai sur support de l'articulation connectée à ce canal")
    mode.add_argument("--pose-sur-support", action="store_true",
                      help="activer les 12 angles de départ progressivement, pattes hors du sol")
    parser.add_argument("--centre", action="store_true", help="aller au centre du canal par pas de 2 degrés")
    args = parser.parse_args()
    if args.centre and args.canal_articulation is None:
        parser.error("--centre nécessite --canal-articulation")
    if args.pose_sur_support and not SUPPORTED_POSE_ENABLED:
        parser.error("Essai de pose suspendu après l'incident du PCA9685.")

    try:
        import serial
    except ModuleNotFoundError:
        parser.exit(1, "Installe pyserial dans le venv : python -m pip install pyserial\n")

    try:
        with serial.Serial(args.port, 9600, timeout=0.5, write_timeout=0.5) as link:
            link.reset_input_buffer()
            if args.servo_libre_canal_0:
                check_single_servo(link)
            elif args.canal_articulation is not None:
                check_joint(link, args.canal_articulation, verify_center=args.centre)
            elif args.pose_sur_support:
                check_supported_pose(link)
            else:
                check_link(link)
    except (serial.SerialException, RuntimeError) as exc:
        parser.exit(1, f"Échec du test série : {exc}\n")


if __name__ == "__main__":
    main()

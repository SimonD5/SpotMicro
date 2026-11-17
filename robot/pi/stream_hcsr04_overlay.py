import cv2
import math
import os
import serial
import threading
import time
from flask import Flask, Response
from picamera2 import Picamera2
from ultralytics import YOLO

app = Flask(__name__)

# Classe COCO 0 : personne. La vidéo garde sa résolution de 640 × 480.
model = YOLO('yolov8n.pt')
PERSON_CLASS = 0
DETECTION_INTERVAL = 0.5
FRAME_INTERVAL = 0.1
DISTANCE_MAX_AGE = 1.5
OBSTACLE_CM = 35.0
BENCH_INTERVAL = 0.2
FRAME_MAX_AGE = 0.75
BENCH_MODE = os.environ.get("SPOT_BANC_SERIE") == "1"

# Publier la distance et son horodatage ensemble pour le thread vidéo.
latest_measurement = (None, 0.0)
latest_intent = ("STOP", None)
bench_state = "connexion"
running = True


def parse_distance(line):
    if not line.endswith(" cm"):
        return None
    try:
        distance = float(line.removeprefix("Distance : ").removesuffix(" cm"))
    except ValueError:
        return None
    return distance if math.isfinite(distance) and distance > 0 else None


def person_direction(box, width):
    center_x = (box[0] + box[2]) / 2
    if center_x < width / 3:
        return "gauche"
    if center_x >= 2 * width / 3:
        return "droite"
    return "centre"


def tracking_hint(person_boxes, width, distance):
    if distance is None:
        return "STOP", "Arret : distance indisponible"
    if distance <= OBSTACLE_CM:
        return "STOP", "Arret : obstacle proche"
    if len(person_boxes) == 0:
        return "STOP", "Arret : aucune personne"
    if len(person_boxes) > 1:
        return "STOP", "Arret : plusieurs personnes"
    direction = person_direction(person_boxes[0], width)
    if direction == "centre":
        return "STOP", "Rester en place"
    return ("LEFT" if direction == "gauche" else "RIGHT"), f"Tourner a {direction}"


def update_distance(line):
    global latest_measurement
    if line.startswith("Distance : "):
        latest_measurement = (parse_distance(line), time.monotonic())


def poll_distance(link):
    if link.in_waiting:
        raw = link.readline()
        if raw.endswith(b"\n"):
            update_distance(raw.decode("ascii", errors="replace").strip())


def relay_bench(link, expect):
    global bench_state

    def exchange(command, reply):
        expect(link, command, reply, on_distance=update_distance)

    exchange("PING", "PONG SPOT_BENCH_V3")
    exchange("DISARM", "OK DISARM")
    bench_state = "en attente de la video"
    while running:
        _, frame_at = latest_intent
        if frame_at is not None and time.monotonic() - frame_at < FRAME_MAX_AGE:
            break
        poll_distance(link)
        time.sleep(0.02)

    if not running:
        return
    exchange("ARM", "OK ARM")
    while running:
        intent, frame_at = latest_intent
        if time.monotonic() - frame_at >= FRAME_MAX_AGE:
            break
        exchange(f"INTENT {intent}", f"OK INTENT {intent}")
        bench_state = f"recu {intent}"
        time.sleep(BENCH_INTERVAL)

    if running:
        bench_state = "video interrompue"
        time.sleep(1.1)
        exchange("STATUS", "DISARMED TIMEOUT")
        exchange("INTENT?", "INTENT STOP")
        bench_state = "STOP confirme par le watchdog"
        print(f"[BANC] {bench_state}. Relancer le flux pour rearmer le test.")


# Thread de lecture Série du HC-SR04 depuis la Teensy
def read_teensy_serial():
    global latest_measurement, bench_state
    try:
        with serial.Serial('/dev/ttyACM0', 9600, timeout=0.5, write_timeout=0.5) as link:
            print("[OK] Connexion série ouverte sur /dev/ttyACM0")
            if BENCH_MODE:
                from test_serial_watchdog import expect

                relay_bench(link, expect)
            while running:
                poll_distance(link)
                time.sleep(0.02)
    except Exception as e:
        latest_measurement = (None, 0.0)
        bench_state = "erreur serie"
        print(f"[ERREUR] Impossible de lire la liaison série : {e}")

# Démarrage du thread de lecture ultrason
serial_thread = threading.Thread(target=read_teensy_serial, daemon=True)
serial_thread.start()

# Initialisation de la caméra WPI408 sur CAM0 (Tête 1)
picam2 = Picamera2(0)
config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
picam2.configure(config)
picam2.start()

def generate_frames():
    global latest_intent
    next_frame = 0.0
    next_detection = 0.0
    person_boxes = []
    while True:
        wait = next_frame - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        next_frame = time.monotonic() + FRAME_INTERVAL
        frame = picam2.capture_array()
        frame_at = time.monotonic()
        
        # 1. Inversion Haut / Bas de l'image (caméra montée à l'envers)
        frame = cv2.flip(frame, 0)
        
        # 2. Réutiliser les derniers cadres entre deux analyses YOLO.
        now = time.monotonic()
        if now >= next_detection:
            next_detection = now + DETECTION_INTERVAL
            results = model(frame, imgsz=320, conf=0.25, classes=[PERSON_CLASS], verbose=False)
            person_boxes = [
                tuple(map(int, box.xyxy[0])) for result in results for box in result.boxes
            ]

        h, w, _ = frame.shape
        for box in person_boxes:
            x1_b, y1_b, x2_b, y2_b = box
            direction = person_direction(box, w)
            box_color = (255, 105, 180)
            cv2.rectangle(frame, (x1_b, y1_b), (x2_b, y2_b), box_color, 2)
            cv2.putText(frame, f"Humain : {direction}", (x1_b, y1_b - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2, cv2.LINE_AA)

        # 3. Calcul du rectangle de visée HC-SR04 (280 x 210 px)
        center_x, center_y = w // 2, h // 2
        
        box_w, box_h = 280, 210
        x1 = center_x - box_w // 2
        y1 = center_y - box_h // 2
        x2 = center_x + box_w // 2
        y2 = center_y + box_h // 2

        # Détermination de la couleur du rectangle de visée selon la distance
        latest_distance, measured_at = latest_measurement
        if time.monotonic() - measured_at >= DISTANCE_MAX_AGE:
            latest_distance = None
        if latest_distance is None:
            color = (128, 128, 128)
            status_text = "HC-SR04: -- cm"
        elif latest_distance < 15.0:
            color = (0, 0, 255)
            status_text = f"HC-SR04: {latest_distance:.1f} cm [DANGER]"
        elif latest_distance <= OBSTACLE_CM:
            color = (0, 255, 255)
            status_text = f"HC-SR04: {latest_distance:.1f} cm [ATTENTION]"
        else:
            color = (0, 255, 0)
            status_text = f"HC-SR04: {latest_distance:.1f} cm [OK]"

        # Dessiner le viseur ultrason
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.line(frame, (center_x - 15, center_y), (center_x + 15, center_y), color, 1)
        cv2.line(frame, (center_x, center_y - 15), (center_x, center_y + 15), color, 1)

        # Fond et texte de distance ultrason
        cv2.rectangle(frame, (x1, y1 - 30), (x1 + 240, y1), (0, 0, 0), -1)
        cv2.putText(frame, status_text, (x1 + 5, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

        intent, hint = tracking_hint(person_boxes, w, latest_distance)
        if BENCH_MODE:
            latest_intent = (intent, frame_at)
            cv2.rectangle(frame, (0, h - 50), (w, h), (0, 0, 0), -1)
            cv2.putText(frame, f"Teensy : {bench_state}", (8, h - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        else:
            cv2.rectangle(frame, (0, h - 28), (w, h), (0, 0, 0), -1)
        cv2.putText(frame, f"Suivi simule : {hint}", (8, h - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

        # Conversion BGR pour diffusion Flask
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        ret, buffer = cv2.imencode('.jpg', frame_bgr)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("[INFO] Serveur Web de visée Tête 1 (HC-SR04 + YOLO personnes) sur http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, threaded=True)

import cv2
import serial
import threading
import time
from flask import Flask, Response
from picamera2 import Picamera2
from ultralytics import YOLO

app = Flask(__name__)

# Chargement du modèle YOLOv8 (yolov8s.pt présent à la racine du dépôt)
model = YOLO('yolov8s.pt')

# Classes ciblées : 0 = person (humain), 67 = cell phone (téléphone)
TARGET_CLASSES = [0, 67]

# Variable globale pour stocker la dernière distance mesurée par le HC-SR04
latest_distance = -1.0
running = True

# Thread de lecture Série du HC-SR04 depuis la Teensy
def read_teensy_serial():
    global latest_distance, running
    try:
        ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
        print("[OK] Connexion série ouverte sur /dev/ttyACM0")
        while running:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if "Distance" in line and ":" in line:
                    try:
                        val_str = line.split(":")[1].replace("cm", "").strip()
                        latest_distance = float(val_str)
                    except ValueError:
                        pass
            time.sleep(0.02)
        ser.close()
    except Exception as e:
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
    global latest_distance
    while True:
        frame = picam2.capture_array()
        
        # 1. Inversion Haut / Bas de l'image (caméra montée à l'envers)
        frame = cv2.flip(frame, 0)
        
        # 2. Détection YOLO (filtré sur Humain [0] et Téléphone [67])
        results = model(frame, conf=0.25, classes=TARGET_CLASSES, verbose=False)
        for r in results:
            for box in r.boxes:
                x1_b, y1_b, x2_b, y2_b = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                label = "Humain" if cls_id == 0 else "Telephone"
                box_color = (255, 105, 180)  # Rose pour la détection objet

                # Dessiner le rectangle et le libellé de l'objet
                cv2.rectangle(frame, (x1_b, y1_b), (x2_b, y2_b), box_color, 2)
                cv2.putText(frame, f"{label} {conf:.2f}", (x1_b, y1_b - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2, cv2.LINE_AA)

        # 3. Calcul du rectangle de visée HC-SR04 (280 x 210 px)
        h, w, _ = frame.shape
        center_x, center_y = w // 2, h // 2
        
        box_w, box_h = 280, 210
        x1 = center_x - box_w // 2
        y1 = center_y - box_h // 2
        x2 = center_x + box_w // 2
        y2 = center_y + box_h // 2

        # Détermination de la couleur du rectangle de visée selon la distance
        if latest_distance < 0:
            color = (128, 128, 128)
            status_text = "HC-SR04: -- cm"
        elif latest_distance < 15.0:
            color = (0, 0, 255)
            status_text = f"HC-SR04: {latest_distance:.1f} cm [DANGER]"
        elif latest_distance < 35.0:
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
    print("[INFO] Serveur Web de visée Tête 1 (HC-SR04 + YOLO Humain/Téléphone) sur http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, threaded=True)
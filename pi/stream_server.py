import io
import time
import cv2
from flask import Flask, Response
from picamera2 import Picamera2
from ultralytics import YOLO

app = Flask(__name__)

print("1. Chargement du modèle YOLOv8s (Small - plus précis)...")
# Télécharge automatiquement 'yolov8s.pt' (~22 Mo) au premier lancement
model = YOLO("yolov8s.pt")

print("2. Initialisation de la caméra 0 (640x480)...")
picam2 = Picamera2(camera_num=0)
config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
picam2.configure(config)
picam2.start()
time.sleep(1)

# (Optionnel) Classes COCO particulièrement utiles pour le robot Spot :
# 0: person, 15: cat, 16: dog, 67: cell phone
# Tu peux retirer 'classes=...' si tu veux tout détecter sans filtre.
TARGET_CLASSES = [0, 15, 16, 67]

def generate_frames():
    while True:
        frame = picam2.capture_array()
        bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Inférence avec YOLOv8s
        results = model(bgr_frame, verbose=False, conf=0.15, classes=TARGET_CLASSES)
        annotated_frame = results[0].plot()

        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame_bytes = buffer.tobytes()

        # Petite pause pour réguler à ~10 FPS et libérer du CPU
        time.sleep(0.03)

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
@app.route('/')
def index():
    return """
    <html>
        <head>
            <title>Spot Micro - Vision IA YOLOv8s</title>
            <style>
                body { background-color: #121212; color: white; text-align: center; font-family: sans-serif; }
                img { border: 2px solid #00ff88; border-radius: 8px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <h1>Spot Micro — Vision IA (YOLOv8 Small)</h1>
            <img src="/video_feed" width="640" height="480">
        </body>
    </html>
    """

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
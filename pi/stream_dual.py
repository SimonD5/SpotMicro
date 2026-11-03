import time
import cv2
from flask import Flask, Response
from picamera2 import Picamera2

app = Flask(__name__)

print("1. Initialisation des caméras (CAM0 = Gauche, CAM1 = Droite)...")
cam_left = Picamera2(camera_num=0)
cam_right = Picamera2(camera_num=1)

config = {"main": {"size": (640, 480), "format": "RGB888"}}
cam_left.configure(cam_left.create_video_configuration(**config))
cam_right.configure(cam_right.create_video_configuration(**config))

cam_left.start()
cam_right.start()
time.sleep(1)

def generate_frames():
    while True:
        frame_l = cam_left.capture_array()
        frame_r = cam_right.capture_array()

        bgr_l = cv2.cvtColor(frame_l, cv2.COLOR_RGB2BGR)
        bgr_r = cv2.cvtColor(frame_r, cv2.COLOR_RGB2BGR)

        # (Décommenter si la caméra DROITE est physiquement à l'envers)
        # bgr_r = cv2.rotate(bgr_r, cv2.ROTATE_180)

        # (Décommenter si la caméra GAUCHE est physiquement à l'envers)
        # bgr_l = cv2.rotate(bgr_l, cv2.ROTATE_180)

        # Ajout des étiquettes et lignes guides horizontales
        cv2.putText(bgr_l, "CAM 0 (GAUCHE)", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(bgr_r, "CAM 1 (DROITE)", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Juxtaposition horizontale (1280x480)
        combined = cv2.hconcat([bgr_l, bgr_r])

        # Dessin de 3 lignes repères horizontales pour vérifier l'alignement
        h, w, _ = combined.shape
        for y_line in [h // 4, h // 2, (3 * h) // 4]:
            cv2.line(combined, (0, y_line), (w, y_line), (0, 0, 255), 1)

        ret, buffer = cv2.imencode('.jpg', combined)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return """
    <html>
        <head>
            <title>Spot Micro - Alignement Stéréo Dual</title>
            <style>
                body { background-color: #121212; color: white; text-align: center; font-family: sans-serif; }
                img { border: 2px solid #00ff88; border-radius: 8px; margin-top: 10px; }
            </style>
        </head>
        <body>
            <h1>Alignement Physique des Caméras Stéréo</h1>
            <p>Vérifie que le haut/bas est identique sur les 2 images et que les objets sont à la même hauteur (lignes rouges).</p>
            <img src="/video_feed" width="1280" height="480">
        </body>
    </html>
    """

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
import time
import cv2
from picamera2 import Picamera2

print("1. Initialisation de Picamera2 (Caméra 0)...")
picam2 = Picamera2(camera_num=0)

# Configuration en 640x480 RGB888 (format idéal pour OpenCV et le suivi stéréo)
config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
picam2.configure(config)

print("2. Démarrage du flux...")
picam2.start()
time.sleep(1)  # Temps d'ajustement de l'exposition automatique

print("3. Capture de l'image dans une matrice NumPy...")
frame = picam2.capture_array()
print(f"   Dimensions de l'image capturée : {frame.shape}")

# Conversion RGB -> BGR pour enregistrement OpenCV
bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
cv2.imwrite("test_python.jpg", bgr_frame)

picam2.stop()
print("4. Terminé ! Image enregistrée sous 'test_python.jpg'.")
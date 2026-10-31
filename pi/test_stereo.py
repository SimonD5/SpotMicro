import time
import cv2
from picamera2 import Picamera2

print("1. Initialisation des deux caméras (CAM0 = Gauche, CAM1 = Droite)...")

# Caméra 0 (Gauche)
cam_left = Picamera2(camera_num=0)
config_left = cam_left.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
cam_left.configure(config_left)

# Caméra 1 (Droite)
cam_right = Picamera2(camera_num=1)
config_right = cam_right.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
cam_right.configure(config_right)

print("2. Démarrage des flux...")
cam_left.start()
cam_right.start()
time.sleep(1)  # Exposition automatique

print("3. Capture simultanée de la paire stéréo...")
frame_left = cam_left.capture_array()
frame_right = cam_right.capture_array()

cam_left.stop()
cam_right.stop()

# Conversion RGB -> BGR pour OpenCV
bgr_left = cv2.cvtColor(frame_left, cv2.COLOR_RGB2BGR)
bgr_right = cv2.cvtColor(frame_right, cv2.COLOR_RGB2BGR)

# Juxtaposition des deux images (Side-by-Side)
stereo_combined = cv2.hconcat([bgr_left, bgr_right])

# Enregistrement
cv2.imwrite("stereo_left.jpg", bgr_left)
cv2.imwrite("stereo_right.jpg", bgr_right)
cv2.imwrite("stereo_combined.jpg", stereo_combined)

print("4. Succès ! Images enregistrées : 'stereo_left.jpg', 'stereo_right.jpg' et 'stereo_combined.jpg'.")
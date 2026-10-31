import os
import time
import cv2
import numpy as np
from picamera2 import Picamera2

# Configuration du damier (nombre de coins INTERNES : largeur x hauteur)
CHECKERBOARD = (7, 7)
SAVE_DIR = "calib_images"

os.makedirs(SAVE_DIR, exist_ok=True)

print("1. Initialisation des caméras stéréo...")
cam_left = Picamera2(camera_num=0)
cam_right = Picamera2(camera_num=1)

config = {"main": {"size": (640, 480), "format": "RGB888"}}
cam_left.configure(cam_left.create_video_configuration(**config))
cam_right.configure(cam_right.create_video_configuration(**config))

cam_left.start()
cam_right.start()
time.sleep(1)

print("\n--- MODE CAPTURE CALIBRATION STEREO ---")
print("Instructions :")
print(" - Présente le damier devant les 2 caméras sous différents angles/distances.")
print(" - Appuie sur [ENTRÉE] dans le terminal pour capturer une paire.")
print(" - Tape 'q' puis [ENTRÉE] pour terminer la capture.\n")

pair_count = 0

try:
    while True:
        cmd = input(f"Image {pair_count + 1} - Appuie sur [ENTRÉE] pour capturer (ou 'q' pour quitter) : ")
        if cmd.lower() == 'q':
            break

        # Capture
        frame_l = cam_left.capture_array()
        frame_r = cam_right.capture_array()

        gray_l = cv2.cvtColor(frame_l, cv2.COLOR_RGB2GRAY)
        gray_r = cv2.cvtColor(frame_r, cv2.COLOR_RGB2GRAY)

        # Recherche des coins du damier
        ret_l, corners_l = cv2.findChessboardCorners(gray_l, CHECKERBOARD, None)
        ret_r, corners_r = cv2.findChessboardCorners(gray_r, CHECKERBOARD, None)

        if ret_l and ret_r:
            pair_count += 1
            file_l = os.path.join(SAVE_DIR, f"left_{pair_count:02d}.jpg")
            file_r = os.path.join(SAVE_DIR, f"right_{pair_count:02d}.jpg")

            cv2.imwrite(file_l, cv2.cvtColor(frame_l, cv2.COLOR_RGB2BGR))
            cv2.imwrite(file_r, cv2.cvtColor(frame_r, cv2.COLOR_RGB2BGR))
            print(f"  --> SUCCÈS : Damier vu sur les 2 caméras ! Paire {pair_count} enregistrée.")
        else:
            print("  --> ÉCHEC : Damier non détecté correctement sur l'une des deux images. Réessaye !")

finally:
    cam_left.stop()
    cam_right.stop()
    print(f"\nTerminé ! {pair_count} paires enregistrées dans '{SAVE_DIR}/'.")
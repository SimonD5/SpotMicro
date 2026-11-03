import os
import time
import cv2
import numpy as np
from picamera2 import Picamera2

CHECKERBOARD = (8, 7)
SQUARE_SIZE = 22.0  # mm
SAVE_DIR = "calib_images"
MAX_PAIR_DISPARITY_STD = 1.2  # Seuil de tolérance géométrique (en pixels)

os.makedirs(SAVE_DIR, exist_ok=True)

print("1. Initialisation des caméras...")
cam_left = Picamera2(camera_num=0)
cam_right = Picamera2(camera_num=1)

config = {"main": {"size": (640, 480), "format": "RGB888"}}
cam_left.configure(cam_left.create_video_configuration(**config))
cam_right.configure(cam_right.create_video_configuration(**config))

cam_left.start()
cam_right.start()
time.sleep(1)

FLAGS = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

print("\n--- CAPTURE AVEC VALIDATION EN TEMPS RÉEL ---")
print("Conseils : Garde l'écran de PC entre 40 cm et 1,2 m. Inclinaison modérée (< 25°).\n")

pair_count = 0

try:
    while True:
        cmd = input(f"Paire n°{pair_count + 1} - [ENTRÉE] pour capturer ('q' pour quitter) : ")
        if cmd.lower() == 'q':
            break

        frame_l = cam_left.capture_array()
        frame_r = cam_right.capture_array()

        gray_l = cv2.cvtColor(frame_l, cv2.COLOR_RGB2GRAY)
        gray_r = cv2.cvtColor(frame_r, cv2.COLOR_RGB2GRAY)

        ret_l, corners_l = cv2.findChessboardCorners(gray_l, CHECKERBOARD, FLAGS)
        ret_r, corners_r = cv2.findChessboardCorners(gray_r, CHECKERBOARD, FLAGS)

        if ret_l and ret_r:
            corners_l = cv2.cornerSubPix(gray_l, corners_l, (11, 11), (-1, -1), CRITERIA)
            corners_r = cv2.cornerSubPix(gray_r, corners_r, (11, 11), (-1, -1), CRITERIA)

            pts_l = corners_l.reshape(-1, 2)
            pts_r = corners_r.reshape(-1, 2)

            # Test d'alignement vertical entre les 2 caméras
            y_diff = pts_l[:, 1] - pts_r[:, 1]
            score_std = np.std(y_diff - np.median(y_diff))

            if score_std <= MAX_PAIR_DISPARITY_STD:
                pair_count += 1
                cv2.imwrite(os.path.join(SAVE_DIR, f"left_{pair_count:02d}.jpg"), cv2.cvtColor(frame_l, cv2.COLOR_RGB2BGR))
                cv2.imwrite(os.path.join(SAVE_DIR, f"right_{pair_count:02d}.jpg"), cv2.cvtColor(frame_r, cv2.COLOR_RGB2BGR))
                print(f"  [VALIDE] Score géométrique : {score_std:.2f} px -> Paire {pair_count} ENREGISTRÉE !")
            else:
                print(f"  [REJETÉE] Score : {score_std:.2f} px (trop élevé > {MAX_PAIR_DISPARITY_STD} px).")
                print("            -> Inclinaison trop forte ou moiré sur l'écran. Redresse l'écran !")
        else:
            print("  [ÉCHEC] Damier non vu sur les deux caméras. Ajuste la position.")

finally:
    cam_left.stop()
    cam_right.stop()
    print(f"\nTerminé : {pair_count} paires de haute qualité enregistrées.")
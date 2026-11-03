import os
import time
import cv2
import numpy as np
from picamera2 import Picamera2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKERBOARD = (8, 7)
SQUARE_SIZE = 22.0  # mm
SAVE_DIR = os.path.join(SCRIPT_DIR, "calib_images")
MAX_PAIR_DISPARITY_STD = 1.2  # Seuil de tolérance géométrique (en pixels)

FLAGS = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)


def get_existing_pair_count(save_dir=SAVE_DIR):
    """Retourne le plus grand indice numérique déjà présent dans save_dir pour ne pas écraser les prises."""
    if not os.path.isdir(save_dir):
        return 0
    max_index = 0
    for name in os.listdir(save_dir):
        stem, ext = os.path.splitext(name)
        if ext.lower() != ".jpg":
            continue
        for prefix in ("left_", "right_"):
            if stem.startswith(prefix):
                suffix = stem[len(prefix) :]
                if suffix.isdigit():
                    max_index = max(max_index, int(suffix))
    return max_index


def save_stereo_pair(frame_l, frame_r, save_dir, pair_index):
    """Enregistre la paire left_XX.jpg / right_XX.jpg et vérifie le succès des deux écritures."""
    os.makedirs(save_dir, exist_ok=True)
    left_path = os.path.join(save_dir, f"left_{pair_index:02d}.jpg")
    right_path = os.path.join(save_dir, f"right_{pair_index:02d}.jpg")

    bgr_l = cv2.cvtColor(frame_l, cv2.COLOR_RGB2BGR)
    bgr_r = cv2.cvtColor(frame_r, cv2.COLOR_RGB2BGR)

    ok_l = bool(cv2.imwrite(left_path, bgr_l))
    ok_r = bool(cv2.imwrite(right_path, bgr_r)) if ok_l else False

    if not (ok_l and ok_r):
        for path in (left_path, right_path):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        raise RuntimeError(f"Échec d'écriture disque pour la paire n°{pair_index:02d}.")

    return left_path, right_path


def _stop_camera(cam):
    if cam is None:
        return
    for method_name in ("stop", "close"):
        method = getattr(cam, method_name, None)
        if callable(method):
            try:
                method()
            except Exception:
                pass


def main(save_dir=SAVE_DIR, input_fn=input):
    os.makedirs(save_dir, exist_ok=True)
    pair_count = get_existing_pair_count(save_dir)

    print("1. Initialisation des caméras...")
    cam_left = None
    cam_right = None

    try:
        cam_left = Picamera2(camera_num=0)
        cam_right = Picamera2(camera_num=1)

        config = {"main": {"size": (640, 480), "format": "RGB888"}}
        cam_left.configure(cam_left.create_video_configuration(**config))
        cam_right.configure(cam_right.create_video_configuration(**config))

        cam_left.start()
        cam_right.start()
        time.sleep(1)

        print("\n--- CAPTURE AVEC VALIDATION EN TEMPS RÉEL ---")
        print("Conseils : Garde l'écran de PC entre 40 cm et 1,2 m. Inclinaison modérée (< 25°).\n")

        while True:
            cmd = input_fn(f"Paire n°{pair_count + 1} - [ENTRÉE] pour capturer ('q' pour quitter) : ")
            if cmd.lower() == "q":
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
                    next_index = pair_count + 1
                    save_stereo_pair(frame_l, frame_r, save_dir, next_index)
                    pair_count = next_index
                    print(f"  [VALIDE] Score géométrique : {score_std:.2f} px -> Paire {pair_count} ENREGISTRÉE !")
                else:
                    print(f"  [REJETÉE] Score : {score_std:.2f} px (trop élevé > {MAX_PAIR_DISPARITY_STD} px).")
                    print("            -> Inclinaison trop forte ou moiré sur l'écran. Redresse l'écran !")
            else:
                print("  [ÉCHEC] Damier non vu sur les deux caméras. Ajuste la position.")

    finally:
        _stop_camera(cam_left)
        _stop_camera(cam_right)
        print(f"\nTerminé : {pair_count} paires de haute qualité enregistrées.")


if __name__ == "__main__":
    main()

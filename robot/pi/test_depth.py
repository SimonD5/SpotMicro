import os
import time
import cv2
import numpy as np
from picamera2 import Picamera2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CALIB_FILE = os.path.join(SCRIPT_DIR, "stereo_calib.npz")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "depth_preview.jpg")


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


def main(calib_file=CALIB_FILE, output_file=OUTPUT_FILE):
    # 1. Chargement de la calibration (chemin relatif au script)
    with np.load(calib_file) as calib:
        map_l_x, map_l_y = calib["map_l_x"], calib["map_l_y"]
        map_r_x, map_r_y = calib["map_r_x"], calib["map_r_y"]

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

        print("2. Capture de la paire...")
        frame_l = cam_left.capture_array()
        frame_r = cam_right.capture_array()
    finally:
        _stop_camera(cam_left)
        _stop_camera(cam_right)

    # Conversion BGR
    img_l = cv2.cvtColor(frame_l, cv2.COLOR_RGB2BGR)
    img_r = cv2.cvtColor(frame_r, cv2.COLOR_RGB2BGR)

    # 3. Rectification des images
    rect_l = cv2.remap(img_l, map_l_x, map_l_y, cv2.INTER_LINEAR)
    rect_r = cv2.remap(img_r, map_r_x, map_r_y, cv2.INTER_LINEAR)

    # Conversion en niveaux de gris pour StereoSGBM
    gray_l = cv2.cvtColor(rect_l, cv2.COLOR_BGR2GRAY)
    gray_r = cv2.cvtColor(rect_r, cv2.COLOR_BGR2GRAY)

    # 4. Configuration de l'algorithme Stéréo (StereoSGBM)
    min_disp = 0
    num_disp = 16 * 5  # 80 niveaux de disparité (doit être un multiple de 16)
    block_size = 5

    stereo = cv2.StereoSGBM_create(
        minDisparity=min_disp,
        numDisparities=num_disp,
        blockSize=block_size,
        P1=8 * 3 * block_size**2,
        P2=32 * 3 * block_size**2,
        disp12MaxDiff=1,
        uniquenessRatio=10,
        speckleWindowSize=100,
        speckleRange=32,
    )

    print("3. Calcul de la carte de disparité...")
    disparity = stereo.compute(gray_l, gray_r).astype(np.float32) / 16.0

    # Normalisation pour affichage (0 à 255)
    disp_vis = cv2.normalize(disparity, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    disp_vis = np.uint8(disp_vis)
    disp_color = cv2.applyColorMap(disp_vis, cv2.COLORMAP_JET)

    # Juxtaposition Image Gauche / Carte de Profondeur
    preview = cv2.hconcat([rect_l, disp_color])
    cv2.imwrite(output_file, preview)

    print(f"--> Image '{output_file}' enregistrée.")


if __name__ == "__main__":
    main()

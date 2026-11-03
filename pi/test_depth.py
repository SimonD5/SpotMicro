import time
import cv2
import numpy as np
from picamera2 import Picamera2

# 1. Chargement de la calibration
calib = np.load("pi/stereo_calib.npz")
map_l_x, map_l_y = calib["map_l_x"], calib["map_l_y"]
map_r_x, map_r_y = calib["map_r_x"], calib["map_r_y"]

print("1. Initialisation des caméras...")
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

cam_left.stop()
cam_right.stop()

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
    speckleRange=32
)

print("3. Calcul de la carte de disparité...")
disparity = stereo.compute(gray_l, gray_r).astype(np.float32) / 16.0

# Normalisation pour affichage (0 à 255)
disp_vis = cv2.normalize(disparity, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
disp_vis = np.uint8(disp_vis)
disp_color = cv2.applyColorMap(disp_vis, cv2.COLORMAP_JET)

# Juxtaposition Image Gauche / Carte de Profondeur
preview = cv2.hconcat([rect_l, disp_color])
cv2.imwrite("depth_preview.jpg", preview)

print("--> Image 'depth_preview.jpg' enregistrée.")
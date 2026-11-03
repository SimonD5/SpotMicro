import glob
import os
import cv2
import numpy as np

CHECKERBOARD = (8, 7)
SQUARE_SIZE = 22.0  # mm
MAX_SINGLE_RMS = 1.5  # Seuil d'erreur maximal toléré par photo (en pixels)
MIN_PAIRS_REQUIRED = 4  # Ajusté à 4 pour valider tes 6 images
CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0 : CHECKERBOARD[0], 0 : CHECKERBOARD[1]].T.reshape(-1, 2)
objp *= SQUARE_SIZE

images_l = sorted(glob.glob("calib_images/left_*.jpg"))
images_r = sorted(glob.glob("calib_images/right_*.jpg"))

print(f"1. Analyse de {len(images_l)} paires d'images...")

raw_obj = []
raw_l = []
raw_r = []
valid_files_l = []
valid_files_r = []
image_size = None

for file_l, file_r in zip(images_l, images_r):
    img_l = cv2.imread(file_l)
    img_r = cv2.imread(file_r)

    gray_l = cv2.cvtColor(img_l, cv2.COLOR_BGR2GRAY)
    gray_r = cv2.cvtColor(img_r, cv2.COLOR_BGR2GRAY)

    if image_size is None:
        image_size = (gray_l.shape[1], gray_l.shape[0])

    ret_l, corners_l = cv2.findChessboardCorners(gray_l, CHECKERBOARD, None)
    ret_r, corners_r = cv2.findChessboardCorners(gray_r, CHECKERBOARD, None)

    if ret_l and ret_r:
        corners_l = cv2.cornerSubPix(gray_l, corners_l, (11, 11), (-1, -1), CRITERIA)
        corners_r = cv2.cornerSubPix(gray_r, corners_r, (11, 11), (-1, -1), CRITERIA)

        raw_obj.append(objp)
        raw_l.append(corners_l)
        raw_r.append(corners_r)
        valid_files_l.append(file_l)
        valid_files_r.append(file_r)

# --- FILTRAGE DE LA CAMÉRA GAUCHE ---
ret_l, K_l, D_l, rvecs_l, tvecs_l = cv2.calibrateCamera(raw_obj, raw_l, image_size, None, None)
clean_obj = []
clean_l = []
clean_r = []

for i in range(len(raw_obj)):
    pts_proj, _ = cv2.projectPoints(raw_obj[i], rvecs_l[i], tvecs_l[i], K_l, D_l)
    
    pts_true = raw_l[i].reshape(-1, 2)
    pts_est = pts_proj.reshape(-1, 2)
    err = np.sqrt(np.mean(np.sum((pts_true - pts_est) ** 2, axis=1)))

    if err < MAX_SINGLE_RMS:
        clean_obj.append(raw_obj[i])
        clean_l.append(raw_l[i])
        clean_r.append(raw_r[i])

print(f"\n2. Filtrage des paires : {len(clean_obj)}/{len(raw_obj)} paires conservées (erreur < {MAX_SINGLE_RMS} px).")

if len(clean_obj) < MIN_PAIRS_REQUIRED:
    print(f"  [ERREUR] Moins de {MIN_PAIRS_REQUIRED} paires valides.")
    exit(1)

# --- RECALCUL SUR LES IMAGES PROPRES ---
ret_l, K_l, D_l, _, _ = cv2.calibrateCamera(clean_obj, clean_l, image_size, None, None)
ret_r, K_r, D_r, _, _ = cv2.calibrateCamera(clean_obj, clean_r, image_size, None, None)

print(f"   RMS Gauche filtré : {ret_l:.3f} px")
print(f"   RMS Droite filtré : {ret_r:.3f} px")

print("\n3. Calibration Stéréo finale...")
flags = cv2.CALIB_FIX_INTRINSIC
ret_s, K_l, D_l, K_r, D_r, R, T, E, F = cv2.stereoCalibrate(
    clean_obj, clean_l, clean_r, K_l, D_l, K_r, D_r, image_size, criteria=CRITERIA, flags=flags
)

print(f"   --> Erreur RMS Stéréo : {ret_s:.3f} px")
print(f"   --> Distance calculée (Baseline) : {np.linalg.norm(T):.2f} mm (Cible: ~50 mm)")

print("\n4. Sauvegarde...")
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_l, D_l, K_r, D_r, image_size, R, T, alpha=0)
map_l_x, map_l_y = cv2.initUndistortRectifyMap(K_l, D_l, R1, P1, image_size, cv2.CV_32FC1)
map_r_x, map_r_y = cv2.initUndistortRectifyMap(K_r, D_r, R2, P2, image_size, cv2.CV_32FC1)

np.savez(
    "pi/stereo_calib.npz",
    K_l=K_l, D_l=D_l, K_r=K_r, D_r=D_r,
    R=R, T=T, R1=R1, R2=R2, P1=P1, P2=P2, Q=Q,
    map_l_x=map_l_x, map_l_y=map_l_y, map_r_x=map_r_x, map_r_y=map_r_y
)

last_img_l = cv2.imread(valid_files_l[-1])
last_img_r = cv2.imread(valid_files_r[-1])
rect_l = cv2.remap(last_img_l, map_l_x, map_l_y, cv2.INTER_LINEAR)
rect_r = cv2.remap(last_img_r, map_r_x, map_r_y, cv2.INTER_LINEAR)

rect_combined = cv2.hconcat([rect_l, rect_r])
for y in range(30, image_size[1], 30):
    cv2.line(rect_combined, (0, y), (image_size[0] * 2, y), (0, 0, 255), 1, cv2.LINE_AA)

cv2.imwrite("rectified_test.jpg", rect_combined)
print("--> Fichier 'rectified_test.jpg' généré.")
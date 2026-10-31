import glob
import os
import cv2
import numpy as np

# Configuration du damier (7x7 coins INTERNES, carreaux de 22 mm)
CHECKERBOARD = (7, 7)
SQUARE_SIZE = 22.0  # en millimètres

# Critères de précision pour la recherche des coins au sous-pixel
CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# Préparation des points 3D du damier dans le monde réel : (0,0,0), (22,0,0), (44,0,0)...
objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0 : CHECKERBOARD[0], 0 : CHECKERBOARD[1]].T.reshape(
    -1, 2
)
objp *= SQUARE_SIZE

objpoints = []  # Points 3D réels
imgpoints_l = []  # Points 2D image gauche
imgpoints_r = []  # Points 2D image droite

images_l = sorted(glob.glob("calib_images/left_*.jpg"))
images_r = sorted(glob.glob("calib_images/right_*.jpg"))

print(f"1. Traitement de {len(images_l)} paires d'images de calibration...")

valid_pairs = 0
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
        objpoints.append(objp)

        # Affinage sous-pixelique des coins
        corners_l = cv2.cornerSubPix(
            gray_l, corners_l, (11, 11), (-1, -1), CRITERIA
        )
        corners_r = cv2.cornerSubPix(
            gray_r, corners_r, (11, 11), (-1, -1), CRITERIA
        )

        imgpoints_l.append(corners_l)
        imgpoints_r.append(corners_r)
        valid_pairs += 1

print(f"   --> {valid_pairs}/{len(images_l)} paires valides conservées.")

if valid_pairs < 10:
    print(
        "Erreur : Trop peu de paires valides pour calibrer correctement (minimum 10)."
    )
    exit(1)

print("\n2. Calibration individuelle des deux caméras...")
ret_l, K_l, D_l, _, _ = cv2.calibrateCamera(
    objpoints, imgpoints_l, image_size, None, None
)
ret_r, K_r, D_r, _, _ = cv2.calibrateCamera(
    objpoints, imgpoints_r, image_size, None, None
)

print(f"   Erreur RMS Gauche : {ret_l:.3f} px")
print(f"   Erreur RMS Droite : {ret_r:.3f} px")

print("\n3. Calibration Stéréo (Calcul de la géométrie relative R et T)...")
flags = cv2.CALIB_FIX_INTRINSIC
ret_s, K_l, D_l, K_r, D_r, R, T, E, F = cv2.stereoCalibrate(
    objpoints,
    imgpoints_l,
    imgpoints_r,
    K_l,
    D_l,
    K_r,
    D_r,
    image_size,
    criteria=CRITERIA,
    flags=flags,
)

print(f"   --> Erreur de réprojection Stéréo RMS : {ret_s:.3f} px")
print(
    f"   --> Distance calculée entre les caméras (Baseline) : {np.linalg.norm(T):.2f} mm"
)

print("\n4. Calcul des cartes de rectification d'image (Alignement)...")
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(
    K_l, D_l, K_r, D_r, image_size, R, T, alpha=0
)

# Cartes de déformation pour cv2.remap
map_l_x, map_l_y = cv2.initUndistortRectifyMap(
    K_l, D_l, R1, P1, image_size, cv2.CV_32FC1
)
map_r_x, map_r_y = cv2.initUndistortRectifyMap(
    K_r, D_r, R2, P2, image_size, cv2.CV_32FC1
)

# Enregistrement des données de calibration
out_file = "pi/stereo_calib.npz"
np.savez(
    out_file,
    K_l=K_l,
    D_l=D_l,
    K_r=K_r,
    D_r=D_r,
    R=R,
    T=T,
    R1=R1,
    R2=R2,
    P1=P1,
    P2=P2,
    Q=Q,
    map_l_x=map_l_x,
    map_l_y=map_l_y,
    map_r_x=map_r_x,
    map_r_y=map_r_y,
)
print(f"   --> Fichier de calibration enregistré : '{out_file}'")

# Verification visuelle sur la derniere paire d'images
print("\n5. Génération d'une image de contrôle 'rectified_test.jpg'...")
last_img_l = cv2.imread(images_l[-1])
last_img_r = cv2.imread(images_r[-1])

rect_l = cv2.remap(last_img_l, map_l_x, map_l_y, cv2.INTER_LINEAR)
rect_r = cv2.remap(last_img_r, map_r_x, map_r_y, cv2.INTER_LINEAR)

# Juxtaposition avec lignes horizontales guides rouges
rect_combined = cv2.hconcat([rect_l, rect_r])
for y in range(30, image_size[1], 30):
    cv2.line(
        rect_combined,
        (0, y),
        (image_size[0] * 2, y),
        (0, 0, 255),
        1,
        cv2.LINE_AA,
    )

cv2.imwrite("rectified_test.jpg", rect_combined)
print("   --> Image 'rectified_test.jpg' générée.")
print("\n--- CALIBRATION TERMINÉE AVEC SUCCÈS ---")
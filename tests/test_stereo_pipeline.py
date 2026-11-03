import io
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock
import numpy as np

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
PI_DIR = REPO_ROOT / "robot" / "pi"

for _p in (str(REPO_ROOT), str(PI_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _install_fake_cv2():
    fake_cv2 = types.ModuleType("cv2")
    fake_cv2.TERM_CRITERIA_EPS = 1
    fake_cv2.TERM_CRITERIA_MAX_ITER = 2
    fake_cv2.CALIB_CB_ADAPTIVE_THRESH = 1
    fake_cv2.CALIB_CB_NORMALIZE_IMAGE = 2
    fake_cv2.CALIB_FIX_INTRINSIC = 256
    fake_cv2.CV_32FC1 = 5
    fake_cv2.INTER_LINEAR = 1
    fake_cv2.LINE_AA = 16
    fake_cv2.COLOR_BGR2GRAY = 6
    fake_cv2.COLOR_RGB2GRAY = 7
    fake_cv2.COLOR_RGB2BGR = 4
    fake_cv2.NORM_MINMAX = 32
    fake_cv2.COLORMAP_JET = 2

    base_grid = np.zeros((8 * 7, 1, 2), dtype=np.float32)
    base_grid[:, 0, 0] = np.tile(np.arange(8, dtype=np.float32), 7) * 20.0 + 50.0
    base_grid[:, 0, 1] = np.repeat(np.arange(7, dtype=np.float32), 8) * 20.0 + 50.0

    def cvtColor(img, code):
        arr = np.asarray(img)
        if code in (fake_cv2.COLOR_BGR2GRAY, fake_cv2.COLOR_RGB2GRAY):
            return arr[:, :, 0].copy() if arr.ndim == 3 else arr.copy()
        return arr.copy()

    def imwrite(path, img):
        Path(path).write_bytes(b"FAKE_JPEG")
        return True

    def imread(path):
        if not os.path.exists(path):
            return None
        return np.zeros((480, 640, 3), dtype=np.uint8)

    def findChessboardCorners(gray, pattern_size, flags=None):
        return True, base_grid.copy()

    def cornerSubPix(gray, corners, win_size, zero_zone, criteria):
        return np.asarray(corners, dtype=np.float32).copy()

    def calibrateCamera(obj_list, img_list, image_size, K, D):
        n = len(obj_list)
        if n == 0:
            raise ValueError("calibrateCamera called with empty point list")
        return (
            0.4,
            np.eye(3, dtype=np.float64),
            np.zeros((5, 1), dtype=np.float64),
            [np.zeros((3, 1), dtype=np.float64) for _ in range(n)],
            [np.zeros((3, 1), dtype=np.float64) for _ in range(n)],
        )

    def projectPoints(obj_pts, rvec, tvec, K, D):
        return base_grid.copy(), None

    def stereoCalibrate(obj_list, l_list, r_list, K_l, D_l, K_r, D_r, image_size, criteria=None, flags=0):
        return (
            0.8,
            K_l,
            D_l,
            K_r,
            D_r,
            np.eye(3, dtype=np.float64),
            np.array([[-50.0], [0.0], [0.0]], dtype=np.float64),
            np.eye(3, dtype=np.float64),
            np.eye(3, dtype=np.float64),
        )

    def stereoRectify(K_l, D_l, K_r, D_r, image_size, R, T, alpha=0):
        return (
            np.eye(3, dtype=np.float64),
            np.eye(3, dtype=np.float64),
            np.eye(3, 4, dtype=np.float64),
            np.eye(3, 4, dtype=np.float64),
            np.eye(4, dtype=np.float64),
            (0, 0, image_size[0], image_size[1]),
            (0, 0, image_size[0], image_size[1]),
        )

    def initUndistortRectifyMap(K, D, R, P, size, m1type):
        w, h = size
        return np.zeros((h, w), dtype=np.float32), np.zeros((h, w), dtype=np.float32)

    def remap(img, map_x, map_y, interpolation):
        return np.asarray(img).copy()

    def hconcat(imgs):
        return np.concatenate(imgs, axis=1)

    def line(img, pt1, pt2, color, thickness=1, line_type=0):
        return img

    class _FakeSGBM:
        def compute(self, gray_l, gray_r):
            return np.full(gray_l.shape, 160, dtype=np.int16)

    def StereoSGBM_create(**kwargs):
        return _FakeSGBM()

    def normalize(src, dst, alpha=0, beta=255, norm_type=32):
        return np.zeros_like(src, dtype=np.float32)

    def applyColorMap(src, colormap):
        arr = np.asarray(src, dtype=np.uint8)
        return np.stack([arr, arr, arr], axis=-1)

    fake_cv2.cvtColor = cvtColor
    fake_cv2.imwrite = imwrite
    fake_cv2.imread = imread
    fake_cv2.findChessboardCorners = findChessboardCorners
    fake_cv2.cornerSubPix = cornerSubPix
    fake_cv2.calibrateCamera = calibrateCamera
    fake_cv2.projectPoints = projectPoints
    fake_cv2.stereoCalibrate = stereoCalibrate
    fake_cv2.stereoRectify = stereoRectify
    fake_cv2.initUndistortRectifyMap = initUndistortRectifyMap
    fake_cv2.remap = remap
    fake_cv2.hconcat = hconcat
    fake_cv2.line = line
    fake_cv2.StereoSGBM_create = StereoSGBM_create
    fake_cv2.normalize = normalize
    fake_cv2.applyColorMap = applyColorMap
    sys.modules["cv2"] = fake_cv2
    return fake_cv2


class FakePicamera2:
    instances = []
    fail_on_camera = None

    def __init__(self, camera_num=0):
        self.camera_num = camera_num
        self.configured = None
        self.started = False
        self.stopped = False
        self.closed = False
        FakePicamera2.instances.append(self)

    def create_video_configuration(self, **kwargs):
        return kwargs

    def configure(self, config):
        self.configured = config

    def start(self):
        self.started = True

    def capture_array(self):
        if FakePicamera2.fail_on_camera == self.camera_num:
            raise RuntimeError(f"Erreur capture simulée sur caméra {self.camera_num}")
        return np.zeros((480, 640, 3), dtype=np.uint8)

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


def _install_fake_picamera2():
    mod = types.ModuleType("picamera2")
    mod.Picamera2 = FakePicamera2
    sys.modules["picamera2"] = mod
    return mod


_install_fake_cv2()
_install_fake_picamera2()

import capture_calibration  # noqa: E402
import calibrate_stereo  # noqa: E402
import test_depth  # noqa: E402


class TestStereoPipeline(unittest.TestCase):
    def setUp(self):
        FakePicamera2.instances.clear()
        FakePicamera2.fail_on_camera = None

    def test_capture_calibration_persists_existing_counter_and_saves_next_pair(self):
        with tempfile.TemporaryDirectory(dir=TESTS_DIR) as tmpdir:
            for idx in (1, 2, 6):
                Path(tmpdir, f"left_{idx:02d}.jpg").write_bytes(b"existing")
                Path(tmpdir, f"right_{idx:02d}.jpg").write_bytes(b"existing")

            self.assertEqual(capture_calibration.get_existing_pair_count(tmpdir), 6)

            inputs = iter(["", "q"])
            with (
                mock.patch("capture_calibration.time.sleep"),
                mock.patch("sys.stdout", new_callable=io.StringIO),
            ):
                capture_calibration.main(save_dir=tmpdir, input_fn=lambda _p: next(inputs))

            # Les prises existantes ne sont pas écrasées et la nouvelle prise porte l'indice 07
            self.assertEqual(Path(tmpdir, "left_01.jpg").read_bytes(), b"existing")
            self.assertTrue(Path(tmpdir, "left_07.jpg").is_file())
            self.assertTrue(Path(tmpdir, "right_07.jpg").is_file())
            self.assertEqual(len(FakePicamera2.instances), 2)
            self.assertTrue(all(cam.stopped and cam.closed for cam in FakePicamera2.instances))

    def test_capture_calibration_imwrite_failure_cleans_partial_file(self):
        with tempfile.TemporaryDirectory(dir=TESTS_DIR) as tmpdir:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)

            def fail_on_right(path, img):
                if os.path.basename(path).startswith("left_"):
                    Path(path).write_bytes(b"left_written")
                    return True
                return False

            with mock.patch.object(capture_calibration.cv2, "imwrite", side_effect=fail_on_right):
                with self.assertRaises(RuntimeError):
                    capture_calibration.save_stereo_pair(frame, frame, tmpdir, 7)

            self.assertFalse(Path(tmpdir, "left_07.jpg").exists())
            self.assertFalse(Path(tmpdir, "right_07.jpg").exists())

    def test_calibrate_stereo_matches_by_id_and_skips_unreadable_images(self):
        images_l = ["calib_images/left_10.jpg", "calib_images/left_01.jpg", "calib_images/left_02.jpg"]
        images_r = ["calib_images/right_01.jpg", "calib_images/right_03.jpg", "calib_images/right_10.jpg"]
        self.assertEqual(
            calibrate_stereo.match_image_pairs(images_l, images_r),
            [
                ("calib_images/left_01.jpg", "calib_images/right_01.jpg"),
                ("calib_images/left_10.jpg", "calib_images/right_10.jpg"),
            ],
        )

        with tempfile.TemporaryDirectory(dir=TESTS_DIR) as tmpdir:
            calib_dir = os.path.join(tmpdir, "calib_images")
            os.makedirs(calib_dir, exist_ok=True)
            # 5 paires synchronisées + 1 fichier orphelin ; la paire 02 sera illisible
            for idx in (1, 2, 3, 4, 5):
                Path(calib_dir, f"left_{idx:02d}.jpg").write_bytes(b"img")
                Path(calib_dir, f"right_{idx:02d}.jpg").write_bytes(b"img")
            Path(calib_dir, "left_99.jpg").write_bytes(b"orphan")

            out_npz = os.path.join(tmpdir, "out_calib.npz")
            out_rect = os.path.join(tmpdir, "out_rect.jpg")

            def imread_with_corrupt(path):
                if "left_02.jpg" in path:
                    return None
                return np.zeros((480, 640, 3), dtype=np.uint8)

            with (
                mock.patch.object(calibrate_stereo.cv2, "imread", side_effect=imread_with_corrupt),
                mock.patch("sys.stdout", new_callable=io.StringIO),
            ):
                calibrate_stereo.main(calib_dir=calib_dir, output_file=out_npz, rectified_file=out_rect)

            self.assertTrue(os.path.isfile(out_npz))
            self.assertTrue(os.path.isfile(out_rect))

    def test_calibrate_stereo_exits_cleanly_when_insufficient_or_unreadable_pairs(self):
        with tempfile.TemporaryDirectory(dir=TESTS_DIR) as tmpdir:
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as ctx_empty:
                    calibrate_stereo.main(calib_dir=tmpdir)
            self.assertEqual(ctx_empty.exception.code, 1)

            for idx in (1, 2, 3, 4):
                Path(tmpdir, f"left_{idx:02d}.jpg").write_bytes(b"bad")
                Path(tmpdir, f"right_{idx:02d}.jpg").write_bytes(b"bad")

            with (
                mock.patch.object(calibrate_stereo.cv2, "imread", return_value=None),
                mock.patch("sys.stdout", new_callable=io.StringIO),
            ):
                with self.assertRaises(SystemExit) as ctx_unreadable:
                    calibrate_stereo.main(calib_dir=tmpdir)
            self.assertEqual(ctx_unreadable.exception.code, 1)

    def test_test_depth_uses_script_relative_calib_and_closes_cameras_in_finally(self):
        self.assertEqual(
            Path(test_depth.CALIB_FILE).resolve(),
            (PI_DIR / "stereo_calib.npz").resolve(),
        )

        with tempfile.TemporaryDirectory(dir=TESTS_DIR) as tmpdir:
            preview_path = os.path.join(tmpdir, "depth_preview.jpg")
            with (
                mock.patch("test_depth.time.sleep"),
                mock.patch("sys.stdout", new_callable=io.StringIO),
            ):
                test_depth.main(calib_file=test_depth.CALIB_FILE, output_file=preview_path)

            self.assertTrue(os.path.isfile(preview_path))
            self.assertEqual(len(FakePicamera2.instances), 2)
            self.assertTrue(all(cam.stopped and cam.closed for cam in FakePicamera2.instances))

            # Vérifie la fermeture en finally même si la capture de la caméra droite échoue
            FakePicamera2.instances.clear()
            FakePicamera2.fail_on_camera = 1
            with (
                mock.patch("test_depth.time.sleep"),
                mock.patch("sys.stdout", new_callable=io.StringIO),
            ):
                with self.assertRaises(RuntimeError):
                    test_depth.main(calib_file=test_depth.CALIB_FILE, output_file=preview_path)

            self.assertEqual(len(FakePicamera2.instances), 2)
            self.assertTrue(all(cam.stopped and cam.closed for cam in FakePicamera2.instances))


if __name__ == "__main__":
    unittest.main()

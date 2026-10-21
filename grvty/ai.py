"""AI mode: a small network picks how to blend a few learned colour cubes for
each photo. Runs with OpenCV (already part of Grvty), no extra libraries."""
from pathlib import Path

import cv2
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"


class GradeAI:
    def __init__(self, name="grvty_ai", folder=MODEL_DIR):
        self.onnx = Path(folder) / f"{name}.onnx"
        self.npz = Path(folder) / f"{name}.npz"
        self.net = None
        self.luts = None

    def available(self):
        return self.onnx.exists() and self.npz.exists()

    def _load(self):
        if self.net is None:
            self.net = cv2.dnn.readNetFromONNX(str(self.onnx))
            self.luts = np.load(self.npz)["luts"].astype(np.float32)   # (N, 3, D, D, D) as [c, b, g, r]

    def weights(self, display_img):
        """display_img: HxWx3 float 0..1 (the photo as Grvty shows it by default)."""
        self._load()
        small = cv2.resize(display_img, (256, 256), interpolation=cv2.INTER_AREA)
        self.net.setInput(np.ascontiguousarray(np.transpose(small, (2, 0, 1))[None], dtype=np.float32))
        return self.net.forward().ravel().astype(np.float32)

    def cube(self, w):
        self._load()
        return np.tensordot(w, self.luts, axes=1)        # (3, D, D, D)

    @staticmethod
    def apply(cube, img):
        """Trilinear lookup of every pixel in a (3, D, D, D) colour cube.

        The cube is laid out as a flat image (rows = green, columns = blue
        slice * D + red), so OpenCV's fast, multi-core bilinear remap does the
        red/green part; two slices are then blended for blue."""
        d = cube.shape[-1]
        tex = np.ascontiguousarray(np.transpose(cube, (2, 1, 3, 0)).reshape(d, d * d, 3), dtype=np.float32)  # [g, b*d + r, c]
        x = np.clip(img, 0, 1).astype(np.float32) * (d - 1)
        r, g, b = x[..., 0], x[..., 1], x[..., 2]
        b0 = np.minimum(np.floor(b), d - 2)
        fb = (b - b0)[..., None]
        mx0 = b0 * d + r
        s0 = cv2.remap(tex, mx0, g, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        s1 = cv2.remap(tex, mx0 + d, g, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        out = s0 + (s1 - s0) * fb
        return np.clip(out, 0, 1)

    def grade(self, display_img, w=None):
        if w is None:
            w = self.weights(display_img)
        return self.apply(self.cube(w), display_img), w

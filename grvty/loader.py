"""Opening photos (RAW and JPEG/PNG/TIFF/HEIC-less) into linear float images."""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

RAW_EXT = {".cr2", ".cr3", ".crw", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".raf",
           ".orf", ".rw2", ".pef", ".dng", ".srw", ".3fr", ".iiq", ".x3f", ".rwl"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}
SUPPORTED = RAW_EXT | IMG_EXT


def srgb_to_linear(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(np.float32)


def linear_to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055).astype(np.float32)


def is_raw(path):
    return Path(path).suffix.lower() in RAW_EXT


def load_linear(path, half=False):
    """Return (linear float32 HxWx3 image, info dict).

    RAW: demosaiced with the camera's white balance, kept linear (scene-referred,
    values can exceed 1). JPEG etc.: decoded and converted from sRGB to linear.
    """
    path = Path(path)
    if is_raw(path):
        import rawpy
        with rawpy.imread(str(path)) as r:
            rgb = r.postprocess(use_camera_wb=True, half_size=half, output_bps=16,
                                gamma=(1, 1), no_auto_bright=True,
                                output_color=rawpy.ColorSpace.sRGB,
                                user_flip=None)
        img = rgb.astype(np.float32) / 65535.0
        return img, {"raw": True}
    im = Image.open(path)
    im = ImageOps.exif_transpose(im).convert("RGB")
    arr = np.asarray(im, dtype=np.float32) / 255.0
    return srgb_to_linear(arr), {"raw": False}


def resize_long(img, long_edge):
    h, w = img.shape[:2]
    s = long_edge / max(h, w)
    if s >= 1:
        return img
    return cv2.resize(img, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)


def to_jpeg_bytes(srgb_float, quality=90):
    arr = (np.clip(srgb_float, 0, 1) * 255 + 0.5).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(arr, cv2.COLOR_RGB2BGR),
                           [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes()


def save_image(srgb_float, path, quality=95):
    path = Path(path)
    arr = (np.clip(srgb_float, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(arr).save(path, quality=quality, subsampling=0)

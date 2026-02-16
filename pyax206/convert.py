from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

import numpy as np
from PIL import Image

ScalingMode = Literal["letterbox", "crop", "stretch"]

@dataclass
class FrameSpec:
    width: int
    height: int
    rotation: int = 0  # 0, 90, 180, 270
    scaling: ScalingMode = "letterbox"

def pil_to_rgb565_be_bytes(img: Image.Image, spec: FrameSpec) -> bytes:
    """Convert PIL image to RGB565 big-endian bytes."""
    rotation = spec.rotation % 360
    if rotation:
        img = img.rotate(rotation, expand=True)

    img = img.convert("RGB").resize((spec.width, spec.height))
    px = np.asarray(img, dtype=np.uint8)  # HxWx3 RGB

    r = px[..., 0].astype(np.uint16)
    g = px[..., 1].astype(np.uint16)
    b = px[..., 2].astype(np.uint16)

    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    hi = (rgb565 >> 8).astype(np.uint8)
    lo = (rgb565 & 0xFF).astype(np.uint8)

    out = np.empty((spec.height, spec.width, 2), dtype=np.uint8)
    out[..., 0] = hi
    out[..., 1] = lo
    return out.tobytes()

def _rotate_bgr(frame_bgr: np.ndarray, rotation: int) -> np.ndarray:
    rot = rotation % 360
    if rot == 0:
        return frame_bgr
    if rot == 90:
        return np.rot90(frame_bgr, k=3)  # clockwise
    if rot == 180:
        return np.rot90(frame_bgr, k=2)
    if rot == 270:
        return np.rot90(frame_bgr, k=1)  # counterclockwise
    raise ValueError("rotation must be 0/90/180/270")

def _fit_to_size_bgr(frame_bgr: np.ndarray, w: int, h: int, mode: ScalingMode) -> np.ndarray:
    import cv2

    src_h, src_w = frame_bgr.shape[:2]
    if mode == "stretch":
        return cv2.resize(frame_bgr, (w, h), interpolation=cv2.INTER_AREA)

    if mode == "letterbox":
        scale = min(w / src_w, h / src_h)
        new_w = max(1, int(src_w * scale))
        new_h = max(1, int(src_h * scale))
        resized = cv2.resize(frame_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        x0 = (w - new_w) // 2
        y0 = (h - new_h) // 2
        canvas[y0:y0+new_h, x0:x0+new_w] = resized
        return canvas

    if mode == "crop":
        scale = max(w / src_w, h / src_h)
        new_w = max(1, int(src_w * scale))
        new_h = max(1, int(src_h * scale))
        resized = cv2.resize(frame_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        x0 = (new_w - w) // 2
        y0 = (new_h - h) // 2
        return resized[y0:y0+h, x0:x0+w]

    raise ValueError("scaling must be 'letterbox', 'crop', or 'stretch'")

def bgr_to_rgb565_be_bytes(frame_bgr: np.ndarray, spec: FrameSpec) -> bytes:
    """Convert BGR numpy frame to RGB565 big-endian bytes with rotation+scaling."""
    frame_bgr = _rotate_bgr(frame_bgr, spec.rotation)
    frame_bgr = _fit_to_size_bgr(frame_bgr, spec.width, spec.height, spec.scaling)

    b = frame_bgr[..., 0].astype(np.uint16)
    g = frame_bgr[..., 1].astype(np.uint16)
    r = frame_bgr[..., 2].astype(np.uint16)

    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    hi = (rgb565 >> 8).astype(np.uint8)
    lo = (rgb565 & 0xFF).astype(np.uint8)

    out = np.empty((spec.height, spec.width, 2), dtype=np.uint8)
    out[..., 0] = hi
    out[..., 1] = lo
    return out.tobytes()

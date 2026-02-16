from __future__ import annotations
import time
import cv2

def play_video(display, *, path: str, fps: float | None = None):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {path}")

    src_fps = cap.get(cv2.CAP_PROP_FPS)
    if fps is None:
        fps = src_fps if src_fps and src_fps > 0 else 3.0

    display.set_fps_limit(fps)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        display.show_numpy_bgr(frame)
        time.sleep(0.001)

    cap.release()

from __future__ import annotations
import time
import numpy as np

def _draw_fps_transparent(img_bgr, text: str, *, alpha: float = 0.35, x: int = 8, y: int = 18):
    import cv2
    overlay = img_bgr.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.55
    thickness = 1
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    pad = 6
    x0, y0 = max(0, x - pad), max(0, y - th - pad)
    x1, y1 = min(img_bgr.shape[1]-1, x + tw + pad), min(img_bgr.shape[0]-1, y + baseline + pad)
    cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 0, 0), thickness=-1)
    cv2.addWeighted(overlay, alpha, img_bgr, 1 - alpha, 0, img_bgr)
    cv2.putText(img_bgr, text, (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)

def mirror_windows(display, *, monitor: int = 1, fps: float = 3.0,
                   show_fps: bool = True, overlay_alpha: float = 0.35):

    import mss
    import cv2
    import numpy as np
    import time

    sct = mss.mss()
    mon = sct.monitors[monitor]

    display.set_fps_limit(fps)

    last = time.time()
    fps_smooth = 0.0
    smoothing = 0.15

    while True:
        shot = sct.grab(mon)
        frame = np.array(shot)  # BGRA
        bgr = frame[:, :, :3]

        # Determine target resize size BEFORE rotation
        if display.spec.rotation % 180 == 0:
            target_w = display.spec.width
            target_h = display.spec.height
        else:
            target_w = display.spec.height
            target_h = display.spec.width

        bgr = cv2.resize(
            bgr,
            (target_w, target_h),
            interpolation=cv2.INTER_AREA
        )

        # FPS overlay
        if show_fps:
            now = time.time()
            dt = now - last
            last = now
            fps_inst = (1.0 / dt) if dt > 0 else 0.0
            fps_smooth = (1 - smoothing) * fps_smooth + smoothing * fps_inst
            _draw_fps_transparent(bgr, f"{fps_smooth:0.2f} FPS", alpha=overlay_alpha)

        # Rotation happens inside convert.py
        display.show_numpy_bgr(bgr)

        time.sleep(0.001)




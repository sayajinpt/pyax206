from __future__ import annotations
import time
from typing import Optional, Iterable, Union

import numpy as np
from PIL import Image

from .constants import DEFAULT_VID, DEFAULT_PID, DEFAULT_WIDTH, DEFAULT_HEIGHT
from .transport import AX206Transport, USBConfig
from .convert import FrameSpec, pil_to_rgb565_be_bytes, bgr_to_rgb565_be_bytes, ScalingMode
from .framebuffer import FrameBuffer

class AX206Display:
    """High-level AX206 display API."""

    def __init__(
        self,
        *,
        vid: int = DEFAULT_VID,
        pid: int = DEFAULT_PID,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        rotation: int = 270,
        scaling: ScalingMode = "letterbox",
        fps_limit: Optional[float] = 3.0,
        chunk_size: int = 16384,
        auto_reconnect: bool = True,
        tag: int = 0xDEADBEEF,
        auto_init: bool = True,
    ):
        self.spec = FrameSpec(width=width, height=height, rotation=rotation, scaling=scaling)
        self.fps_limit = fps_limit
        self._min_interval = (1.0 / fps_limit) if fps_limit and fps_limit > 0 else 0.0
        self._last_send = 0.0

        cfg = USBConfig(vid=vid, pid=pid)
        self._t = AX206Transport(cfg, chunk_size=chunk_size, tag=tag, auto_reconnect=auto_reconnect)
        self._fb: Optional[FrameBuffer] = None
        self._auto_init = auto_init

    def open(self) -> "AX206Display":
        self._t.open()
        if self._auto_init:
            self._t.init()
        return self

    def close(self) -> None:
        self._t.close()

    def reconnect(self) -> None:
        self._t.reconnect()
        if self._auto_init:
            self._t.init()

    def set_rotation(self, rotation: int) -> None:
        self.spec.rotation = rotation % 360

    def set_scaling(self, scaling: ScalingMode) -> None:
        self.spec.scaling = scaling

    def set_fps_limit(self, fps: Optional[float]) -> None:
        self.fps_limit = fps
        self._min_interval = (1.0 / fps) if fps and fps > 0 else 0.0

    def begin_draw(self, portrait: bool = False) -> FrameBuffer:
        if portrait:
            self._fb = FrameBuffer(width=320, height=480)
        else:
            self._fb = FrameBuffer(width=self.spec.width, height=self.spec.height)
        return self._fb

    def end_draw(self) -> None:
        if self._fb is None:
            return
        self.show_pil(self._fb.get_image())
        self._fb = None

    def _throttle(self) -> None:
        if self._min_interval <= 0:
            return
        now = time.time()
        dt = now - self._last_send
        if dt < self._min_interval:
            time.sleep(self._min_interval - dt)

    def show_rgb565(self, frame_bytes: bytes) -> None:
        self._throttle()
        self._t.send_frame(frame_bytes)
        self._last_send = time.time()

    def show_pil(self, img: Image.Image) -> None:
        frame = pil_to_rgb565_be_bytes(img, self.spec)
        self.show_rgb565(frame)

    def show_numpy_bgr(self, frame_bgr: np.ndarray) -> None:
        frame = bgr_to_rgb565_be_bytes(frame_bgr, self.spec)
        self.show_rgb565(frame)

    def show_image(self, path: str) -> None:
        img = Image.open(path)
        self.show_pil(img)

    def stream(self, frames: Iterable[Union[Image.Image, np.ndarray, bytes]], *, kind: str = "auto") -> None:
        for f in frames:
            if kind == "pil" or (kind == "auto" and isinstance(f, Image.Image)):
                self.show_pil(f)  # type: ignore[arg-type]
            elif kind == "bgr" or (kind == "auto" and isinstance(f, np.ndarray)):
                self.show_numpy_bgr(f)  # type: ignore[arg-type]
            elif kind == "rgb565" or (kind == "auto" and isinstance(f, (bytes, bytearray))):
                self.show_rgb565(bytes(f))
            else:
                raise TypeError(f"Unsupported frame type for kind={kind}: {type(f)}")

    def mirror_windows(self, monitor: int = 1, fps: float = 3.0, *, show_fps: bool = True, overlay_alpha: float = 0.35) -> None:
        from .mirror import mirror_windows
        mirror_windows(self, monitor=monitor, fps=fps, show_fps=show_fps, overlay_alpha=overlay_alpha)

    def play_video(self, path: str, fps: Optional[float] = None) -> None:
        from .video import play_video
        play_video(self, path=path, fps=fps)

    def attach_process(self, argv: list[str], *, fps: float = 2.0, max_lines: int = 24, title: str = "process") -> None:
        from .console import attach_process
        attach_process(self, argv=argv, fps=fps, max_lines=max_lines, title=title)

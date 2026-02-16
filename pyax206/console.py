from __future__ import annotations
import time
import threading
import queue
import subprocess
from collections import deque
from PIL import Image, ImageDraw, ImageFont

def attach_process(display, *, argv: list[str], fps: float = 2.0, max_lines: int = 24, title: str = "process"):
    display.set_fps_limit(fps)

    proc = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    q: queue.Queue[str | None] = queue.Queue()

    def _reader():
        assert proc.stdout is not None
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            q.put(line.rstrip("\r\n"))
        q.put(None)

    threading.Thread(target=_reader, daemon=True).start()

    lines = deque(maxlen=max(200, max_lines * 10))
    font = ImageFont.load_default()

    def render(lines_list):
        pw, ph = 320, 480
        img = Image.new("RGB", (pw, ph), (0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, pw, 36], fill=(25, 25, 25))
        d.text((8, 10), title, fill=(255, 255, 255), font=font)
        d.text((pw - 70, 10), time.strftime("%H:%M:%S"), fill=(200, 200, 200), font=font)

        y = 44
        line_h = 12
        max_visible = (ph - y - 8) // line_h
        view = lines_list[-max_visible:]

        for ln in view:
            if len(ln) > 52:
                ln = ln[:52] + "…"
            d.text((8, y), ln, fill=(255, 255, 255), font=font)
            y += line_h

        return img.rotate(display.spec.rotation, expand=True)

    last_push = 0.0
    interval = 1.0 / max(1.0, fps)

    while True:
        while True:
            try:
                item = q.get_nowait()
            except queue.Empty:
                break
            if item is None:
                return
            lines.append(item)

        now = time.time()
        if now - last_push >= interval:
            display.show_pil(render(list(lines)))
            last_push = now

        if proc.poll() is not None:
            return

        time.sleep(0.02)

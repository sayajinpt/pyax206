# pyax206

A Python SDK for **AX206-based USB LCD photo-frame displays** (e.g. 3.5" 480×320 “USB-Display”, VID:PID **1908:0102**).

**Protocol**
- BOT-style CBW/CSW over bulk endpoints
- Full-frame updates in **RGB565 big-endian**
- Practical full-screen throughput: **~2–3 FPS**
## Install

Basic:
```bash
pip install pyax206
```

With mirror+video extras:
```bash
pip install "pyax206[all]"
```

## Windows driver note

On Windows, PyUSB typically needs a libusb-compatible driver (commonly libusb-win32/libusb0).
Can be installed using Zadig software.
Close any software already controlling the LCD (AIDA64/vendor app).

## Quick start

## intall 
## pip install ".[all]"



```python
from pyax206 import AX206Display

d = AX206Display(rotation=270).open()
d.show_image("wallpaper.png")
d.close()
```

### Draw UI

```python
from pyax206 import AX206Display
import time

d = AX206Display(rotation=270).open()
fb = d.begin_draw(portrait=True)
fb.clear((0,0,0))
fb.text((10,10), "pyax206 demo")
fb.text((10,30), time.strftime("%Y-%m-%d %H:%M:%S"))
d.end_draw()
d.close()
```

## CLI

```bash
pyax206 image wallpaper.png
pyax206 mirror --monitor 1 --fps 3
pyax206 video video.mp4 --fps 3
pyax206 proc -- minerd.exe --algo=sha256d --url=... --user=... --threads=16
```

## License

MIT

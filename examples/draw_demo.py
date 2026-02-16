from pyax206 import AX206Display
import time

d = AX206Display(rotation=0, fps_limit=2.5).open()
fb = d.begin_draw(portrait=True)
fb.clear((0,0,0))
fb.text((10,10), "pyax206 demo")
fb.text((10,30), time.strftime("%Y-%m-%d %H:%M:%S"))
d.end_draw()
d.close()

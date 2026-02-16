from pyax206 import AX206Display

d = AX206Display(rotation=0).open()
d.mirror_windows(monitor=1, fps=3, show_fps=True, overlay_alpha=0.35)

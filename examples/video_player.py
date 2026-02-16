from pyax206 import AX206Display

d = AX206Display(rotation=0).open()
d.play_video("video.mp4", fps=3)

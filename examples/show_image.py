from pyax206 import AX206Display

d = AX206Display(rotation=270).open()
d.show_image("wallpaper.png")
d.close()

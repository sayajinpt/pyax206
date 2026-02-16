from pyax206 import AX206Display

d = AX206Display(rotation=0).open()
d.attach_process(["ping", "8.8.8.8", "-t"], fps=2, title="ping")

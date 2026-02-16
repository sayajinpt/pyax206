import time
from datetime import datetime
from PIL import ImageFont
from pyax206 import AX206Display

def load_font(size: int):
    # Try common Windows fonts; fall back to default if not found.
    for path in [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/seguisb.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

def draw_clock(fb, now: datetime, fonts):
    W, H = fb.width, fb.height

    bg = (12, 14, 18)
    panel = (20, 24, 32)
    text = (245, 245, 245)
    muted = (170, 180, 195)
    accent = (80, 170, 255)

    fb.clear(bg)

    # Top header bar
    fb.rectangle([0, 0, W, 70], fill=panel)
    fb.text((16, 22), "CLOCK", fill=accent, font=fonts["small_bold"])
    fb.text((W - 16 - 90, 24), now.strftime("%a"), fill=muted, font=fonts["small"])

    # Main time
    time_str = now.strftime("%H:%M")
    sec_str = now.strftime("%S")
    fb.text((16, 110), time_str, fill=text, font=fonts["time"])
    fb.text((W - 16 - 60, 160), sec_str, fill=accent, font=fonts["secs"])

    # Date
    fb.text((18, 230), now.strftime("%A, %d %B %Y"), fill=muted, font=fonts["medium"])

    # Seconds progress bar
    bar_x0, bar_y0 = 18, 280
    bar_x1, bar_y1 = W - 18, 304
    fb.rectangle([bar_x0, bar_y0, bar_x1, bar_y1], outline=(60, 70, 85), width=2)
    pct = now.second / 60.0
    fill_w = int((bar_x1 - bar_x0 - 4) * pct)
    fb.rectangle([bar_x0 + 2, bar_y0 + 2, bar_x0 + 2 + fill_w, bar_y1 - 2], fill=accent)

    # Footer
    fb.text((18, H - 40), "pyax206 • AX206", fill=(120, 130, 150), font=fonts["tiny"])

def main():
    # Portrait UI canvas is 320x480; display rotates to your 480x320 panel
    d = AX206Display(rotation=270, fps_limit=1).open()

    fonts = {
        "tiny": load_font(14),
        "small": load_font(18),
        "small_bold": load_font(18),
        "medium": load_font(22),
        "time": load_font(84),
        "secs": load_font(40),
    }

    try:
        while True:
            now = datetime.now()

            fb = d.begin_draw(portrait=True)
            draw_clock(fb, now, fonts)
            d.end_draw()

            # tick near the top of the next second
            time.sleep(max(0.05, 1.0 - (time.time() % 1.0)))
    finally:
        d.close()

if __name__ == "__main__":
    main()

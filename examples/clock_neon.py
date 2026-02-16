import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pyax206 import AX206Display

fps_limit=2

def load_font(size: int, bold=False):
    # Try a few common Windows fonts; fallback to default.
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

def neon_glow(base: Image.Image, draw_fn, glow_radius=8, glow_strength=2):
    """Draw glow by rendering to a separate layer and blurring."""
    w, h = base.size
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow_layer)
    draw_fn(d)  # draw neon shapes/text to glow layer
    blurred = glow_layer.filter(ImageFilter.GaussianBlur(glow_radius))

    out = base.convert("RGBA")
    for _ in range(glow_strength):
        out = Image.alpha_composite(out, blurred)
    out = Image.alpha_composite(out, glow_layer)
    return out

def add_scanlines(img: Image.Image, spacing=4, alpha=28):
    """Subtle scanlines across the whole UI."""
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for y in range(0, h, spacing):
        d.line([(0, y), (w, y)], fill=(0, 0, 0, alpha), width=1)
    return Image.alpha_composite(img.convert("RGBA"), overlay)

def gradient_bg(w, h):
    """Cyberpunk teal→purple vertical gradient + vignette."""
    top = (8, 14, 22)
    mid = (14, 8, 24)
    bot = (6, 2, 18)
    img = Image.new("RGB", (w, h), top)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.5:
            a = t / 0.5
            r = int(top[0] + a * (mid[0] - top[0]))
            g = int(top[1] + a * (mid[1] - top[1]))
            b = int(top[2] + a * (mid[2] - top[2]))
        else:
            a = (t - 0.5) / 0.5
            r = int(mid[0] + a * (bot[0] - mid[0]))
            g = int(mid[1] + a * (bot[1] - mid[1]))
            b = int(mid[2] + a * (bot[2] - mid[2]))
        for x in range(w):
            px[x, y] = (r, g, b)

    # vignette
    vign = Image.new("L", (w, h), 0)
    dv = ImageDraw.Draw(vign)
    dv.ellipse([-w*0.2, -h*0.1, w*1.2, h*1.1], fill=255)
    vign = vign.filter(ImageFilter.GaussianBlur(30))
    vign = Image.eval(vign, lambda v: int(v * 0.85))
    img = Image.composite(img, Image.new("RGB", (w, h), (0, 0, 0)), ImageOps.invert(vign))
    return img

def hud_panel(img_rgba, box, outline=(0, 240, 255, 190), fill=(0, 0, 0, 70), corner=16):
    """Rounded HUD panel with neon outline."""
    x0, y0, x1, y1 = box
    panel = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(panel)
    d.rounded_rectangle(box, radius=corner, fill=fill, outline=outline, width=2)
    return Image.alpha_composite(img_rgba, panel)

def draw_clock_frame(now: datetime, fonts):
    W, H = 320, 480  # portrait canvas for best readability
    # Neon palette
    CYAN = (0, 240, 255)
    MAG  = (255, 50, 180)
    PURP = (160, 80, 255)
    TXT  = (240, 245, 255)
    MUT  = (160, 170, 190)

    # Base background (simple gradient using PIL ops; keep it fast)
    base = Image.new("RGB", (W, H), (8, 10, 18))
    d0 = ImageDraw.Draw(base)
    # soft gradient bands
    for y in range(H):
        t = y / (H - 1)
        r = int(10 + 18 * (1 - t) + 6 * t)
        g = int(10 + 6 * (1 - t) + 2 * t)
        b = int(22 + 22 * (1 - t) + 30 * t)
        d0.line([(0, y), (W, y)], fill=(r, g, b))

    img = base.convert("RGBA")

    # Panels
    img = hud_panel(img, (14, 14, W - 14, 90), outline=(CYAN[0], CYAN[1], CYAN[2], 170), fill=(0, 0, 0, 90))
    img = hud_panel(img, (14, 108, W - 14, 328), outline=(MAG[0], MAG[1], MAG[2], 150), fill=(0, 0, 0, 80))
    img = hud_panel(img, (14, 350, W - 14, H - 14), outline=(PURP[0], PURP[1], PURP[2], 150), fill=(0, 0, 0, 70))

    # Neon header + tiny system text
    def draw_header(glowdraw):
        glowdraw.text((22, 26), "AX206 // CLOCK", font=fonts["small_bold"], fill=(CYAN[0], CYAN[1], CYAN[2], 255))
        glowdraw.text((22, 58), now.strftime("%a %d %b %Y"), font=fonts["small"], fill=(MUT[0], MUT[1], MUT[2], 255))

    img = neon_glow(img, draw_header, glow_radius=6, glow_strength=2)

    d = ImageDraw.Draw(img)

    # Big time
    hhmm = now.strftime("%H:%M")
    ss = now.strftime("%S")

    # time glow
    def draw_time(glowdraw):
        glowdraw.text((26, 132), hhmm, font=fonts["time"], fill=(TXT[0], TXT[1], TXT[2], 255))
        glowdraw.text((232, 208), ss, font=fonts["secs"], fill=(MAG[0], MAG[1], MAG[2], 255))

    img = neon_glow(img, draw_time, glow_radius=10, glow_strength=2)

    d = ImageDraw.Draw(img)
    d.text((35, 260), now.strftime("%A"), font=fonts["medium"], fill=MUT + (255,))
    d.text((35, 290), "LOCAL TIME", font=fonts["tiny"], fill=(120, 130, 150, 255))

    # Seconds progress bar (neon)
    bar_x0, bar_y0 = 26, 388
    bar_x1, bar_y1 = W - 26, 420
    pct = now.second / 60.0
    fill_w = int((bar_x1 - bar_x0) * pct)

    # outline
    d.rounded_rectangle((bar_x0, bar_y0, bar_x1, bar_y1), radius=10,
                        outline=(CYAN[0], CYAN[1], CYAN[2], 180), width=2, fill=(0, 0, 0, 60))

    # fill glow
    def draw_bar(glowdraw):
        glowdraw.rounded_rectangle((bar_x0 + 2, bar_y0 + 2, bar_x0 + 2 + max(0, fill_w - 4), bar_y1 - 2),
                                   radius=8, fill=(CYAN[0], CYAN[1], CYAN[2], 220))

    img = neon_glow(img, draw_bar, glow_radius=8, glow_strength=2)

    d = ImageDraw.Draw(img)
    d.text((26, 432), f"FPS LIMIT: {fps_limit} ", font=fonts["tiny"], fill=(120, 130, 150, 255))
    d.text((W - 26 - 66, 432), "PYAX206", font=fonts["tiny"], fill=(PURP[0], PURP[1], PURP[2], 255))

    # Scanlines
    img = add_scanlines(img, spacing=4, alpha=24)

    return img.convert("RGB")

def main():
    d = AX206Display(rotation=270, fps_limit=fps_limit).open()

    fonts = {
        "tiny": load_font(14),
        "small": load_font(18),
        "small_bold": load_font(18, bold=True),
        "medium": load_font(24),
        "time": load_font(86),
        "secs": load_font(44),
    }

    try:
        while True:
            now = datetime.now()
            frame = draw_clock_frame(now, fonts)

            fb = d.begin_draw(portrait=True)
            fb.paste(frame, (0, 0))
            d.end_draw()

            time.sleep(max(0.05, 1.0 - (time.time() % 1.0)))
    finally:
        d.close()

if __name__ == "__main__":
    main()

import time
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pyax206 import AX206Display
import psutil

# Optional NVIDIA VRAM stats
try:
    import pynvml
    pynvml.nvmlInit()
    _NVML_OK = True
except Exception:
    _NVML_OK = False


# ----------------- styling helpers -----------------

def load_font(size: int, bold=False):
    candidates = [
        "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()

def neon_layer(size, draw_fn, blur=8, strength=2):
    w, h = size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    draw_fn(d)
    glow = layer.filter(ImageFilter.GaussianBlur(blur))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for _ in range(strength):
        out = Image.alpha_composite(out, glow)
    out = Image.alpha_composite(out, layer)
    return out

def add_scanlines(img_rgba, spacing=4, alpha=22):
    w, h = img_rgba.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for y in range(0, h, spacing):
        d.line([(0, y), (w, y)], fill=(0, 0, 0, alpha), width=1)
    return Image.alpha_composite(img_rgba, overlay)

def rounded_panel(d: ImageDraw.ImageDraw, box, radius=16, fill=(0, 0, 0, 85),
                  outline=(0, 240, 255, 150), width=2):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def clamp(x, a, b):
    return a if x < a else b if x > b else x

def fmt_bytes(n: float) -> str:
    # bytes -> nice
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024.0
        i += 1
    if i == 0:
        return f"{int(v)}{units[i]}"
    if v >= 100:
        return f"{v:0.0f}{units[i]}"
    if v >= 10:
        return f"{v:0.1f}{units[i]}"
    return f"{v:0.2f}{units[i]}"

def fmt_rate(bytes_per_s: float) -> str:
    return f"{fmt_bytes(bytes_per_s)}/s"

def get_gpu_vram():
    """Return dict with used/free/total bytes if NVML available."""
    if not _NVML_OK:
        return None
    try:
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        mem = pynvml.nvmlDeviceGetMemoryInfo(h)
        return {
            "used": float(mem.used),
            "free": float(mem.free),
            "total": float(mem.total),
        }
    except Exception:
        return None


# ----------------- ring drawing -----------------

def draw_ring(d: ImageDraw.ImageDraw, bbox, pct, fg, width=14):
    """Circular progress ring (0..1)."""
    pct = clamp(pct, 0.0, 1.0)

    # Background ring
    bg = (60, 80, 95, 140)
    for i in range(width):
        d.arc([bbox[0]+i, bbox[1]+i, bbox[2]-i, bbox[3]-i], start=0, end=359, fill=bg)

    # Progress
    start = -90
    end = start + int(360 * pct)
    for i in range(width):
        d.arc([bbox[0]+i, bbox[1]+i, bbox[2]-i, bbox[3]-i], start=start, end=end, fill=fg)


# ----------------- UI frame -----------------

def draw_frame(now: datetime, stats: dict, fonts: dict) -> Image.Image:
    W, H = 320, 480

    CYAN = (0, 240, 255, 255)
    MAG  = (255, 50, 180, 255)
    PURP = (160, 80, 255, 255)
    TXT  = (240, 245, 255, 255)
    MUT  = (155, 170, 190, 255)

    # Background gradient
    base = Image.new("RGB", (W, H), (8, 10, 18))
    db = ImageDraw.Draw(base)
    for y in range(H):
        t = y / (H - 1)
        r = int(10 + 10*(1-t) + 4*t)
        g = int(12 + 4*(1-t) + 2*t)
        b = int(26 + 18*(1-t) + 26*t)
        db.line([(0, y), (W, y)], fill=(r, g, b))
    img = base.convert("RGBA")
    d = ImageDraw.Draw(img)

    # Panels: top header, middle clock zone, bottom stats zone
    rounded_panel(d, (14, 14, W-14, 90),  radius=18, fill=(0,0,0,90), outline=(CYAN[0],CYAN[1],CYAN[2],160))
    rounded_panel(d, (14, 104, W-14, 344), radius=26, fill=(0,0,0,78), outline=(MAG[0],MAG[1],MAG[2],140))
    rounded_panel(d, (14, 358, W-14, H-14), radius=18, fill=(0,0,0,75), outline=(PURP[0],PURP[1],PURP[2],140))

    # Header glow
    def _hdr(dd):
        cpu = stats["cpu_pct"]

        # CPU label
        dd.text((22, 26), f"CPU {cpu:0.0f}%", font=fonts["small_b"], fill=CYAN)

        # Date under it
        dd.text((22, 56), now.strftime("%a %d %b %Y"), font=fonts["small"], fill=MUT)

        # Network rates on right
        rx = stats["net_down"]
        tx = stats["net_up"]
        dd.text((W-22-95, 26), f"DL {fmt_rate(rx)}", font=fonts["tiny"],
                fill=(CYAN[0], CYAN[1], CYAN[2], 220))
        dd.text((W-22-95, 46), f"UL {fmt_rate(tx)}", font=fonts["tiny"],
                fill=(PURP[0], PURP[1], PURP[2], 220))


    img = Image.alpha_composite(img, neon_layer((W,H), _hdr, blur=6, strength=2))
    d = ImageDraw.Draw(img)

    # --- Big centered ring in the middle panel ---
    # Center it within middle box (14,104)-(306,344)
    cx, cy = W // 2, (104 + 344) // 2
    ring_radius = 110  # big ring
    ring_box = (cx - ring_radius, cy - ring_radius, cx + ring_radius, cy + ring_radius)

    sec = now.second
    pct = sec / 60.0

    # Ring glow
    def _ring(dd):
        draw_ring(dd, ring_box, pct, CYAN, width=16)

    img = Image.alpha_composite(img, neon_layer((W,H), _ring, blur=10, strength=2))
    d = ImageDraw.Draw(img)

    # Clock INSIDE ring (HH:MM) + seconds smaller
    hhmm = now.strftime("%H:%M")
    ss = now.strftime("%S")

    # measure to center text
    tw, th = d.textbbox((0,0), hhmm, font=fonts["time"])[2:]
    d.text((cx - tw//2, cy - th//2 - 10), hhmm, font=fonts["time"], fill=TXT)

    sw, sh = d.textbbox((0,0), ss, font=fonts["secs"])[2:]
    d.text((cx - sw//2, cy + th//2 - 10), ss, font=fonts["secs"], fill=MAG)


    # --- Bottom stats box ---
    ram_used = stats["ram_used"]
    ram_avail = stats["ram_avail"]
    ram_total = stats["ram_total"]

    gpu = stats.get("gpu_vram")

    # Left: RAM
    d.text((22, 372), "RAM", font=fonts["small_b"], fill=PURP)
    d.text((22, 400), f"Used: {fmt_bytes(ram_used)}", font=fonts["small"], fill=TXT)
    d.text((22, 426), f"Free: {fmt_bytes(ram_avail)}", font=fonts["small"], fill=TXT)

    # Right: GPU VRAM
    d.text((170, 372), "GPU VRAM", font=fonts["small_b"], fill=CYAN)
    if gpu is None:
        d.text((170, 400), "n/a", font=fonts["small"], fill=MUT)
    else:
        d.text((170, 400), f"Used: {fmt_bytes(gpu['used'])}", font=fonts["small"], fill=TXT)
        d.text((170, 426), f"Free: {fmt_bytes(gpu['free'])}", font=fonts["small"], fill=TXT)

    # Scanlines
    img = add_scanlines(img, spacing=4, alpha=22)
    return img.convert("RGB")


# ----------------- app loop -----------------

def main():
    # 1 FPS keeps it stable
    d = AX206Display(rotation=270, fps_limit=1).open()

    fonts = {
        "tiny":    load_font(14),
        "small":   load_font(18),
        "small_b": load_font(18, bold=True),
        "time":    load_font(64, bold=True),
        "secs":    load_font(34, bold=True),
    }

    # Network baseline
    prev = psutil.net_io_counters()
    prev_t = time.time()

    try:
        while True:
            now = datetime.now()

            # RAM
            vm = psutil.virtual_memory()
            ram_total = float(vm.total)
            ram_avail = float(vm.available)
            ram_used = ram_total - ram_avail

            # Network rates
            cur = psutil.net_io_counters()
            cur_t = time.time()
            dt = max(0.001, cur_t - prev_t)
            net_down = (cur.bytes_recv - prev.bytes_recv) / dt
            net_up   = (cur.bytes_sent - prev.bytes_sent) / dt
            prev, prev_t = cur, cur_t
            
            cpu_pct = psutil.cpu_percent(interval=None)


            stats = {
                "cpu_pct": cpu_pct,
                "ram_total": ram_total,
                "ram_avail": ram_avail,
                "ram_used": ram_used,
                "net_down": net_down,
                "net_up": net_up,
                "gpu_vram": get_gpu_vram(),
            }


            frame = draw_frame(now, stats, fonts)

            fb = d.begin_draw(portrait=True)
            fb.paste(frame, (0, 0))
            d.end_draw()

            time.sleep(max(0.05, 1.0 - (time.time() % 1.0)))
    finally:
        d.close()

if __name__ == "__main__":
    main()

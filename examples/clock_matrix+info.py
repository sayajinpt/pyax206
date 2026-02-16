import time
import random
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
from pyax206 import AX206Display
import psutil

# Optional NVIDIA VRAM stats
try:
    import pynvml
    pynvml.nvmlInit()
    _NVML_OK = True
except Exception:
    _NVML_OK = False


# ----------------- helpers -----------------

def load_font(size: int, bold=False):
    # Prefer monospace for Matrix vibe
    candidates = [
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/lucon.ttf",
        "C:/Windows/Fonts/cour.ttf",
        "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()

def clamp(x, a, b):
    return a if x < a else b if x > b else x

def fmt_bytes(n: float) -> str:
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
    if not _NVML_OK:
        return None
    try:
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        mem = pynvml.nvmlDeviceGetMemoryInfo(h)
        return {"used": float(mem.used), "free": float(mem.free), "total": float(mem.total)}
    except Exception:
        return None


# ----------------- matrix background -----------------

MATRIX_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ#$%*+-=<>?/\\|"

def init_rain(width, height, step=12):
    cols = list(range(0, width, step))
    drops = []
    for x in cols:
        drops.append({
            "x": x,
            "y": random.randint(-height, 0),
            "speed": random.randint(8, 18),     # pixels per frame
            "len": random.randint(8, 18),       # chars in a column
        })
    return drops

def draw_matrix_rain(d: ImageDraw.ImageDraw, W, H, drops, *,
                     step=12,
                     bright=(0, 255, 70, 170),
                     dim=(0, 120, 40, 120),
                     faint=(0, 50, 18, 80),
                     font=None):
    if font is None:
        font = ImageFont.load_default()

    # Subtle vertical grid
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=(0, 35, 0, 70))

    # Rain columns
    for drop in drops:
        x = drop["x"]
        y = drop["y"]
        L = drop["len"]

        # tail → head
        for i in range(L):
            ch = random.choice(MATRIX_CHARS)
            yy = y - i * step
            if yy < -step or yy > H + step:
                continue

            # head brighter, tail dimmer
            if i == 0:
                col = bright
            elif i < 4:
                col = dim
            else:
                col = faint

            d.text((x, yy), ch, font=font, fill=col)

        # advance
        drop["y"] += drop["speed"]
        if drop["y"] - L * step > H + 30:
            drop["y"] = random.randint(-H, -30)
            drop["speed"] = random.randint(8, 18)
            drop["len"] = random.randint(8, 18)


# ----------------- ring drawing -----------------

def draw_ring(d: ImageDraw.ImageDraw, bbox, pct, *, width=14,
              fg=(0, 255, 70, 230), bg=(0, 70, 25, 160)):
    pct = clamp(pct, 0.0, 1.0)

    # background ring
    for i in range(width):
        d.arc([bbox[0]+i, bbox[1]+i, bbox[2]-i, bbox[3]-i], start=0, end=359, fill=bg)

    # progress (start at top)
    start = -90
    end = start + int(360 * pct)
    for i in range(width):
        d.arc([bbox[0]+i, bbox[1]+i, bbox[2]-i, bbox[3]-i], start=start, end=end, fill=fg)


# ----------------- UI frame -----------------

def draw_frame(now: datetime, stats: dict, fonts: dict, drops) -> Image.Image:
    W, H = 320, 480

    GREEN = (0, 255, 70, 255)
    DIM   = (0, 150, 50, 255)
    DARK  = (0, 60, 20, 255)
    FAINT = (0, 90, 30, 255)

    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)

    # Background: Matrix rain
    draw_matrix_rain(d, W, H, drops, step=12, font=fonts["matrix"])

    # Terminal borders
    d.rectangle((6, 6, W-6, H-6), outline=DARK, width=2)
    d.rectangle((12, 12, W-12, 92), outline=DARK, width=1)      # header band
    d.rectangle((12, 102, W-12, 350), outline=DARK, width=1)    # ring band
    d.rectangle((12, 360, W-12, H-12), outline=DARK, width=1)   # stats band

    # Header content
    cpu = stats["cpu_pct"]
    rx = stats["net_down"]
    tx = stats["net_up"]

    d.text((18, 28), f"[ CPU ] {cpu:0.0f}%", font=fonts["small_b"], fill=GREEN)
    d.text((18, 58), now.strftime("%a %d %b %Y"), font=fonts["small"], fill=DIM)

    d.text((W-110, 18), f"DL {fmt_rate(rx)}", font=fonts["tiny"], fill=GREEN)
    d.text((W-110, 42), f"UL {fmt_rate(tx)}", font=fonts["tiny"], fill=GREEN)

    # Middle: ring + clock inside
    cx, cy = W // 2, (102 + 350) // 2
    ring_radius = 118
    ring_box = (cx - ring_radius, cy - ring_radius, cx + ring_radius, cy + ring_radius)

    sec = now.second
    pct = sec / 60.0
    draw_ring(d, ring_box, pct, width=14, fg=(0, 255, 70, 235), bg=(0, 70, 25, 170))

    hhmm = now.strftime("%H:%M")
    ss = now.strftime("%S")

    # center HH:MM
    tw = d.textbbox((0, 0), hhmm, font=fonts["time"])[2]
    th = d.textbbox((0, 0), hhmm, font=fonts["time"])[3]
    d.text((cx - tw // 2, cy - th // 2 - 8), hhmm, font=fonts["time"], fill=GREEN)

    # center seconds under
    sw = d.textbbox((0, 0), ss, font=fonts["secs"])[2]
    sh = d.textbbox((0, 0), ss, font=fonts["secs"])[3]
    d.text((cx - sw // 2, cy + th // 2 - 6), ss, font=fonts["secs"], fill=DIM)

    # Bottom stats
    ram_used = stats["ram_used"]
    ram_avail = stats["ram_avail"]
    gpu = stats.get("gpu_vram")

    d.text((18, 368), "[ RAM ]", font=fonts["small_b"], fill=GREEN)
    d.text((18, 396), f"USED {fmt_bytes(ram_used)}", font=fonts["small"], fill=GREEN)
    d.text((18, 422), f"FREE {fmt_bytes(ram_avail)}", font=fonts["small"], fill=GREEN)

    d.text((170, 368), "[ GPU VRAM ]", font=fonts["small_b"], fill=GREEN)
    if gpu is None:
        d.text((170, 396), "N/A", font=fonts["small"], fill=DIM)
        d.text((170, 422), "N/A", font=fonts["small"], fill=DIM)
    else:
        d.text((170, 396), f"USED {fmt_bytes(gpu['used'])}", font=fonts["small"], fill=GREEN)
        d.text((170, 422), f"FREE {fmt_bytes(gpu['free'])}", font=fonts["small"], fill=GREEN)

    # Occasional CRT-ish flicker line
    if random.random() < 0.25:
        y = random.randint(8, H-8)
        d.line([(8, y), (W-8, y)], fill=(0, 255, 70, 70), width=1)

    return img.convert("RGB")


# ----------------- app loop -----------------

def main():
    d = AX206Display(rotation=270, fps_limit=1).open()

    fonts = {
        "tiny":    load_font(14),
        "small":   load_font(18),
        "small_b": load_font(18, bold=True),
        "time":    load_font(66, bold=True),
        "secs":    load_font(34, bold=True),
        "matrix":  load_font(14),   # rain characters
    }

    # Warm up CPU percent
    psutil.cpu_percent(interval=None)

    # Network baseline
    prev = psutil.net_io_counters()
    prev_t = time.time()

    drops = init_rain(320, 480, step=12)

    try:
        while True:
            now = datetime.now()

            # RAM
            vm = psutil.virtual_memory()
            ram_total = float(vm.total)
            ram_avail = float(vm.available)
            ram_used = ram_total - ram_avail

            # CPU
            cpu_pct = psutil.cpu_percent(interval=None)

            # Network rates
            cur = psutil.net_io_counters()
            cur_t = time.time()
            dt = max(0.001, cur_t - prev_t)
            net_down = (cur.bytes_recv - prev.bytes_recv) / dt
            net_up   = (cur.bytes_sent - prev.bytes_sent) / dt
            prev, prev_t = cur, cur_t

            stats = {
                "cpu_pct": cpu_pct,
                "ram_total": ram_total,
                "ram_avail": ram_avail,
                "ram_used": ram_used,
                "net_down": net_down,
                "net_up": net_up,
                "gpu_vram": get_gpu_vram(),
            }

            frame = draw_frame(now, stats, fonts, drops)

            fb = d.begin_draw(portrait=True)
            fb.paste(frame, (0, 0))
            d.end_draw()

            time.sleep(max(0.05, 1.0 - (time.time() % 1.0)))
    finally:
        d.close()

if __name__ == "__main__":
    main()

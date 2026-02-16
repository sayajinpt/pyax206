from __future__ import annotations
import argparse
from .display import AX206Display

def main(argv=None):
    p = argparse.ArgumentParser(prog="pyax206", description="AX206 USB LCD utility")
    sub = p.add_subparsers(dest="cmd", required=True)

    s_img = sub.add_parser("image", help="Show an image")
    s_img.add_argument("path")
    s_img.add_argument("--rotation", type=int, default=270)
    s_img.add_argument("--scaling", choices=["letterbox","crop","stretch"], default="letterbox")

    s_mirror = sub.add_parser("mirror", help="Mirror Windows monitor (slow preview)")
    s_mirror.add_argument("--monitor", type=int, default=1)
    s_mirror.add_argument("--fps", type=float, default=3.0)
    s_mirror.add_argument("--no-fps", action="store_true")
    s_mirror.add_argument("--alpha", type=float, default=0.35)

    s_vid = sub.add_parser("video", help="Play a video (downscaled)")
    s_vid.add_argument("path")
    s_vid.add_argument("--fps", type=float, default=3.0)

    s_proc = sub.add_parser("proc", help="Attach to a process and show its output")
    s_proc.add_argument("cmdline", nargs=argparse.REMAINDER)
    s_proc.add_argument("--fps", type=float, default=2.0)

    args = p.parse_args(argv)

    d = AX206Display(rotation=getattr(args, "rotation", 270), scaling=getattr(args, "scaling", "letterbox")).open()
    try:
        if args.cmd == "image":
            d.set_rotation(args.rotation)
            d.set_scaling(args.scaling)
            d.show_image(args.path)
        elif args.cmd == "mirror":
            d.mirror_windows(monitor=args.monitor, fps=args.fps, show_fps=not args.no_fps, overlay_alpha=args.alpha)
        elif args.cmd == "video":
            d.play_video(args.path, fps=args.fps)
        elif args.cmd == "proc":
            cmd = args.cmdline
            if cmd and cmd[0] == "--":
                cmd = cmd[1:]
            if not cmd:
                raise SystemExit("Provide command after 'proc', e.g. pyax206 proc -- minerd.exe ...")
            d.attach_process(cmd, fps=args.fps, title=" ".join(cmd[:2]))
    finally:
        d.close()

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

@dataclass
class FrameBuffer:
    width: int
    height: int
    background: Tuple[int, int, int] = (0, 0, 0)

    def __post_init__(self):
        self.image = Image.new("RGB", (self.width, self.height), self.background)
        self.draw = ImageDraw.Draw(self.image)

    def clear(self, color: Tuple[int, int, int] | None = None) -> None:
        color = self.background if color is None else color
        self.draw.rectangle([0, 0, self.width, self.height], fill=color)

    def text(self, xy: Tuple[int, int], text: str, fill=(255,255,255), font=None) -> None:
        if font is None:
            font = ImageFont.load_default()
        self.draw.text(xy, text, fill=fill, font=font)

    def rectangle(self, xy, fill=None, outline=None, width=1):
        self.draw.rectangle(xy, fill=fill, outline=outline, width=width)

    def line(self, xy, fill=(255,255,255), width=1):
        self.draw.line(xy, fill=fill, width=width)

    def paste(self, img: Image.Image, xy=(0,0)):
        self.image.paste(img, xy)

    def get_image(self) -> Image.Image:
        return self.image

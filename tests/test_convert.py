from PIL import Image
from pyax206.convert import FrameSpec, pil_to_rgb565_be_bytes

def test_rgb565_length():
    spec = FrameSpec(width=480, height=320, rotation=0, scaling="letterbox")
    img = Image.new("RGB", (480,320), (255,0,0))
    b = pil_to_rgb565_be_bytes(img, spec)
    assert len(b) == 480*320*2

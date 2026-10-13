"""Build code-drawn PWA icons; Pillow is needed only to regenerate the assets."""

from pathlib import Path
from PIL import Image, ImageDraw


def build():
    destination = Path(__file__).resolve().parent / "static"
    image = Image.new("RGB", (768, 768), "#145dc5")
    draw = ImageDraw.Draw(image)
    # Same cloud/rain geometry as icon.svg, at 4x its 192-unit canvas.
    draw.ellipse((84, 232, 300, 448), fill="white")
    draw.ellipse((176, 104, 496, 424), fill="white")
    draw.ellipse((444, 192, 700, 448), fill="white")
    draw.rectangle((192, 296, 572, 448), fill="white")
    for x in (256, 376, 496):
        draw.line((x, 528, x-32, 596), fill="white", width=40)
        for cx, cy in ((x, 528), (x-32, 596)):
            draw.ellipse((cx-20, cy-20, cx+20, cy+20), fill="white")
    for size in (180, 192, 512):
        image.resize((size, size), Image.Resampling.LANCZOS).save(destination / f"icon-{size}.png")


if __name__ == "__main__":
    build()

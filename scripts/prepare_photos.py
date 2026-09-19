"""Resize the boat photos for the web and strip all metadata (including GPS).

Usage (from the repo root):
    python scripts/prepare_photos.py "G:\\My Drive\\Reel Sound\\Website Media\\boat"
Writes images/<name>.jpg in the current directory.
"""
import glob
import os
import sys

from PIL import Image, ImageOps

MAP = {
    "_0008_": "hero",
    "_0020_": "boat-above",
    "_0010_": "boat-side",
    "184436313": "boat-aft",
}

src = sys.argv[1]
os.makedirs("images", exist_ok=True)
for path in sorted(glob.glob(os.path.join(src, "*"))):
    base = os.path.basename(path)
    for key, name in MAP.items():
        if key in base:
            im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
            im.thumbnail((2000, 2000))
            clean = Image.new("RGB", im.size)  # new image carries no EXIF/GPS
            clean.paste(im)
            clean.save(f"images/{name}.jpg", "JPEG", quality=82, optimize=True, progressive=True)
            print(name, clean.size, "from", base)

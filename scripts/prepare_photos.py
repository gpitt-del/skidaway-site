"""Build the site's images/ folder: resize for the web and strip all metadata (including GPS).

Usage (from the repo root):
    python scripts/prepare_photos.py "<boat photos folder>" "<skidaway-media web/final folder>"

Example:
    python scripts/prepare_photos.py "G:\\My Drive\\Reel Sound\\Website Media\\boat" "..\\skidaway-media\\web\\final"

Writes eight files into images/ in the current directory and exits with an
error if any of them could not be produced.
"""
import glob
import os
import sys

from PIL import Image, ImageOps

# Boat originals are matched by a fragment of the camera file name.
BOAT = {
    "_0008_": "hero",
    "_0020_": "boat-above",
    "_0010_": "boat-side",
    "184436313": "boat-aft",
}

# Finished shots from skidaway-media/web/final are matched by exact file name.
FINAL = {
    "card-dolphins.jpg": "moon-river",
    "hero-sunset.jpg": "moon-river-hero",
    "hero-home.jpg": "sunset-hero",
    "gallery-boat-bow.jpg": "boat-bow",
}


def save(path, name):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    im.thumbnail((2000, 2000))
    clean = Image.new("RGB", im.size)  # a new image carries no EXIF or GPS
    clean.paste(im)
    out = os.path.join("images", name + ".jpg")
    clean.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    print(f"{name}.jpg  {clean.size[0]}x{clean.size[1]}  {os.path.getsize(out) // 1024} KB  from {os.path.basename(path)}")


if len(sys.argv) != 3:
    sys.exit(__doc__)

boat_dir, final_dir = sys.argv[1], sys.argv[2]
os.makedirs("images", exist_ok=True)
made = set()

for path in sorted(glob.glob(os.path.join(boat_dir, "*"))):
    base = os.path.basename(path)
    for key, name in BOAT.items():
        if key in base and name not in made:
            save(path, name)
            made.add(name)

for src, name in FINAL.items():
    path = os.path.join(final_dir, src)
    if os.path.exists(path):
        save(path, name)
        made.add(name)

missing = sorted((set(BOAT.values()) | set(FINAL.values())) - made)
if missing:
    sys.exit("MISSING: " + ", ".join(missing))

for name in sorted(made):
    exif = Image.open(os.path.join("images", name + ".jpg")).getexif()
    if len(exif):
        sys.exit(f"{name}.jpg still carries metadata")
print("All 8 images written, no metadata.")

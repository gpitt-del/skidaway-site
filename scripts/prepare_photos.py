"""Build the site's images/ folder. Resizes for the web and strips all metadata (including GPS).

Run from the skidaway-site repo root:

    python scripts/prepare_photos.py "<boat photos folder>" "<skidaway-media web/final folder>"

It reads eight named source files, writes eight named files into images/, then
checks its own work. It never modifies or deletes a source file. Any problem
ends the run with a line starting "FAILED:". On success the last line is:

    OK: 8 images written, no metadata, all page references resolve.
"""
import glob
import os
import re
import sys

from PIL import Image, ImageOps

MAX_BYTES = 900 * 1024

# Exact source file name -> output name. Nothing else in either folder is read.
BOAT = {
    "DJI_20260913134625_0008_D.JPG": "hero",
    "DJI_20260913141728_0020_D.JPG": "boat-above",
    "DJI_20260913134735_0010_D.JPG": "boat-side",
    "PXL_20260913_184436313.jpg": "boat-aft",
}
FINAL = {
    "card-dolphins.jpg": "moon-river",
    "hero-sunset.jpg": "moon-river-hero",
    "hero-home.jpg": "sunset-hero",
    "gallery-boat-bow.jpg": "boat-bow",
}


def fail(msg):
    sys.exit("FAILED: " + msg)


def save(path, name):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    im.thumbnail((2000, 2000))
    clean = Image.new("RGB", im.size)  # a new image carries no EXIF or GPS
    clean.paste(im)
    out = os.path.join("images", name + ".jpg")
    for quality in (82, 76, 70, 64):
        clean.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
        if os.path.getsize(out) <= MAX_BYTES:
            break
    else:
        fail(f"{name}.jpg is still over {MAX_BYTES // 1024} KB at quality 64")
    print(f"{name}.jpg  {clean.size[0]}x{clean.size[1]}  {os.path.getsize(out) // 1024} KB  q{quality}  from {os.path.basename(path)}")


if len(sys.argv) != 3:
    sys.exit(__doc__)
if not os.path.exists("index.html") or not os.path.exists("CNAME"):
    fail("run this from the skidaway-site repo root")

boat_dir, final_dir = sys.argv[1], sys.argv[2]
jobs = [(os.path.join(boat_dir, src), name) for src, name in BOAT.items()]
jobs += [(os.path.join(final_dir, src), name) for src, name in FINAL.items()]

missing = [path for path, _ in jobs if not os.path.isfile(path)]
if missing:
    fail("source files not found:\n  " + "\n  ".join(missing))

os.makedirs("images", exist_ok=True)
for path, name in jobs:
    save(path, name)

expected = sorted(name + ".jpg" for _, name in jobs)
present = sorted(os.listdir("images"))
if present != expected:
    fail(f"images/ should hold exactly {expected} but holds {present}")

for name in expected:
    if len(Image.open(os.path.join("images", name)).getexif()):
        fail(f"{name} still carries metadata")

referenced = set()
for page in glob.glob("*.html"):
    with open(page, encoding="utf-8") as fh:
        referenced |= set(re.findall(r"/images/([A-Za-z0-9_-]+\.(?:jpg|png|webp))", fh.read()))
unresolved = sorted(referenced - set(expected))
unused = sorted(set(expected) - referenced)
if unresolved:
    fail(f"pages reference images that do not exist: {unresolved}")
if unused:
    fail(f"images no page uses: {unused}")

print("OK: 8 images written, no metadata, all page references resolve.")

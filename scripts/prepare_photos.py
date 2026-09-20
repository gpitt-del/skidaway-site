"""Build the site's images/ folder. Resizes for the web and strips all metadata (including GPS).

Run from the skidaway-site repo root:

    python scripts/prepare_photos.py "<boat photos folder>" "<skidaway-media web/final folder>"

Add --only=<name> (for example --only=moon-river) to rewrite a single image and
leave the other seven files untouched.

It reads eight named source files, writes eight named files into images/, then
checks its own work. It never modifies or deletes a source file. Any problem
ends the run with a line starting "FAILED:". On success the last line is:

    OK: 8 images present, no metadata, all page references resolve.
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
    "gallery-dolphin-profile.jpg": "moon-river",
    "hero-sunset.jpg": "moon-river-hero",
    "hero-home.jpg": "sunset-hero",
    "gallery-boat-bow.jpg": "boat-bow",
}

# Fixed crops: output name -> (required source size, crop box left/top/right/bottom).
# The dolphin frame is a tall phone video still; the site shows it in a wide card.
CROP = {
    "moon-river": ((900, 1600), (0, 470, 900, 1130)),
}


def fail(msg):
    sys.exit("FAILED: " + msg)


def save(path, name):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if name in CROP:
        size, box = CROP[name]
        if im.size != size:
            fail(f"{os.path.basename(path)} is {im.size}, expected {size}; crop not applied")
        im = im.crop(box)
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


paths = [a for a in sys.argv[1:] if not a.startswith("--")]
flags = [a for a in sys.argv[1:] if a.startswith("--")]
if len(paths) != 2 or any(not f.startswith("--only=") for f in flags):
    sys.exit(__doc__)
if not os.path.exists("index.html") or not os.path.exists("CNAME"):
    fail("run this from the skidaway-site repo root")

boat_dir, final_dir = paths
jobs = [(os.path.join(boat_dir, src), name) for src, name in BOAT.items()]
jobs += [(os.path.join(final_dir, src), name) for src, name in FINAL.items()]
names = [name for _, name in jobs]

only = [f.split("=", 1)[1] for f in flags]
unknown = [n for n in only if n not in names]
if unknown:
    fail(f"--only names not recognised: {unknown}")
todo = [(path, name) for path, name in jobs if not only or name in only]

missing = [path for path, _ in todo if not os.path.isfile(path)]
if missing:
    fail("source files not found:\n  " + "\n  ".join(missing))

os.makedirs("images", exist_ok=True)
for path, name in todo:
    save(path, name)

expected = sorted(name + ".jpg" for name in names)
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

print("OK: 8 images present, no metadata, all page references resolve.")

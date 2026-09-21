"""Build the Moon River page's dolphin loop and its poster frame from the Sept 20, 2026 phone video.

Run from the skidaway-site repo root:

    python scripts/prepare_video.py "<Reel Sound Images folder>"

Reads one named video and never modifies it. Writes exactly three files:

    video/moon-river-dolphins.mp4   silent loop, 1280 px wide, all metadata (including GPS) stripped
    images/moon-river-hero.jpg      poster: the loop's first frame, metadata stripped
    review/clip-check.jpg           two frames per second of the finished loop, for Claude to check
                                    the crop. Claude deletes this before anything goes live.

Any problem ends the run with a line starting "FAILED:". On success the last line starts "OK:".
Needs ffmpeg and ffprobe (PATH, or the winget install location).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

SOURCE = "PXL_20260920_175724000.mp4"
START, LENGTH = 34.0, 7.5            # seconds: dolphins surface repeatedly from 0:34 to 0:41
CROP = "crop=iw*0.65:ih*0.65:iw*0.05:0"  # zoom toward the upper left, where the dolphins and marsh are
OUT_W = 1280
MAX_CLIP_BYTES = int(2.5 * 1024 * 1024)
MAX_POSTER_BYTES = 400 * 1024
HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}
# Phone HDR (HLG or PQ) to ordinary SDR. Without this the picture comes out grey and washed.
TONEMAP = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
           "tonemap=tonemap=mobius:desat=0,zscale=t=bt709:m=bt709:r=tv")


def fail(msg: str) -> None:
    sys.exit("FAILED: " + msg)


def find_tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    pkgs = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
    if pkgs.is_dir():
        for cand in sorted(pkgs.glob(f"Gyan.FFmpeg*/**/bin/{name}.exe"), reverse=True):
            return str(cand)
    fail(f"{name} not found")


def probe(ffprobe: str, path: Path) -> dict:
    out = subprocess.run(
        [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, check=True, timeout=600,
    ).stdout
    return json.loads(out)


def load_font(size: int):
    for path in ("C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    if not os.path.exists("index.html") or not os.path.exists("CNAME"):
        fail("run this from the skidaway-site repo root")
    src = Path(sys.argv[1]) / SOURCE
    if not src.is_file():
        fail(f"source video not found: {src}")
    ffmpeg, ffprobe = find_tool("ffmpeg"), find_tool("ffprobe")

    info = probe(ffprobe, src)
    v = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    if v is None:
        fail("no video stream in the source")
    duration = float(info["format"]["duration"])
    hdr = v.get("color_transfer") in HDR_TRANSFERS
    print(f"source  {v.get('codec_name')} {v.get('width')}x{v.get('height')} {v.get('pix_fmt')} "
          f"transfer={v.get('color_transfer', 'unset')} {duration:.1f}s"
          + ("  (HDR: tone-mapping to SDR)" if hdr else ""))
    if hdr:
        listed = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True,
                                check=True, timeout=120).stdout
        missing = [f for f in ("zscale", "tonemap") if f" {f} " not in listed]
        if missing:
            fail(f"the source is HDR and this ffmpeg build lacks the filters needed to convert it: {missing}")
    if duration < START + LENGTH:
        fail(f"the source is only {duration:.1f}s long")

    for folder in ("video", "images", "review"):
        os.makedirs(folder, exist_ok=True)
    clip = Path("video/moon-river-dolphins.mp4")
    poster = Path("images/moon-river-hero.jpg")
    check = Path("review/clip-check.jpg")

    # The loop. -an drops audio; -map_metadata -1 drops every tag, including the phone's GPS location.
    for crf in (25, 28, 31):
        subprocess.run(
            [ffmpeg, "-y", "-v", "error", "-ss", str(START), "-t", str(LENGTH), "-i", str(src),
             "-an", "-vf", f"{CROP},scale={OUT_W}:-2" + (f",{TONEMAP}" if hdr else "") + ",format=yuv420p",
             "-r", "30", "-c:v", "libx264", "-profile:v", "main", "-pix_fmt", "yuv420p",
             "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
             "-crf", str(crf), "-preset", "slow", "-movflags", "+faststart",
             "-map_metadata", "-1", "-map_chapters", "-1", str(clip)],
            check=True, timeout=3600,
        )
        if clip.stat().st_size <= MAX_CLIP_BYTES:
            break
    else:
        fail(f"the loop is still over {MAX_CLIP_BYTES // 1024} KB at crf 31")

    out = probe(ffprobe, clip)
    ov = next(s for s in out["streams"] if s.get("codec_type") == "video")
    if any(s.get("codec_type") == "audio" for s in out["streams"]):
        fail("the loop still has an audio track")
    tags = {k.lower(): val for k, val in out["format"].get("tags", {}).items()}
    leaked = [k for k in tags if "location" in k or "gps" in k or k in {"make", "model", "creation_time"}]
    if leaked:
        fail(f"the loop still carries metadata: {leaked}")
    print(f"moon-river-dolphins.mp4  {ov['width']}x{ov['height']}  {float(out['format']['duration']):.1f}s  "
          f"{clip.stat().st_size // 1024} KB  crf{crf}")

    # Poster (first frame of the loop) and the check sheet (2 frames per second of the loop).
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [ffmpeg, "-y", "-v", "error", "-i", str(clip), "-vf", "fps=2", "-q:v", "3",
             "-start_number", "0", str(Path(tmp) / "c-%03d.jpg")],
            check=True, timeout=600,
        )
        frames = sorted(Path(tmp).glob("c-*.jpg"))
        if len(frames) < 10:
            fail(f"expected about 15 check frames, got {len(frames)}")

        with Image.open(frames[0]) as im:
            first = im.convert("RGB")
        clean = Image.new("RGB", first.size)
        clean.paste(first)
        for quality in (85, 78, 70):
            clean.save(poster, "JPEG", quality=quality, optimize=True, progressive=True)
            if poster.stat().st_size <= MAX_POSTER_BYTES:
                break
        else:
            fail("the poster is still too large at quality 70")
        if len(Image.open(poster).getexif()):
            fail("the poster still carries metadata")
        print(f"moon-river-hero.jpg  {clean.size[0]}x{clean.size[1]}  {poster.stat().st_size // 1024} KB  q{quality}")

        cols, tw, th, lh, gut = 5, 448, 252, 40, 24
        rows = -(-len(frames) // cols)
        sheet = Image.new("RGB", (cols * tw + (cols + 1) * gut, rows * (th + lh) + (rows + 1) * gut), (128, 128, 128))
        draw, font = ImageDraw.Draw(sheet), load_font(28)
        for i, f in enumerate(frames):
            with Image.open(f) as im:
                thumb = ImageOps.contain(im.convert("RGB"), (tw, th), Image.Resampling.LANCZOS)
            x0 = gut + (i % cols) * (tw + gut)
            y0 = gut + (i // cols) * (th + lh + gut)
            sheet.paste(thumb, (x0, y0))
            draw.rectangle([x0, y0 + th, x0 + tw - 1, y0 + th + lh - 1], fill=(0, 0, 0))
            draw.text((x0 + tw / 2, y0 + th + lh / 2), f"{i / 2:.1f}s", font=font, fill=(255, 255, 255), anchor="mm")
        sheet.save(check, "JPEG", quality=80, optimize=True)
    print(f"clip-check.jpg  {len(frames)} frames  {check.stat().st_size // 1024} KB")
    print("OK: loop, poster and check sheet written.")


if __name__ == "__main__":
    main()

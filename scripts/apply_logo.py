import sys, glob, pathlib
from PIL import Image
SRC = r"C:\Users\gabep\projects\skidaway-media\Images\skidaway-logo-files"
img = pathlib.Path("images")
def prep(name, out, w):
    im = Image.open(f"{SRC}/{name}").convert("RGBA")
    im = im.resize((w, round(im.height*w/im.width)), Image.LANCZOS)
    im.save(img/out, optimize=True); return im.size
hw, hh = prep("header-lockup_3000px_cream.png", "logo-header.png", 1200)
prep("header-lockup_3000px_green.png", "logo-header-green.png", 1200)
Image.open(f"{SRC}/site-icon_512px.png").convert("RGBA").save(img/"icon.png", optimize=True)
def sub(text, old, new, n, path, atleast=False):
    c = text.count(old)
    ok = (c >= n) if atleast else (c == n)
    if not ok: sys.exit(f"FAILED: {path}: expected {'>=' if atleast else ''}{n} of {old[:60]!r}, found {c}")
    return text.replace(old, new)
ICON = '<link rel="icon" href="/images/icon.png" type="image/png">'
def brand(src): return f'<a class="brand" href="/"><img src="/images/{src}" alt="Skidaway Charters" width="{hw}" height="{hh}"></a>'
for p in ["index.html","moon-river-cruise.html","sunset-cruise.html","the-boat.html","faq.html"]:
    f = pathlib.Path(p); t = f.read_text(encoding="utf-8")
    t = sub(t, '<a class="brand" href="/">Skidaway Charters</a>', brand("logo-header.png"), 1, p)
    t = sub(t, '<link rel="stylesheet" href="/css/site.css">', ICON+'\n<link rel="stylesheet" href="/css/site.css">', 1, p)
    t = sub(t, '© 2026 Reel Sound LLC, doing business as Skidaway Charters. Savannah, GA 31411.', '© 2026 Skidaway Charters · Savannah, GA', 1, p)
    if p == "index.html":
        t = sub(t, 'Skidaway Charters | Private Boat Charters and Moon River Cruises, Savannah GA', 'Skidaway Charters | Private Boat Charters from Delegal Creek, Savannah GA', 2, p)
        t = sub(t, 'Private boat charters from Skidaway Island, Savannah. The Moon River Cruise', 'Private boat charters from Delegal Creek Marina on Skidaway Island, Savannah. The Moon River Cruise', 2, p)
        t = sub(t, '"description":"Private boat charters from Skidaway Island, Savannah, Georgia."', '"description":"Private boat charters from Delegal Creek Marina on Skidaway Island, Savannah, Georgia."', 1, p)
    if p == "the-boat.html":
        t = sub(t, '<div class="eyebrow">The boat</div>', '<div class="eyebrow">The boat · Delegal Creek Marina</div>', 1, p)
    f.write_text(t, encoding="utf-8")
# privacy.html: standalone page with inline styles and a light header
p = "privacy.html"; f = pathlib.Path(p); t = f.read_text(encoding="utf-8")
t = sub(t, '<a class="brand" href="/">Skidaway Charters</a>', brand("logo-header-green.png"), 1, p)
t = sub(t, '</head>', ICON+'\n</head>', 1, p)
t = sub(t, '</style>', '.brand img{display:block;height:40px;width:auto}\n</style>', 1, p)
t = sub(t, 'Reel Sound LLC dba Skidaway Charters', 'Skidaway Charters', 1, p, atleast=True)
f.write_text(t, encoding="utf-8")
css = pathlib.Path("css/site.css"); c = css.read_text(encoding="utf-8")
c = sub(c, '.brand{font:500 24px Fraunces,Georgia,serif;color:var(--cream);text-decoration:none}', '.brand{display:block;text-decoration:none}\n.brand img{display:block;height:44px;width:auto}', 1, "css/site.css")
css.write_text(c, encoding="utf-8")
for x in ("images/logo-header.png","images/logo-header-green.png","images/icon.png"):
    if Image.open(x).info: sys.exit(f"FAILED: {x} still has metadata")
print("OK: logo applied.")

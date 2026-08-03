#!/usr/bin/env python3
"""Render one WebP per place into docs/images/ from the cached source photographs.

The single-file build inlines images as base64 and has to stay under a size cap;
the published site does not, so these are rendered large enough to look right in
the full-screen detail view (default 680 px wide).

    python3 src/render_images.py               # default size/quality
    python3 src/render_images.py --width 900 --quality 78
"""
import argparse, io, json, os, re, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import ENRICHED, CACHE, IMGDIR

ap = argparse.ArgumentParser()
ap.add_argument("--width", type=int, default=680)
ap.add_argument("--quality", type=int, default=72)
ap.add_argument("--force", action="store_true", help="re-render images that already exist")
a = ap.parse_args()

TH = int(round(a.width * 2.05 / 3))          # the card's aspect ratio

def cached(url):
    if not url: return None
    key = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]", "_", url)[-180:])
    return open(key, "rb").read() if os.path.isfile(key) else None

places = json.load(open(ENRICHED, encoding="utf-8"))
made = skipped = missing = 0
for p in places:
    dest = os.path.join(IMGDIR, p["id"] + ".webp")
    if os.path.exists(dest) and not a.force:
        skipped += 1; continue
    raw = cached(p.get("thumb") or "")
    if not raw:
        missing += 1; continue
    try:
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        w, h = im.size
        s = max(a.width / w, TH / h)
        if s < 1:
            im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
        w, h = im.size
        if w > a.width or h > TH:                       # centre crop, biased slightly high
            l, t = (w - a.width) // 2, max(0, int((h - TH) * 0.42))
            im = im.crop((max(0, l), t, max(0, l) + min(a.width, w), t + min(TH, h)))
        im.save(dest, "WEBP", quality=a.quality, method=6)
        made += 1
    except Exception as e:
        print(f"  ! {p['id']}: {type(e).__name__}")
        missing += 1

total = sum(os.path.getsize(os.path.join(IMGDIR, f)) for f in os.listdir(IMGDIR) if f.endswith(".webp"))
n = len([f for f in os.listdir(IMGDIR) if f.endswith(".webp")])
print(f"rendered {made}, kept {skipped}, no source {missing}")
print(f"{n} images, {total/1e6:.1f} MB total, {total/max(n,1)/1000:.0f} KB average")

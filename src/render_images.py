#!/usr/bin/env python3
"""Render one WebP per place into docs/images/ from the cached source photographs.

The single-file build inlines images as base64 and has to stay under a size cap;
the published site does not, so these are rendered large enough to look right in
the full-screen detail view (default 680 px wide).

    python3 src/render_images.py               # default size/quality
    python3 src/render_images.py --width 900 --quality 78
"""
import argparse, io, json, os, re, sys, time, urllib.request
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import ENRICHED, CACHE, IMGDIR

UA = {"User-Agent": "BeautifulTurkiyeAtlas/1.0 (+https://github.com/rizabalci/beautiful-turkiye)"}

ap = argparse.ArgumentParser()
ap.add_argument("--width", type=int, default=680)
ap.add_argument("--quality", type=int, default=72)
ap.add_argument("--force", action="store_true", help="re-render images that already exist")
a = ap.parse_args()

TH = int(round(a.width * 2.05 / 3))          # the card's aspect ratio

_last = [0.0]
def source(url, tries=5):
    """The source photograph, from the cache if we have it and over the wire if not.
    A cold CI runner has an empty cache, so this has to be able to fetch — politely.
    Seven hundred rapid-fire requests get throttled, so requests are spaced and
    retried with a widening backoff."""
    if not url: return None, None
    key = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]", "_", url)[-180:])
    if os.path.isfile(key):
        return open(key, "rb").read(), None
    err = None
    for i in range(tries):
        gap = 0.12 - (time.time() - _last[0])       # ~8 requests a second, ceiling
        if gap > 0: time.sleep(gap)
        _last[0] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                blob = r.read()
            open(key, "wb").write(blob)
            return blob, None
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            time.sleep(2 ** i)                       # 1, 2, 4, 8, 16 s
    return None, err

places = json.load(open(ENRICHED, encoding="utf-8"))

# Remember what each rendered file was made from. If the upstream photograph
# changes — or the size does — the stale render is replaced rather than kept,
# which is otherwise an easy way to keep serving a picture you already rejected.
MANIFEST = os.path.join(os.path.dirname(IMGDIR), "..", "build", "rendered.json")
MANIFEST = os.path.abspath(MANIFEST)
try:
    seen = json.load(open(MANIFEST, encoding="utf-8"))
except Exception:
    seen = {}

made = skipped = 0
no_source, failed = [], []
for p in places:
    dest = os.path.join(IMGDIR, p["id"] + ".webp")
    stamp = [p.get("thumb"), a.width, a.quality]
    if os.path.exists(dest) and not a.force and seen.get(p["id"]) == stamp:
        skipped += 1; continue
    if not p.get("thumb"):
        # No usable photograph upstream any more — drop a render left over from a
        # previous source, or the atlas keeps showing a picture we since rejected.
        if os.path.exists(dest):
            os.remove(dest); seen.pop(p["id"], None)
        no_source.append(p["id"]); continue
    raw, err = source(p["thumb"])
    if not raw:
        failed.append((p["id"], err)); continue
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
        seen[p["id"]] = stamp
        made += 1
    except Exception as e:
        failed.append((p["id"], f"decode: {type(e).__name__}"))

json.dump(seen, open(MANIFEST, "w", encoding="utf-8"))

total = sum(os.path.getsize(os.path.join(IMGDIR, f)) for f in os.listdir(IMGDIR) if f.endswith(".webp"))
n = len([f for f in os.listdir(IMGDIR) if f.endswith(".webp")])
print(f"rendered {made}, already present {skipped}, "
      f"no photograph upstream {len(no_source)}, download failed {len(failed)}")
for pid, err in failed:
    print(f"  ! {pid}: {err}")
if failed:
    print("\n  Re-run this script to retry the failures — everything already "
          "fetched is cached, so it picks up where it left off.")
print(f"{n} images, {total/1e6:.1f} MB total, {total/max(n,1)/1000:.0f} KB average")

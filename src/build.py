#!/usr/bin/env python3
"""Assemble the atlas.

    python3 src/build.py                  # -> docs/index.html, images referenced from docs/images/
    python3 src/build.py --single-file    # -> build/beautiful-turkiye.html, everything inlined

The single-file build is what you drop into a chat, email or a Claude artifact.
The site build is what GitHub Pages serves; it loads images lazily, so the page
opens immediately instead of shipping ten megabytes up front.
"""
import argparse, datetime, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import ROOT, SRC, DOCS, IMGDIR, BUILD, DATA, ENRICHED, IMAGES64, MAPJSON
from content import ACT, MINTRO
from trips import TRIPS, MEVENTS
from airports import AIRPORTS

ap = argparse.ArgumentParser()
ap.add_argument("--single-file", action="store_true",
                help="inline every image as base64 into one portable HTML file")
args = ap.parse_args()

J = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))

places = json.load(open(ENRICHED, encoding="utf-8"))
MAP    = json.load(open(MAPJSON, encoding="utf-8"))

if args.single_file:
    if not os.path.exists(IMAGES64):
        sys.exit("build/images.json is missing — run: python3 src/enrich.py --embed")
    IMGS_SRC = json.load(open(IMAGES64, encoding="utf-8"))
    have = lambda pid: pid in IMGS_SRC
    ref  = lambda pid: IMGS_SRC[pid]
else:
    have = lambda pid: os.path.exists(os.path.join(IMGDIR, pid + ".webp"))
    ref  = lambda pid: f"images/{pid}.webp"

REGIONS = ["Marmara", "Aegean", "Mediterranean", "Central Anatolia", "Black Sea",
           "Southeastern Anatolia", "Eastern Anatolia"]
CATS = {"ruins", "heritage", "coast", "mountain", "water", "village", "city", "nature", "drive"}

# ---- keep only places we can actually show -----------------------------------
dropped, DATA_ = [], []
for p in places:
    if not have(p["id"]):          dropped.append((p["id"], "no photo")); continue
    if p["region"] not in REGIONS: dropped.append((p["id"], "bad region")); continue
    if p["cat"] not in CATS: p["cat"] = "heritage"
    p["act"] = [a for a in (p.get("act") or []) if a in ACT] or ["culture"]
    sea = [int(x) if isinstance(x, (int, float)) and 0 <= x <= 2 else 1 for x in (p.get("sea") or [])][:12]
    p["sea"] = sea + [1] * (12 - len(sea))
    DATA_.append(p)

DATA_.sort(key=lambda p: (REGIONS.index(p["region"]), p["lon"]))

KEEP = ["id","name","tr","prov","cat","badge","unesco","desc","season","tip","near","todo","act",
        "rev","entry","onward","sea","lat","lon","ap","apn","fd","fp","flink","apkm","apmin",
        "tag","wikiurl","credit","license"]
slim = [{**{k: p[k] for k in KEEP if k in p}, "state": p["region"]} for p in DATA_]
ids = {p["id"] for p in slim}

# ---- validate every route / month reference ----------------------------------
bad_refs = []
def clean_steps(steps):
    if not steps: return None
    out = []
    for s in steps:
        pid, txt = (list(s) + [None, None])[:2]
        if pid and pid not in ids:
            bad_refs.append(pid); pid = None
        out.append([pid, txt])
    return out or None

trips = []
for t in TRIPS:
    t = dict(t)
    for k in ("d1", "d2", "d3", "d4", "d5"):
        t[k] = clean_steps(t.get(k))
    real = sum(1 for k in ("d1","d2","d3","d4","d5") for s in (t[k] or []) if s[0])
    if real < 3:
        dropped.append((t["id"], f"route had only {real} resolvable stops")); continue
    trips.append(t)

mev = {str(m): clean_steps(rows) or [] for m, rows in MEVENTS.items()}

meta = {
  "name": "Beautiful Türkiye Explorer", "schemaVersion": 1,
  "description": (f"Interactive atlas of {len(slim)} beautiful places across all 7 regions and "
                  f"{len({p['prov'] for p in slim})} provinces of Türkiye — grid, region map, "
                  f"{len(trips)} multi-day routes and month-by-month views; filters by region, type, "
                  "activity, UNESCO and your own been-there/want-to-go marks; photos, visitor reviews, "
                  "ticket prices, and for every place the nearest airport, the flight from Vienna and "
                  "the ground leg."),
  "mcpTools": [], "mcpServerNames": [],
}

blocks = "\n".join([
  "const DATA = "      + J(slim) + ";",
  "const IMGS = "      + J({p["id"]: ref(p["id"]) for p in slim}) + ";",
  "const MAP = "       + J(MAP) + ";",
  "const TRIPS = "     + J(trips) + ";",
  "const ACT = "       + J(ACT) + ";",
  "const MINTRO = "    + J({str(k): v for k, v in MINTRO.items()}) + ";",
  "const MEVENTS = "   + J(mev) + ";",
  "const AIRPORTS = "  + J([[a[0], a[2], a[3]] for a in AIRPORTS]) + ";",
])

html = (open(os.path.join(SRC, "template.html"), encoding="utf-8").read()
        .replace("__META__", json.dumps(meta, ensure_ascii=False, indent=2))
        .replace("__DATA__", blocks)
        .replace("__BUILT__", datetime.date.today().strftime("%B %Y")))

out = (os.path.join(BUILD, "beautiful-turkiye.html") if args.single_file
       else os.path.join(DOCS, "index.html"))
open(out, "w", encoding="utf-8").write(html)
if not args.single_file:
    open(os.path.join(DOCS, ".nojekyll"), "w").close()   # stop Pages mangling the folder

# ---- a clean data export, so the dataset is usable on its own -----------------
if not args.single_file:
    json.dump(slim, open(os.path.join(DATA, "places.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    geo = {"type": "FeatureCollection", "features": [
        {"type": "Feature",
         "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
         "properties": {k: v for k, v in p.items() if k not in ("lat", "lon", "sea", "todo")}}
        for p in slim]}
    json.dump(geo, open(os.path.join(DATA, "places.geojson"), "w", encoding="utf-8"),
              ensure_ascii=False)
    import csv
    cols = ["id","name","tr","state","prov","cat","badge","unesco","lat","lon",
            "ap","apn","fd","apkm","apmin","season","entry","wikiurl"]
    with open(os.path.join(DATA, "places.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(slim)

print(f"places      {len(slim)}")
print(f"provinces   {len({p['prov'] for p in slim})}")
print("regions     " + ", ".join(f"{r}:{sum(1 for p in slim if p['state'] == r)}" for r in REGIONS))
print(f"gems {sum(1 for p in slim if p['badge']=='gem')}  "
      f"unesco {sum(1 for p in slim if p['unesco'])}  routes {len(trips)}")
if dropped: print(f"dropped     {len(dropped)}  ({', '.join(d[0] for d in dropped[:8])}…)")
if bad_refs: print(f"unresolved route refs: {sorted(set(bad_refs))}")
print(f"\n{os.path.relpath(out, ROOT)}  {os.path.getsize(out)/1e6:.1f} MB")

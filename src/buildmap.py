#!/usr/bin/env python3
"""Dissolve Türkiye's 81 provinces into the 7 geographic regions and emit SVG paths.

Boundaries come from Natural Earth (public domain), downloaded on first run and
cached in build/. Output is build/map.json: one simplified path per region, plus
the equirectangular projection constants the page uses to place its dots."""
import os, sys, shapefile, zipfile, io, json, math, urllib.request
from shapely.geometry import shape
from shapely.ops import unary_union
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import NE_ZIP, MAPJSON

NE_URL = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip"
if not os.path.exists(NE_ZIP):
    print("downloading Natural Earth admin-1 boundaries ...")
    req = urllib.request.Request(NE_URL, headers={"User-Agent": "beautiful-turkiye/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(NE_ZIP, "wb") as f:
        f.write(r.read())

REGION_OF = {}
for reg, provs in {
 "Marmara": "Istanbul Edirne Kirklareli Tekirdag Balikesir Çanakkale Bursa Yalova Kocaeli Sakarya Bilecik",
 "Aegean": "Izmir Manisa Aydin Denizli Mugla Usak Kütahya Afyonkarahisar",
 "Mediterranean": "Antalya Isparta Burdur Mersin Adana Osmaniye Hatay|K. Maras",
 "Central Anatolia": "Ankara Konya Karaman Eskisehir Kirsehir Nevsehir Nigde Aksaray Kayseri Sivas Yozgat Çankiri Kinkkale",
 "Black Sea": "Zinguldak Bartın Karabük Bolu Düzce Kastamonu Sinop Samsun Çorum Amasya Tokat Ordu Giresun Trabzon Rize Artvin Gümüshane Bayburt",
 "Eastern Anatolia": "Erzurum Erzincan Kars Ardahan Iğdir Agri Van Bitlis Mus Hakkari Tunceli Bingöl Malatya Elazig",
 "Southeastern Anatolia": "Gaziantep Sanliurfa Adiyaman Mardin Diyarbakir Batman Siirt Sirnak Kilis",
}.items():
    for tok in provs.replace("|", " ").split(" "):
        REGION_OF[tok if tok != "K." else "K. Maras"] = reg
REGION_OF["K. Maras"] = "Mediterranean"; REGION_OF.pop("K.", None); REGION_OF.pop("Maras", None)

z = zipfile.ZipFile(NE_ZIP)
r = shapefile.Reader(shp=io.BytesIO(z.read("ne_10m_admin_1_states_provinces.shp")),
                     dbf=io.BytesIO(z.read("ne_10m_admin_1_states_provinces.dbf")))
fl = [f[0] for f in r.fields[1:]]
ia, iname = fl.index("adm0_a3"), fl.index("name")

groups, unknown = {}, []
for sr in r.shapeRecords():
    rec = sr.record
    if rec[ia] != "TUR": continue
    reg = REGION_OF.get(rec[iname])
    if not reg: unknown.append(rec[iname]); continue
    groups.setdefault(reg, []).append(shape(sr.shape.__geo_interface__).buffer(0))
assert not unknown, unknown

merged = {k: unary_union(v).simplify(0.012, preserve_topology=True) for k, v in groups.items()}

# ---- projection (equirectangular, same scheme as the Slovakia atlas) ----
LON0, LON1, LAT0, LAT1 = 25.55, 45.00, 35.75, 42.20
KX = math.cos(math.radians((LAT0 + LAT1) / 2))
PAD, W = 8, 1000
SCALE = (W - 2 * PAD) / ((LON1 - LON0) * KX)
H = int(round((LAT1 - LAT0) * SCALE + 2 * PAD))

def px(lon, lat):
    return (PAD + (lon - LON0) * KX * SCALE, PAD + (LAT1 - lat) * SCALE)

def ring_d(coords):
    pts = [px(x, y) for x, y in coords]
    out, last = [], None
    for x, y in pts:                       # drop sub-pixel noise
        if last and abs(x - last[0]) < 0.45 and abs(y - last[1]) < 0.45: continue
        out.append((x, y)); last = (x, y)
    if len(out) < 3: return ""
    return "M" + " ".join(f"{x:.1f},{y:.1f}" for x, y in out) + "Z"

paths, labels = {}, {}
for name, geom in merged.items():
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    d = ""
    for poly in polys:
        if poly.area < 0.02: continue      # drop specks; keeps the big islands
        d += ring_d(list(poly.exterior.coords))
        for it in poly.interiors:
            d += ring_d(list(it.coords))
    paths[name] = d
    c = max(polys, key=lambda p: p.area).representative_point()
    x, y = px(c.x, c.y); labels[name] = [round(x, 1), round(y, 1)]

MAP = {"w": W, "h": H, "lon0": LON0, "lat1": LAT1, "kx": round(KX, 10),
       "scale": round(SCALE, 6), "pad": PAD, "paths": paths, "labels": labels}
json.dump(MAP, open(MAPJSON, "w"), ensure_ascii=False)
print(f"{W}x{H}  regions={len(paths)}  json={len(json.dumps(MAP))/1024:.0f} KB")
for k, v in paths.items(): print(f"  {k:24s} {len(v):>6d} chars  label {labels[k]}")

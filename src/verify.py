#!/usr/bin/env python3
"""Check the built atlas for the mistakes that actually happen.

    python3 src/verify.py

Exits non-zero if anything fails, so it works as a pre-commit or CI gate. The
interesting check is the geographic one: coordinates arrive from an API keyed on
an article title, and a wrong title yields coordinates that look perfectly valid
until you notice the place is in the sea.
"""
import io, json, os, sys, zipfile
import shapefile
from shapely.geometry import shape, Point
from shapely.ops import unary_union
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import ENRICHED, NE_ZIP, IMGDIR, DOCS
from trips import TRIPS, MEVENTS
from content import ACT

REGION_OF = {}
for reg, provs in {
 "Marmara": "Istanbul Edirne Kirklareli Tekirdag Balikesir Çanakkale Bursa Yalova Kocaeli Sakarya Bilecik",
 "Aegean": "Izmir Manisa Aydin Denizli Mugla Usak Kütahya Afyonkarahisar",
 "Mediterranean": "Antalya Isparta Burdur Mersin Adana Osmaniye Hatay",
 "Central Anatolia": "Ankara Konya Karaman Eskisehir Kirsehir Nevsehir Nigde Aksaray Kayseri Sivas Yozgat Çankiri Kinkkale",
 "Black Sea": "Zinguldak Bartın Karabük Bolu Düzce Kastamonu Sinop Samsun Çorum Amasya Tokat Ordu Giresun Trabzon Rize Artvin Gümüshane Bayburt",
 "Eastern Anatolia": "Erzurum Erzincan Kars Ardahan Iğdir Agri Van Bitlis Mus Hakkari Tunceli Bingöl Malatya Elazig",
 "Southeastern Anatolia": "Gaziantep Sanliurfa Adiyaman Mardin Diyarbakir Batman Siirt Sirnak Kilis",
}.items():
    for t in provs.split(): REGION_OF[t] = reg
REGION_OF["K. Maras"] = "Mediterranean"

CATS = {"ruins","heritage","coast","mountain","water","village","city","nature","drive"}
REQUIRED = ["id","name","tr","region","prov","cat","badge","unesco","desc","season","tip",
            "near","todo","act","rev","entry","onward","sea","lat","lon","ap","apn","apkm","apmin"]

fails, warns = [], []
def fail(msg): fails.append(msg)
def warn(msg): warns.append(msg)

places = json.load(open(ENRICHED, encoding="utf-8"))
ids = {p["id"] for p in places}
print(f"checking {len(places)} places\n")

# ---- 1. structure ------------------------------------------------------------
if len(ids) != len(places): fail(f"duplicate ids: {len(places) - len(ids)}")
for p in places:
    miss = [k for k in REQUIRED if k not in p]
    if miss: fail(f"{p['id']}: missing {miss}")
    if p.get("cat") not in CATS: fail(f"{p['id']}: unknown cat {p.get('cat')!r}")
    if p.get("badge") not in ("icon", "gem"): fail(f"{p['id']}: bad badge {p.get('badge')!r}")
    sea = p.get("sea") or []
    if len(sea) != 12 or any(x not in (0, 1, 2) for x in sea):
        fail(f"{p['id']}: season array is {sea!r}")
    for a in p.get("act") or []:
        if a not in ACT: fail(f"{p['id']}: unknown activity {a!r}")
    if len(p.get("todo") or []) < 1: warn(f"{p['id']}: no todo items")

# ---- 2. geography ------------------------------------------------------------
z = zipfile.ZipFile(NE_ZIP)
r = shapefile.Reader(shp=io.BytesIO(z.read("ne_10m_admin_1_states_provinces.shp")),
                     dbf=io.BytesIO(z.read("ne_10m_admin_1_states_provinces.dbf")))
fl = [f[0] for f in r.fields[1:]]
ia, inm = fl.index("adm0_a3"), fl.index("name")
groups, country = {}, []
for sr in r.shapeRecords():
    if sr.record[ia] != "TUR": continue
    g = shape(sr.shape.__geo_interface__).buffer(0)
    country.append(g)
    reg = REGION_OF.get(sr.record[inm])
    if reg: groups.setdefault(reg, []).append(g)
TR = unary_union(country).buffer(0.10)                 # ~11 km, covers offshore islands
REG = {k: unary_union(v).buffer(0.12) for k, v in groups.items()}

for p in places:
    pt = Point(p["lon"], p["lat"])
    if not TR.contains(pt):
        fail(f"{p['id']} ({p['prov']}) is outside Türkiye at {p['lat']},{p['lon']}")
    elif p["region"] in REG and not REG[p["region"]].contains(pt):
        warn(f"{p['id']} ({p['prov']}) sits outside its {p['region']} polygon — island or border?")

# ---- 3. photographs ----------------------------------------------------------
missing_img = [p["id"] for p in places
               if not os.path.exists(os.path.join(IMGDIR, p["id"] + ".webp"))]
if missing_img:
    warn(f"{len(missing_img)} places have no rendered photograph and will be dropped "
         f"from the atlas: {', '.join(missing_img[:6])}"
         + ("…" if len(missing_img) > 6 else ""))

# ---- 4. routes and month lists ----------------------------------------------
shown = ids - set(missing_img)
for t in TRIPS:
    stops = [s[0] for k in ("d1","d2","d3","d4","d5") for s in (t.get(k) or []) if s[0]]
    bad = [s for s in stops if s not in shown]
    if bad: fail(f"route {t['id']} points at missing places: {bad}")
    if len(stops) - len(bad) < 3: fail(f"route {t['id']} has fewer than 3 usable stops")
for m, rows in MEVENTS.items():
    bad = [s[0] for s in rows if s[0] and s[0] not in shown]
    if bad: fail(f"month {m} points at missing places: {bad}")

# ---- 5. the built page -------------------------------------------------------
index = os.path.join(DOCS, "index.html")
if os.path.exists(index):
    html = open(index, encoding="utf-8").read()
    if "__DATA__" in html or "__META__" in html: fail("docs/index.html still has unfilled placeholders")
    if "const DATA" not in html: fail("docs/index.html has no DATA block")
    print(f"docs/index.html  {os.path.getsize(index)/1e6:.1f} MB")
else:
    warn("docs/index.html has not been built yet")

# ---- report ------------------------------------------------------------------
for w in warns: print(f"  warn  {w}")
for f in fails: print(f"  FAIL  {f}")
print(f"\n{len(fails)} failures, {len(warns)} warnings")
sys.exit(1 if fails else 0)

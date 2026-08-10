#!/usr/bin/env python3
"""Resolve every place record against Wikipedia and Wikimedia Commons.

For each place this fetches the coordinates, the lead photograph and its licence,
then attaches the nearest airport and the ground leg from it. Output is
build/enriched.json. Pass --embed to also produce build/images.json, the base64
payload used by the single-file build.

All HTTP responses are cached under build/cache, so re-runs are nearly free.
"""
import json, glob, os, re, sys, time, math, io, urllib.parse, urllib.request
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from airports import AIRPORTS, LINK_LABEL

from paths import PLACES, CACHE, ENRICHED, IMAGES64, GAPS, OVERRIDES
UA = {"User-Agent": "BeautifulTurkiyeAtlas/1.0 (+https://github.com/rizabalci/beautiful-turkiye)"}
EMBED = "--embed" in sys.argv      # also emit the base64 payload for the single-file build

def get(url, binary=False, tries=4):
    key = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]", "_", url)[-180:])
    if os.path.exists(key):
        return open(key, "rb").read() if binary else open(key, encoding="utf-8").read()
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                b = r.read()
            open(key, "wb").write(b)
            return b if binary else b.decode("utf-8")
        except Exception as e:
            last = e; time.sleep(1.5 * (i + 1))
    raise last

def api(host, params):
    params = dict(params); params.update({"format": "json", "formatversion": "2"})
    return json.loads(get(f"https://{host}/w/api.php?" + urllib.parse.urlencode(params)))

def haversine(a, b, c, d):
    R = 6371.0
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(h))

def clean_html(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()

# ---------------------------------------------------------------- load
places = []
for f in sorted(glob.glob(os.path.join(PLACES, "*.json"))):
    places += json.load(open(f, encoding="utf-8"))
seen = set(); uniq = []
for p in places:
    if p["id"] in seen: continue
    seen.add(p["id"]); uniq.append(p)
places = uniq
print(f"{len(places)} places loaded", flush=True)

# ---------------------------------------------------------------- wikipedia pass
OV0 = json.load(open(OVERRIDES, encoding="utf-8"))
for p in places:                                   # apply title corrections up front
    if p["id"] in OV0.get("wikifix", {}):
        p["wiki"] = OV0["wikifix"][p["id"]]
titles = sorted({p["wiki"] for p in places})
info = {}
for i in range(0, len(titles), 40):
    chunk = titles[i:i+40]
    d = api("en.wikipedia.org", {
        "action": "query", "prop": "coordinates|pageimages|info",
        "titles": "|".join(chunk), "redirects": "1", "colimit": "max", "pilimit": "max",
        "pithumbsize": "1000", "piprop": "thumbnail|name", "inprop": "url"})
    q = d.get("query", {})
    norm = {n["from"]: n["to"] for n in q.get("normalized", [])}
    redir = {r["from"]: r["to"] for r in q.get("redirects", [])}
    pages = {pg["title"]: pg for pg in q.get("pages", [])}
    for t in chunk:
        t2 = redir.get(norm.get(t, t), norm.get(t, t))
        pg = pages.get(t2)
        if not pg or pg.get("missing"): continue
        co = (pg.get("coordinates") or [{}])[0]
        info[t] = {"title": pg["title"], "url": pg.get("fullurl"),
                   "lat": co.get("lat"), "lon": co.get("lon"),
                   "file": pg.get("pageimage"), "thumb": (pg.get("thumbnail") or {}).get("source")}
    print(f"  wiki {i+len(chunk)}/{len(titles)}", flush=True)

# ---------------------------------------------------------------- licence pass
files = sorted({v["file"] for v in info.values() if v.get("file")})
lic = {}
for i in range(0, len(files), 25):
    chunk = files[i:i+25]
    try:
        d = api("commons.wikimedia.org", {
            "action": "query", "prop": "imageinfo", "iiprop": "extmetadata",
            "titles": "|".join("File:" + f for f in chunk)})
    except Exception:
        continue
    for pg in d.get("query", {}).get("pages", []):
        if pg.get("missing"): continue
        ii = (pg.get("imageinfo") or [{}])[0].get("extmetadata", {})
        lic[pg["title"][5:]] = {
            "artist": clean_html(ii.get("Artist", {}).get("value", ""))[:90],
            "lic": clean_html(ii.get("LicenseShortName", {}).get("value", ""))[:40]}
    print(f"  lic {i+len(chunk)}/{len(files)}", flush=True)

# ---------------------------------------------------------------- images
IMGS = {}
def fetch_img(pid, url):
    try:
        raw = get(url, binary=True)
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        w, h = im.size
        tw = 372
        th = int(round(tw * 2.05 / 3))          # card aspect
        s = max(tw / w, th / h)
        if s < 1:
            im = im.resize((max(1, int(w*s)), max(1, int(h*s))), Image.LANCZOS)
        w, h = im.size
        if w > tw or h > th:                     # centre crop
            l, t = (w - tw)//2, max(0, int((h - th) * 0.42))
            im = im.crop((max(0,l), t, max(0,l)+min(tw,w), t+min(th,h)))
        buf = io.BytesIO(); im.save(buf, "WEBP", quality=34, method=6)
        return "data:image/webp;base64," + __import__("base64").b64encode(buf.getvalue()).decode()
    except Exception as e:
        print(f"    !img {pid}: {type(e).__name__}", flush=True)
        return None

OV = json.load(open(OVERRIDES, encoding="utf-8"))

def commons_lookup(term):
    """Find a Commons photo for a place that has no Wikipedia lead image."""
    try:
        d = api("commons.wikimedia.org", {
            "action": "query", "generator": "search", "gsrsearch": term,
            "gsrnamespace": "6", "gsrlimit": "8", "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime", "iiurlwidth": "1000"})
    except Exception:
        return None
    for pg in sorted(d.get("query", {}).get("pages", []), key=lambda x: x.get("index", 99)):
        ii = (pg.get("imageinfo") or [{}])[0]
        if not ii.get("thumburl") or ii.get("mime", "") not in ("image/jpeg", "image/png", "image/webp"):
            continue
        if is_junk(pg.get("title", "")): continue      # search returns locator maps too
        em = ii.get("extmetadata", {})
        return {"thumb": ii["thumburl"],
                "artist": clean_html(em.get("Artist", {}).get("value", ""))[:90] or "Wikimedia Commons",
                "lic": clean_html(em.get("LicenseShortName", {}).get("value", ""))[:40]}
    return None

# Wikipedia's lead image for a district is very often a locator map, a district
# outline or a municipal logo rather than a photograph of anywhere. Those get
# rejected here so the Commons fallbacks can find an actual picture.
JUNK_RE = re.compile(
    r"(?:^|[_\-. ])maps?(?:$|[_\-. ])|locator|location|districts?[_\-]of|[_\-]districts"
    r"|harita|landsat|sentinel|satellite|view[_\-. ]of[_\-. ]earth|iss0|iss1"
    r"|coat[_\-]of[_\-]arms|flag|logo|seal[_\-]of|plan[_\-]of|belediye"
    r"|topographic|blank|diagram|schematic|karte|kaart|mappa|carte[_\-. ]|atlas[_\-. ]|chart", re.I)

def is_junk(name):
    return bool(JUNK_RE.search(name or ""))

def commons_geo(p):
    """Last resort for a photo: geotagged Commons files near the place, scored by name match."""
    try:
        d = api("commons.wikimedia.org", {
            "action": "query", "generator": "geosearch",
            "ggscoord": f"{p['lat']}|{p['lon']}", "ggsradius": "4000",
            "ggsnamespace": "6", "ggslimit": "25",
            "prop": "imageinfo", "iiprop": "url|extmetadata|mime", "iiurlwidth": "1000"})
    except Exception:
        return None
    toks = {t for t in re.split(r"[^0-9A-Za-zÇĞİÖŞÜçğıöşü]+",
            (p["name"] + " " + p.get("tr", "") + " " + p["prov"]).lower()) if len(t) > 3}
    best = None
    for pg in d.get("query", {}).get("pages", []):
        ii = (pg.get("imageinfo") or [{}])[0]
        title = pg["title"][5:]
        low = title.lower()
        if not ii.get("thumburl") or not ii.get("mime", "").startswith("image/"): continue
        if is_junk(title): continue
        score = sum(1 for t in toks if t in low)
        if best is None or score > best[0]:
            em = ii.get("extmetadata", {})
            best = (score, {"thumb": ii["thumburl"],
                            "artist": clean_html(em.get("Artist", {}).get("value", ""))[:90] or "Wikimedia Commons",
                            "lic": clean_html(em.get("LicenseShortName", {}).get("value", ""))[:40]})
    return best[1] if best else None

_geo_last = [0.0]
def nominatim(q):
    """Last-resort coordinates: geocode the human-readable 'near' string."""
    key = os.path.join(CACHE, "geo_" + re.sub(r"[^A-Za-z0-9]", "_", q)[:120])
    if os.path.exists(key):
        try: return json.load(open(key, encoding="utf-8"))
        except Exception: pass
    wait = 1.1 - (time.time() - _geo_last[0])
    if wait > 0: time.sleep(wait)
    _geo_last[0] = time.time()
    try:
        u = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
            {"q": q, "format": "json", "limit": 1, "countrycodes": "tr"})
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
            d = json.loads(r.read())
        if not d: return None
        res = [float(d[0]["lat"]), float(d[0]["lon"])]
        json.dump(res, open(key, "w"))
        return res
    except Exception:
        return None

# ---------------------------------------------------------------- assemble
out, missing_wiki, missing_img, geocoded = [], [], [], []
for n, p in enumerate(places):
    w = dict(info.get(p["wiki"]) or {})
    ovc = OV["coords"].get(p["id"])
    if ovc:
        w.setdefault("url", "https://en.wikipedia.org/wiki/" + urllib.parse.quote(p["wiki"].replace(" ", "_")))
        w["lat"], w["lon"] = ovc
    if w.get("lat") is None:                       # fall back to geocoding "near"
        g = nominatim(p["near"]) or nominatim(p["name"] + ", " + p["prov"] + ", Türkiye")
        if g:
            w["lat"], w["lon"] = g
            w.setdefault("url", "https://en.wikipedia.org/wiki/" + urllib.parse.quote(p["wiki"].replace(" ", "_")))
            geocoded.append(p["id"])
        else:
            missing_wiki.append((p["id"], p["wiki"] + " [no coords]")); continue
    if w.get("file") and is_junk(w["file"]):
        w["thumb"] = None                          # a locator map is not a photograph of a place
    if not w.get("thumb"):                         # two shots at a photo
        for term in (OV["imgsearch"].get(p["id"]), p["name"] + " " + p["prov"], p["tr"] + " " + p["prov"]):
            if not term: continue
            alt = commons_lookup(term)
            if alt:
                w["thumb"] = alt["thumb"]
                lic[alt["thumb"]] = {"artist": alt["artist"], "lic": alt["lic"]}
                w["file"] = alt["thumb"]; break
        if not w.get("thumb"):
            alt = commons_geo({**p, "lat": w["lat"], "lon": w["lon"]})
            if alt:
                w["thumb"] = alt["thumb"]
                lic[alt["thumb"]] = {"artist": alt["artist"], "lic": alt["lic"]}
                w["file"] = alt["thumb"]
    p = dict(p)
    p["lat"] = round(w["lat"], 5); p["lon"] = round(w["lon"], 5)
    p["wikiurl"] = w["url"]
    p["thumb"] = w.get("thumb")   # source photo URL, so images can be re-rendered at any size
    li = lic.get(w.get("file") or "", {})
    p["credit"] = li.get("artist", "") or "Wikimedia Commons"
    p["license"] = li.get("lic", "")
    # nearest airport
    best = min(AIRPORTS, key=lambda a: haversine(p["lat"], p["lon"], a[2], a[3]))
    gc = haversine(p["lat"], p["lon"], best[2], best[3])
    p["ap"] = best[0]; p["apn"] = best[1]
    p["fd"] = best[5]; p["fp"] = best[6]; p["flink"] = LINK_LABEL[best[4]]
    p["apkm"] = int(round(gc * 1.30 / 5) * 5) or 5
    p["apmin"] = int(round((p["apkm"] / 62) * 60 / 5) * 5) or 5
    p["tag"] = re.sub(r"[^a-z0-9]", "", p["id"].replace("-", ""))
    if w.get("thumb"):
        if EMBED:
            d = fetch_img(p["id"], w["thumb"])
            if d: IMGS[p["id"]] = d
            else: missing_img.append(p["id"])
    else:
        missing_img.append(p["id"])
    out.append(p)
    if (n+1) % 25 == 0: print(f"  built {n+1}/{len(places)}", flush=True)

json.dump(out, open(ENRICHED, "w", encoding="utf-8"), ensure_ascii=False)
if EMBED: json.dump(IMGS, open(IMAGES64, "w", encoding="utf-8"), ensure_ascii=False)
json.dump({"missing_wiki": missing_wiki, "missing_img": missing_img, "geocoded": geocoded},
          open(GAPS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nDONE  kept {len(out)}  ·  no wiki/coords {len(missing_wiki)}  ·  no image {len(missing_img)}")
if EMBED: print(f"images payload {os.path.getsize(IMAGES64)/1e6:.1f} MB")

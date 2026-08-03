# Beautiful Türkiye

An interactive atlas of **719 places worth the flight**, across all 7 regions and all 81 provinces of Türkiye — from Lycian coves and Kaçkar yaylas to Göbekli Tepe and the Phrygian valleys.

**→ [rizabalci.github.io/beautiful-turkiye](https://rizabalci.github.io/beautiful-turkiye/)**

It is a single self-contained page with four views: a filterable grid, a region map, 28 multi-day routes, and a month-by-month "where is it good right now" layer. Every place carries a photograph, three things to actually do, an insider tip, an honest note on what visitors complain about, a ticket price, the twelve-month season score, and — because this was built by someone who flies in from Vienna — the nearest airport, the flight, and the ground leg from it.

| | |
|---|---|
| Places | 719 |
| Provinces covered | 81 of 81 |
| Hidden gems | 485 |
| UNESCO World Heritage sites | 57 |
| Multi-day routes | 28 |
| Repository size | ~4 MB (the site is built, not committed) |

## What makes it different from a list of sights

**The travel maths is real.** Each place is matched by great-circle distance to its nearest usable airport, out of 51 in the table. Vienna has year-round nonstops to Istanbul (IST and Sabiha Gökçen), Ankara, İzmir and Antalya, and summer nonstops to Bodrum and Dalaman; everything else routes through Istanbul, and the page says which. The "easiest to reach" sort ranks by total door-to-door time rather than kilometres.

**The reviews are not advertising.** Every record's `rev` field is required to carry the common complaint alongside the praise — the touts, the unpaved last kilometre, the closure, the tour-bus hour. Hasankeyf says plainly that most of it went under the reservoir in 2020. Antakya and Kahramanmaraş note what the 2023 earthquakes did. The Hakkari and Şırnak entries flag travel advisories.

**The seasons are honest.** Interior Anatolia and the southeast score `0` in July and August because they pass 40 °C. Eastern passes and yayla roads score `0` from November to April because they are under snow. The Mount Nemrut summit road is `0` for seven months of the year, which is the single most useful fact about visiting it.

**The geography is checked, not asserted.** Coordinates come from the Wikipedia API rather than from prose, and the build verifies every point falls inside its own region's polygon. That check caught two bad coordinates in 719 — Damlataş Cave sitting in the sea and the Zap valley landing in Iraq.

## How it is built

```
data/places/*.json   hand-written place records, one file per area   ← the actual content
        │
        ├── src/enrich.py       Wikipedia coordinates + Commons photo + licence,
        │                       nearest airport, ground leg          → build/enriched.json
        ├── src/buildmap.py     Natural Earth provinces dissolved
        │                       into 7 regions, projected            → build/map.json
        ├── src/render_images.py  one WebP per place                 → docs/images/
        └── src/build.py        validates, assembles, injects        → docs/index.html
```

Nothing about a place's location or photograph is written by hand. The source records name an English Wikipedia article; everything geographic is resolved from the API, with three fallbacks when an article has no lead photo (a Commons keyword search, a Commons geosearch scored by name match, and a small table of manual overrides). Satellite tiles, locator maps and flags are rejected as lead images — they are not photographs of a place.

The published site is **not committed** — `docs/` is generated. The Pages workflow rebuilds it from source on every push and deploys the result, which keeps 712 photographs out of git history and means the repository is about 4 MB rather than 40. A cold build fetches everything from Wikipedia and Commons and takes roughly ten minutes; after that the cache makes it about one.

### Building it yourself

```bash
pip install -r requirements.txt

python3 src/enrich.py          # ~10 min cold, seconds warm (everything caches in build/)
python3 src/buildmap.py        # downloads Natural Earth boundaries on first run
python3 src/render_images.py   # → docs/images/*.webp
python3 src/build.py           # → docs/index.html
python3 src/verify.py          # structural + geographic checks, exits non-zero on failure

python3 -m http.server -d docs 8000     # then open http://localhost:8000
```

For a portable one-file version with every image inlined as base64 — for email, a chat, or an offline laptop:

```bash
python3 src/enrich.py --embed
python3 src/build.py --single-file    # → build/beautiful-turkiye.html
```

The site build keeps images as separate lazily-loaded files, so the page opens in about a second. The single-file build is one 10 MB HTML document that works with no server and no network at all.

## The data on its own

Three exports are regenerated on every build, if you want the dataset without the interface:

- `data/places.json` — the full enriched records
- `data/places.geojson` — points with properties, drops straight into QGIS, Felt or Mapbox
- `data/places.csv` — a flat table of the essentials

## Adding or fixing a place

Records live in `data/places/`, split by area. The field-by-field contract — including the tone rules, the category and activity vocabularies, and what the season scores mean — is in [SPEC.md](SPEC.md). The only field that must be exactly right is `wiki`: it is the English Wikipedia article title, and the whole enrichment chain hangs off it.

A place whose photograph cannot be found is still included — it gets a plain placeholder card rather than being dropped, so one flaked download degrades a single card instead of breaking a route and failing the deploy.

Add your record to the appropriate file, then re-run the pipeline. `build.py` validates as it goes, and `verify.py` runs the harder checks — it will tell you if a route now points at a place that does not exist, if a category is unknown, if a season array is malformed, or if your new place's coordinates landed outside the region you filed it under. Both run automatically on pull requests that touch `data/` or `src/`.

## Credits and licensing

Photographs are by Wikimedia Commons contributors under their respective free licences; the photographer and licence are shown on every place. Province boundaries are from [Natural Earth](https://www.naturalearthdata.com/) (public domain). Coordinates and articles are from Wikipedia under CC BY-SA 4.0.

The code and the written place descriptions in this repository are MIT-licensed — see [LICENSE](LICENSE). The photographs are not: they remain under whatever licence their contributor chose, and the per-place attribution is there so you can honour it.

## A caveat worth reading

Prices are in lira with euro equivalents, and the lira moves. Flight times and fares are typical ranges, not quotes. Opening hours change, caves close in winter, and mountain roads close earlier than anyone expects. Treat every number here as an order of magnitude and check locally before a long drive.

---

Sister atlases: Beautiful Austria and Beautiful Slovakia, built on the same engine.

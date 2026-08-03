"""Shared paths. Everything is resolved from the repository root, so the scripts
can be run from anywhere: `python src/enrich.py`, `python3 src/build.py`, etc."""
import os

SRC   = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.dirname(SRC)
DATA  = os.path.join(ROOT, "data")
PLACES= os.path.join(DATA, "places")          # hand-written source records, one file per area
BUILD = os.path.join(ROOT, "build")           # intermediates + HTTP cache (git-ignored)
CACHE = os.path.join(BUILD, "cache")
DOCS  = os.path.join(ROOT, "docs")            # the published site (GitHub Pages root)
IMGDIR= os.path.join(DOCS, "images")

ENRICHED = os.path.join(BUILD, "enriched.json")
IMAGES64 = os.path.join(BUILD, "images.json")  # base64 payload, only for the single-file build
MAPJSON  = os.path.join(BUILD, "map.json")
GAPS     = os.path.join(BUILD, "gaps.json")
OVERRIDES= os.path.join(DATA, "overrides.json")
NE_ZIP   = os.path.join(BUILD, "ne10_admin1.zip")

for d in (BUILD, CACHE, DOCS, IMGDIR):
    os.makedirs(d, exist_ok=True)

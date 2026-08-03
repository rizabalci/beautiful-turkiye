# Beautiful Türkiye — place-record spec

You are writing records for an interactive atlas of beautiful places in Türkiye, built for a
Turkish traveller (Riza) who lives in Vienna and flies back regularly. The atlas is the sister
of two existing artifacts ("Beautiful Austria Explorer", "Beautiful Slovakia Explorer").

Tone: a well-travelled, unsentimental friend who has actually been there. Concrete, sensory,
specific. No brochure language ("nestled", "must-see", "breathtaking", "hidden treasure",
"a feast for the senses"). Never use exclamation marks.

## Output

Write ONE file: the exact path you are given. It must contain a single JSON array of objects,
UTF-8, valid JSON (no trailing commas, no comments, no markdown fences). Nothing else in the file.

## Record schema — every field is REQUIRED

```json
{
  "id": "goreme-open-air-museum",
  "name": "Göreme Open-Air Museum",
  "tr": "Göreme Açık Hava Müzesi",
  "region": "Central Anatolia",
  "prov": "Nevşehir",
  "cat": "ruins",
  "badge": "icon",
  "unesco": true,
  "desc": "...",
  "season": "...",
  "tip": "...",
  "near": "Göreme, Nevşehir, Türkiye",
  "wiki": "Göreme Open Air Museum",
  "todo": ["...", "...", "..."],
  "act": ["culture", "photo"],
  "rev": "...",
  "entry": "...",
  "onward": "...",
  "sea": [0,0,1,2,2,1,1,1,2,2,1,0]
}
```

### Field rules

- **id** — lowercase kebab-case, ASCII only (transliterate: ş→s, ı→i, ğ→g, ü→u, ö→o, ç→c),
  globally unique. Prefix with the place name, not the province.
- **name** — the name an English-speaking traveller would search for. If the Turkish name is
  the common one, use it (e.g. "Ihlara Valley", "Sümela Monastery", "Saklıkent Gorge").
- **tr** — the Turkish name. If identical to `name`, repeat it.
- **region** — EXACTLY one of: `Marmara`, `Aegean`, `Mediterranean`, `Central Anatolia`,
  `Black Sea`, `Eastern Anatolia`, `Southeastern Anatolia`.
- **prov** — the province (il), correctly spelled in Turkish, e.g. `Şanlıurfa`, `Muğla`.
- **cat** — EXACTLY one of:
  - `ruins` — ancient cities, archaeological sites, rock-cut sites, tumuli
  - `heritage` — mosques, churches, monasteries, caravanserais, castles, bridges, hans, palaces
  - `coast` — beaches, coves, bays, peninsulas, islands, lagoons
  - `mountain` — peaks, plateaus (yayla), highlands, volcanoes, ski areas, viewpoints
  - `water` — lakes, rivers, waterfalls, canyons, caves, travertines, deltas, hot springs
  - `village` — villages and small old towns whose fabric is the attraction
  - `city` — cities and city quarters
  - `nature` — forests, national parks, wildlife reserves, dunes, salt flats, meadows
  - `drive` — scenic roads, mountain passes, ferry crossings, historic railway journeys
- **badge** — `icon` for places most people have heard of, `gem` for the ones they haven't.
  Aim for roughly 65% `gem` in your batch. Be honest: Pamukkale is `icon`, not `gem`.
- **unesco** — `true` only if the place is on the UNESCO World Heritage List (inscribed, not
  tentative). Otherwise `false`. Do not guess; if unsure, `false`.
- **desc** — 2–3 sentences, 45–65 words. What it actually looks and feels like, and why it is
  worth the detour. One concrete detail beats three adjectives.
- **season** — one short line, e.g. `May–Jun and Sep–Oct — July heat is brutal on the plateau`.
- **tip** — ONE sentence of insider advice a first-timer would not know: the right hour, the
  right entrance, the local bus, the thing everyone misses, the thing that ruins the visit.
- **near** — a string Google Maps can geocode: `Town, Province, Türkiye`.
- **wiki** — the EXACT title of the English Wikipedia article for this place, as it appears in
  the URL after `/wiki/` (with spaces instead of underscores). This is used to fetch the
  photograph and coordinates, so accuracy matters more than anything else in the record.
  Use the most specific article that has a photo. If the place has no English article, use the
  closest article that does (e.g. the village, the national park, the nearest town) — never
  invent a title. Prefer titles you are confident exist.
- **todo** — exactly 3 items, each under 60 characters, imperative or noun-phrase, specific.
- **act** — 1–5 keys from: `hike`, `swim`, `dive`, `boat`, `bike`, `climb`, `winter`, `spa`,
  `food`, `culture`, `photo`, `family`, `wildlife`, `stars`, `air`, `rail`.
  (`air` = ballooning/paragliding, `stars` = dark skies, `spa` = thermal/hamam.)
- **rev** — ONE sentence synthesising what visitors actually report, INCLUDING the common
  complaint (crowds, touts, a long unpaved road, closed in winter, the entrance fee jump,
  the drone ban). This is the field that makes the atlas trustworthy — never make it pure praise.
- **entry** — 2026 ticket reality. Turkish state museums price in ₺ and many are foreigner-priced
  in €; the Museum Pass Türkiye covers most. Give an approximate figure with a € equivalent,
  e.g. `₺600 (≈€13) · covered by Museum Pass Türkiye`. Use `Free` where it is free. If you are
  not confident of the number, write `Small fee — check locally` rather than inventing one.
- **onward** — how you actually reach it once you have landed: which airport, then the road or
  the bus. E.g. `Kayseri (ASR) or Nevşehir (NAV) airport, then 45-min shuttle to Göreme;
  a hire car is worth it for the valleys`. One sentence. Do NOT invent flight times — just name
  the airport and the ground leg.
- **sea** — 12 integers, January→December: `2` = at its best, `1` = fine/open, `0` = poor,
  closed, or actively unpleasant. Be honest about winter closures, summer heat (interior
  Anatolia and the southeast are 40 °C+ in July–August), the Black Sea's rain, snowbound
  eastern passes (many are `0` from November to April), and jellyfish/meltemi on the coast.

## Selection rules for your batch

- Weight strongly toward **hidden gems**, **nature and hiking**, **ancient sites**, and
  **coast/food/old towns** — in that spirit, but keep the famous anchors too, because the atlas
  has to be usable as a real trip planner.
- Cover the whole geography you are assigned, not just its capital. Small provinces deserve
  2–5 entries each; big ones more.
- Include every UNESCO World Heritage site that falls in your area.
- No duplicates within your batch, and stay strictly inside your assigned provinces so batches
  don't collide.
- Vary the categories — a batch that is 80% `ruins` is a failed batch.
- Real places only. If you are not confident a place exists as described, drop it.

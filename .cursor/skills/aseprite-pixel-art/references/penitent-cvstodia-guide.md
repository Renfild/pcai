# Penitent / Cvstodia Locations (Blasphemous-inspired)

Purist pixel craft for dark Spanish-gothic Metroidvania stages.

## Traditions we follow

- **Limited ramps** — ash stone, faded gold, penitent crimson (or snow / bilge)
- **No fake modern shaders** — only Aseprite blend modes (multiply / screen / addition)
- **Main layer** — hard dark outline + bright walkable lip; interactive only
- **Close background** — no outline, flatter/saturated; never looks collidable
- **Far** — few colors, silhouettes, soft dither
- **Foreground** — margin props only; never covers the player lane
- **Detail budget** — rich on walkable edges; quiet inner fills

Influences: Blasphemous (The Game Kitchen) — Sevillian Holy Week iconography, Goya/Ribera gloom, Castlevania structure. Pixel “purist” stance per Enrique Cabeza / Colinet interviews.

## Themes

| Key | Location vibe |
|---|---|
| `penitent` | Mother of Mothers — ash nave, gold, blood, thorns |
| `olive_wither` | Where Olive Trees Wither — cold hills, snow, dead olives |
| `cistern` | Desecrated Cistern — wet stone, bilge, black water |

## Helper

`scripts/penitent_style.py` — arches, stained glass, thorns, cages, candles, columns, olive trees, dither, stone blocks.

## Stages in this repo

| Folder | Export |
|---|---|
| `pixel-art/mother-of-thorns/` | cathedral nave + thorn pit |
| `pixel-art/olive-wither-hills/` | snowy olive path + ravine |
| `pixel-art/desecrated-cistern/` | flooded underground |

Each writes `.aseprite` / `.png` / `.gif` / `*_game.json` with `validation.ok`.

```bash
python3 pixel-art/mother-of-thorns/build.py
python3 pixel-art/olive-wither-hills/build.py
python3 pixel-art/desecrated-cistern/build.py
```

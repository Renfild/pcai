# Environments & Scenes Guide

Use this when building **locations, backgrounds, rooms, overworld tiles, or multi-layer scenes** — not single characters.

## Canvas sizing

| Use case | Typical size | Notes |
|---|---|---|
| Room / interior | 160×96 to 320×180 | Keep character sprites readable at 1x |
| Overworld chunk | 256×224 (SNES-ish) or 240×160 (GBA) | Match target engine viewport |
| Parallax strip | width ≥ viewport × 2 | Allows seamless scroll |
| Tileable backdrop | 32×32 / 64×64 / 128×128 | Power-of-two helps engines |

Decide the **camera frame** first, then give yourself margin for parallax layers that scroll at different rates.

## Layer stack (back → front)

Suggested naming and blend modes:

1. `sky` — flat or gradient fill (`normal`)
2. `far` — mountains / distant trees (`normal`, maybe lower opacity)
3. `mid` — buildings / cliffs (`normal`)
4. `near` — foreground props (`normal`)
5. `lighting` — multiply wash for time-of-day (`multiply`, opacity 40–120)
6. `glow` — lamps, windows, magic (`addition` or `screen`)
7. `particles` — dust, embers, rain (`addition` or `normal`)
8. `overlay` — vignette / weather film (`multiply` or `normal` low opacity)

Characters / interactive props usually sit between `near` and `lighting`.

## Depth cueing

- Cooler + desaturated + lower contrast → farther
- Warm accents + sharper silhouettes → nearer
- Overlap beats scale: a small prop overlapping a large one still reads as closer
- Drop soft ground shadows on a dedicated `shadow` multiply layer (opacity ~80–140)

## Parallax

For an N-frame horizontal scroll preview:

```python
scroll = frame * speed_px   # different speed per layer
# stamp layer art at x = -scroll % layer_width
```

Speeds (relative to camera): far 0.25, mid 0.5, near 1.0, particles 1.1+.

## Seamless tiling

1. Lock left/right (and top/bottom) edge pixels first
2. Fill interior second
3. Preview with a 2×2 or 3×3 stamp before accepting
4. Avoid unique landmarks that only appear once on a tile edge

## Scene workflow

1. Block silhouettes on `mid` / `near` with flat colors
2. Add value groups (3–5) before hue
3. Push depth with a multiply lighting wash
4. Add additive glow only on actual light sources
5. Finish with sparse particles (dust / fireflies / rain) — less than you think

See also: [lighting-and-particles-guide.md](lighting-and-particles-guide.md)

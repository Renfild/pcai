---
name: aseprite-pixel-art
description: Create pixel-art characters, props, locations/backgrounds/scenes, and VFX as real .aseprite files (pure Python, no Aseprite app required). Writes multi-layer sprites with blend modes (addition/screen/multiply/…), animates with walk_cycle/wave_curve, and builds glow/particle FX via fx_helpers so PNG/GIF previews match Aseprite. Use when the user asks for pixel art, sprites, .aseprite files, walk cycles, idle/attack animations, tilesets, rooms, backgrounds, environments, scenes, lighting, glow, torches, particles, embers, sparks, magic FX, or game-ready retro art.
---

# Aseprite Pixel Art (with FX)

Author layered `.aseprite` sprites in Python. Previews composite **real blend modes**, so additive glow and particles look like they will in Aseprite.

Dependencies: `pip install pillow`

## Core workflow

1. **Brief** — canvas size, palette budget, light direction, whether FX/layers are needed.
2. **Build** — write a small script that uses `scripts/aseprite_io.py` (+ `fx_helpers.py` when glowing/animating).
3. **Preview** — `sprite.preview()` / `preview_gif()`; look at the image; fix.
4. **Deliver** — `.aseprite` master + scaled PNG/GIF. Keep the build script as source of truth.

For locations/backgrounds read [references/environments-and-scenes-guide.md](references/environments-and-scenes-guide.md).  
For glow/particles/blend modes read [references/lighting-and-particles-guide.md](references/lighting-and-particles-guide.md).

Multi-layer FX pattern: solid art on `normal` layers; light on `addition`/`screen`; shadow washes on `multiply`.

## API cheat-sheet

```python
import sys
from pathlib import Path
SKILL = Path(__file__).resolve().parents[/* adjust */]
sys.path.insert(0, str(SKILL / "scripts"))

from aseprite_io import Sprite, load_aseprite
from fx_helpers import (
    walk_cycle, wave_curve, radial_glow, flicker,
    spawn_burst, simulate_particles, stamp_particles, ember_trail, apply_glow,
)

s = Sprite(48, 48)
s.add_layer("body")                              # normal
s.add_layer("glow", blend_mode="addition")       # also: screen, multiply, overlay, …
s.add_frame(duration_ms=100)                     # returns new index; copy_from=i supported
s.put_pixel(x, y, (r, g, b, a), layer="body", frame=0)
s.fill_rect(x0, y0, x1, y1, color, layer=…, frame=…)
s.fill_circle(cx, cy, r, color, layer=…, frame=…, fill=True)
s.stamp([(x, y, rgba), …], layer="glow", frame=0)
s.add_tag("idle", 0, 3)
s.set_frame_duration(0, 120)

img = s.composite_frame(0)          # PIL RGBA — blend modes simulated
s.preview("preview.png", scale=8)
s.preview_gif("anim.gif", scale=8)
s.save("torch.aseprite")

s2 = load_aseprite("torch.aseprite")
```

### Blend mode strings

`normal` · `multiply` · `screen` · `overlay` · `darken` · `lighten` · `color_dodge` · `color_burn` · `hard_light` · `soft_light` · `difference` · `exclusion` · `addition` (alias `add`) · `subtract` · `divide`

### FX helpers

| Helper | Purpose |
|---|---|
| `walk_cycle(frame, frames=8, stride=2, bob=1)` | Leg/arm/body offsets; **bob peaks at passing** |
| `wave_curve(frame, frames, amplitude, phase=0, cycles=1)` | Looping sine |
| `radial_glow(cx, cy, radius, color, falloff=2, hollow=0)` | Soft light ring pixels |
| `flicker(frame, base=1, amount=0.15, seed=0)` | Torch/candle intensity |
| `spawn_burst(...)` / `simulate_particles(sys)` / `stamp_particles(sys)` | Tiny particle system |
| `ember_trail(cx, cy, frames, …)` | Rising embers per-frame pixel lists |
| `apply_glow(sprite, layer, frame, pixels)` | Stamp helper |

## Minimal torch (glow + embers)

```python
s = Sprite(32, 32)
s.add_layer("body")
s.add_layer("glow", blend_mode="addition")
s.add_layer("embers", blend_mode="addition")
for i in range(7):
    if i: s.add_frame(80)
# pole + bowl on body…
for f in range(s.frame_count):
    inten = flicker(f, seed=1)
    apply_glow(s, "glow", f, radial_glow(16, 12, 6, (255, 160, 40, int(140 * inten))))
for f, px in enumerate(ember_trail(16, 11, s.frame_count, seed=2)):
    s.stamp(px, layer="embers", frame=f)
s.save("torch.aseprite"); s.preview_gif("torch.gif", scale=8)
```

## Quality bar

- Readable silhouette at 1x before adding FX
- Palette discipline (≈8–16 colors for characters)
- FX on separate blend layers — never baked into lineart
- At least 2 preview passes (see → fix → see) before delivery

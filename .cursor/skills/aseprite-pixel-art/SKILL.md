---
name: aseprite-pixel-art
description: Create pixel-art for platformer games and general retro art as real .aseprite files (pure Python, no Aseprite app). Generates locations/stages (platforms, tiles, collision hints), character animations (idle/run/jump/land/attack), and logic-driven lighting (point/shaft/spot + time-of-day). Blend modes (addition/screen/multiply) composite correctly in previews. Use when the user asks for pixel art, platformer stages, levels, rooms, tilesets, environments, backgrounds, locations, walk/run/jump cycles, sprite animation, lighting, glow, lamps, god-rays, particles, or game-ready .aseprite assets.
---

# Aseprite Pixel Art — Platformer Ready

Layered `.aseprite` authoring in Python. Previews simulate **real blend modes**. Oriented for **pixel platformers**: location gen, animation curves, lighting logic.

Deps: `pip install pillow`

## Core workflow

1. **Brief** — platformer stage vs character vs prop; tile size; theme; time-of-day.
2. **Generate logic** — `location_gen` / `anim_helpers` / `lighting_logic` (don't hand-wave layouts).
3. **Build script** — draw from those specs into `aseprite_io.Sprite`.
4. **Preview** — `preview` / `preview_gif`; fix; deliver `.aseprite` + collision hints.

### Read when…

| Task | Reference |
|---|---|
| Platformer stages, tiles, collision, themes | [references/platformer-guide.md](references/platformer-guide.md) |
| Interiors / scenes / parallax | [references/environments-and-scenes-guide.md](references/environments-and-scenes-guide.md) |
| Glow, particles, blend modes | [references/lighting-and-particles-guide.md](references/lighting-and-particles-guide.md) |

## API cheat-sheet

```python
import sys
from pathlib import Path
SKILL = Path("…/.cursor/skills/aseprite-pixel-art")
sys.path.insert(0, str(SKILL / "scripts"))

from aseprite_io import Sprite, load_aseprite
from fx_helpers import walk_cycle, wave_curve, radial_glow, flicker, ember_trail, apply_glow
from anim_helpers import idle_breath, run_cycle, jump_arc, land_squash, attack_swing, anim_tag_plan, pose_for
from lighting_logic import LightingSetup, platformer_default_lights, stamp_lighting, apply_time_of_day
from location_gen import make_platformer_room, build_platformer_stage, theme_colors

# —— Stage ——
loc = make_platformer_room(theme="castle", style="linear", width=320, height=176, seed=2)
s, loc = build_platformer_stage(Sprite, loc)
setup = platformer_default_lights(loc.width, loc.height, loc.ground_y, "dusk", loc.windows, loc.lamps)
stamp_lighting(s, setup, frame=0)
print(loc.collision_map())   # engine AABBs
s.save("stage.aseprite")

# —— Character anim plan ——
plan = anim_tag_plan(["idle", "run", "jump", "land"])
pose = run_cycle(frame, frames=8, stride=3)

# —— Manual sprite ——
s = Sprite(48, 48)
s.add_layer("body")
s.add_layer("glow", blend_mode="addition")
s.put_pixel(x, y, (r,g,b,a), layer="body", frame=0)
s.composite_frame(0); s.preview("p.png", scale=8); s.preview_gif("a.gif", scale=8)
```

### Modules

| Module | Role |
|---|---|
| `aseprite_io.py` | Sprite R/W, layers, blend-aware `composite_frame` |
| `fx_helpers.py` | glow, flicker, particles, walk/wave curves |
| `anim_helpers.py` | idle/run/jump/land/attack + `anim_tag_plan` |
| `lighting_logic.py` | LightSource, time-of-day, shafts/points, `stamp_lighting` |
| `location_gen.py` | `make_platformer_room`, themes, collision map, draw helpers |

### Blend modes

`normal` · `multiply` · `screen` · `overlay` · `addition`/`add` · `darken` · `lighten` · …

### Location styles & themes

- Styles: `linear` · `ascent` · `arena` · `pit`
- Themes: `castle` · `cave` · `forest` · `dungeon` · `rooftop`
- Times: `dawn` · `day` · `dusk` · `night` · `magic`

## Platformer stage (minimal)

```python
loc = make_platformer_room(name="intro", theme="castle", style="ascent", platforms=5, seed=7)
s, loc = build_platformer_stage(Sprite, loc)
for i in range(7):
    if i: s.add_frame(120)
    # copy world/props into new frames if animating lamps…
setup = platformer_default_lights(loc.width, loc.height, loc.ground_y, "night", loc.windows, loc.lamps)
stamp_lighting(s, setup, 0)
s.preview_gif("stage.gif", scale=2); s.save("stage.aseprite")
```

## Quality bar

- Silhouette reads at 1x with FX off
- Platforms snapped to tile grid; collision exported
- Animations use curves (stable foot pivot, no volume swimming)
- Lights on `screen`/`addition`; mood wash on `multiply`
- ≥2 preview passes before delivery

---
name: aseprite-pixel-art
description: Create pixel-art for platformer games and general retro art as real .aseprite files (pure Python, no Aseprite app). Generates game-ready locations/stages (platforms, tilemap, collision, spawn validation), character animations (idle/run/jump/land/attack), diffused lighting + soft atmosphere (clouds, mist, volumetric water, leaves), and logic-driven lights (point/shaft/spot + time-of-day). Blend modes (addition/screen/multiply) composite correctly in previews. Use when the user asks for pixel art, platformer stages, levels, rooms, tilesets, environments, backgrounds, locations, walk/run/jump cycles, sprite animation, lighting, glow, lamps, god-rays, particles, clouds, water, leaves, or game-ready .aseprite assets.
---

# Aseprite Pixel Art — Platformer Ready

Layered `.aseprite` authoring in Python. Previews simulate **real blend modes**. Oriented for **pixel platformers**: location gen, animation curves, lighting + atmosphere.

Deps: `pip install pillow`

## Core workflow

1. **Brief** — platformer stage vs character vs prop; tile size; theme; time-of-day.
2. **Generate logic** — `location_gen` / `anim_helpers` / `lighting_logic` / `atmosphere` (don't hand-wave layouts).
3. **Build script** — draw from those specs into `aseprite_io.Sprite`.
4. **Export** — `.aseprite` + `loc.export_game()` JSON (collision, tilemap, spawn, validation).
5. **Preview** — `preview` / `preview_gif`; fix; deliver.

### Read when…

| Task | Reference |
|---|---|
| Platformer stages, tiles, collision, themes | [references/platformer-guide.md](references/platformer-guide.md) |
| Interiors / scenes / parallax | [references/environments-and-scenes-guide.md](references/environments-and-scenes-guide.md) |
| Glow, particles, blend modes, atmosphere | [references/lighting-and-particles-guide.md](references/lighting-and-particles-guide.md) |

## API cheat-sheet

```python
import sys
from pathlib import Path
SKILL = Path("…/.cursor/skills/aseprite-pixel-art")
sys.path.insert(0, str(SKILL / "scripts"))

from aseprite_io import Sprite, load_aseprite
from fx_helpers import walk_cycle, wave_curve, radial_glow, flicker, ember_trail, apply_glow
from anim_helpers import idle_breath, run_cycle, jump_arc, land_squash, attack_swing, anim_tag_plan, pose_for
from lighting_logic import LightingSetup, platformer_default_lights, stamp_lighting, stamp_diffused, apply_time_of_day
from atmosphere import soft_sky_pixels, drifting_clouds_frame, stamp_water, falling_leaves_frame, leaf_litter_pixels
from location_gen import make_platformer_room, build_platformer_stage, theme_colors, ensure_game_ready

# —— Game-ready stage ——
loc = make_platformer_room(theme="autumn_forest", style="linear", width=320, height=176, seed=2, game_ready=True)
s, loc = build_platformer_stage(Sprite, loc)
setup = platformer_default_lights(loc.width, loc.height, loc.ground_y, "dusk", loc.windows, loc.lamps, diffused=True)
stamp_diffused(s, color=(255, 200, 150), strength=0.35, frame=0)
stamp_lighting(s, setup, frame=0)
json.dump(loc.export_game(), open("stage.json", "w"), indent=2)  # tilemap + collision + spawn
s.save("stage.aseprite")

# —— Atmosphere ——
s.stamp(soft_sky_pixels(W, H, top, bot, haze=haze), layer="far")
s.stamp(drifting_clouds_frame(W, H, f, 8, layer="fg"), layer="clouds_fg")
stamp_water(s, x, y, w, h, pal["water"], frame=f)
s.stamp(falling_leaves_frame(W, H, f, colors=pal["leaf"]), layer="leaves")
```

### Modules

| Module | Role |
|---|---|
| `aseprite_io.py` | Sprite R/W, layers, blend-aware `composite_frame` |
| `fx_helpers.py` | glow, flicker, particles, walk/wave curves |
| `anim_helpers.py` | idle/run/jump/land/attack + `anim_tag_plan` |
| `lighting_logic.py` | lights, time-of-day, `stamp_diffused`, shafts/points |
| `atmosphere.py` | soft BG, clouds, volumetric water, leaf volume |
| `location_gen.py` | rooms, themes, tilemap, `export_game()`, validation |

### Blend modes

`normal` · `multiply` · `screen` · `overlay` · `addition`/`add` · `darken` · `lighten` · …

### Location styles & themes

- Styles: `linear` · `ascent` · `arena` · `pit`
- Themes: `castle` · `cave` · `forest` · `autumn_forest` · `dungeon` · `rooftop`
- Times: `dawn` · `day` · `dusk` · `night` · `magic`

## Game-ready export

`loc.export_game()` returns:

- `collision` — AABB list (`solid` / `one_way` / `hazard` / `climb` / `kill`)
- `tilemap` — grid codes for engines
- `spawn` — feet position + player size
- `checkpoints`, `exits`, `camera`, `physics` (jump height/gap)
- `validation` — spawn clearance + hard-gap warnings

Generators respect `PlatformerPhysics.jump_height` / `jump_gap` so platforms stay reachable.

## Quality bar

- Silhouette reads at 1x with FX off
- Platforms snapped to tile grid; `export_game()` validation `ok`
- Soft diffused fill + optional shafts (not only hard god-rays)
- Water has surface + depth + caustics; leaves have highlight/mid/shadow
- FG/BG clouds on separate scroll layers
- Animations use curves (stable foot pivot, no volume swimming)
- ≥2 preview passes before delivery

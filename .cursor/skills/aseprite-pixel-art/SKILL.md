---
name: aseprite-pixel-art
description: Create game-ready pixel art as real .aseprite files (pure Python, no Aseprite app). Platformer stages with Maglione-style layer roles (foreground/main/close-bg/parallax), collision/tilemap export, diffused lighting and atmosphere (clouds, volumetric water, leaves). Side-view animation with Slynyrd keyframe/energy timing (3/4/6/8-frame runs). Top-down 3/4 character animation (4- or 8-dir, variable bob, flip economy). Use for pixel art, platformer levels, tilesets, environments, walk/run/jump cycles, top-down RPG characters, glow, particles, god-rays, or .aseprite delivery.
---

# Aseprite Pixel Art — Game Ready

Layered `.aseprite` authoring in Python with blend-accurate previews. Built for **platformers** and **top-down** characters.

Deps: `pip install pillow`

## Influences (read these)

| Topic | Source |
|---|---|
| Keyframes, run economy, energy vs smoothness | [Slynyrd Pixelblog 8 — Intro to Animation](https://www.slynyrd.com/blog/2018/8/19/pixelblog-8-intro-to-animation) |
| FG / main / close-bg / parallax level layers | [Sandro Maglione — Platformer Level Design](https://www.sandromaglione.com/articles/pixel-art-platformer-level-design-full-guide) |
| 8-dir top-down, variable bob, flip economy | [Slynyrd Pixelblog 55 — Top Down Character Animation](https://www.slynyrd.com/blog/2025/3/24/pixelblog-55-top-down-character-animation) |

## Core workflow

1. **Brief** — side-view stage vs top-down character vs prop; tile size; theme
2. **Logic first** — `location_gen` / `anim_helpers` / `topdown_anim` / `lighting_logic` / `atmosphere`
3. **Build script** — stamp into `aseprite_io.Sprite`
4. **Export** — `.aseprite` + `loc.export_game()` JSON when it's a stage
5. **Preview** — fix clusters; respect keyframes; confirm `validation.ok`

### Read when…

| Task | Reference |
|---|---|
| Side-view idle/run keyframes & timing | [references/animation-guide.md](references/animation-guide.md) |
| Top-down 4/8-dir characters | [references/topdown-character-guide.md](references/topdown-character-guide.md) |
| Platformer layers, tiles, collision | [references/platformer-guide.md](references/platformer-guide.md) |
| Scenes / parallax | [references/environments-and-scenes-guide.md](references/environments-and-scenes-guide.md) |
| Glow, particles, diffused light, water | [references/lighting-and-particles-guide.md](references/lighting-and-particles-guide.md) |

## API cheat-sheet

```python
import sys
from pathlib import Path
SKILL = Path("…/aseprite-pixel-art")  # or this repo root
sys.path.insert(0, str(SKILL / "scripts"))

from aseprite_io import Sprite
from anim_helpers import run_cycle, idle_breath, anim_tag_plan, economize_run_frames
from topdown_anim import TopDownProfile, topdown_run, topdown_sheet_plan, authoring_directions
from lighting_logic import platformer_default_lights, stamp_lighting, stamp_diffused
from atmosphere import soft_sky_pixels, stamp_water, drifting_clouds_frame, falling_leaves_frame
from location_gen import make_platformer_room, build_platformer_stage, platformer_layer_stack

# Stage (Maglione layers + game export)
loc = make_platformer_room(theme="autumn_forest", style="linear", game_ready=True)
s, loc = build_platformer_stage(Sprite, loc)
stamp_diffused(s, strength=0.4, frame=0)
stamp_lighting(s, platformer_default_lights(loc.width, loc.height, loc.ground_y, "dusk",
                                            loc.windows, loc.lamps, diffused=True), 0)
loc.export_game()  # tilemap + collision + spawn + validation

# Side-view run — 6 frames, energy timing (Pixelblog 8)
pose = run_cycle(f, frames=6, variable_bob=True)
plan = anim_tag_plan(["idle", "run", "jump"])  # run defaults to 6

# Top-down sheet (Pixelblog 55)
profile = TopDownProfile(width=26, height=32, directions=8, run_frames=6)
sheet = topdown_sheet_plan(profile)
run = topdown_run(f, direction="SE")
```

### Modules

| Module | Role |
|---|---|
| `aseprite_io.py` | Sprite R/W, blend-aware composite |
| `anim_helpers.py` | Side-view curves, keyframe economy, hold timing |
| `topdown_anim.py` | 4/8-dir top-down idle/run, flips, sheet plan |
| `fx_helpers.py` | glow, flicker, particles |
| `lighting_logic.py` | lights, `stamp_diffused`, time-of-day |
| `atmosphere.py` | soft BG, clouds, volumetric water, leaves |
| `location_gen.py` | rooms, Maglione layer roles, `export_game()` |

## Quality bar

- Main-layer collidables read with FX off (outline + contrast)
- FG never covers the player silhouette
- Close-bg is not parallaxed; far layers are
- Run keyframes readable alone; prefer 6 frames; scale ms when cutting
- Top-down: sync bob across directions; author 5 + flip when symmetric
- `export_game()["validation"]["ok"]` for stages
- ≥2 preview passes before delivery

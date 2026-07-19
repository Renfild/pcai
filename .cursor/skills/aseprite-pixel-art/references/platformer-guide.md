# Platformer Pixel Art Guide

Use this skill for **side-view platformer** stages, characters, and props — not just showcase scenes.

## Canvas & tile grid

| Role | Typical size | Notes |
|---|---|---|
| Character | 16×16 / 24×24 / 32×32 | Keep pivot on feet center |
| Tiles | 16×16 (or 8×8) | All solids snap to grid |
| Stage chunk | 256–384 wide × 144–224 tall | ≈ one camera view |
| Parallax strip | ≥ camera width × 1.5 | Seamless loop |

Always decide **tile size first**, then place platforms on that grid. Export collision AABBs from `LocationSpec.collision_map()`.

## Location generation workflow

```python
from location_gen import make_platformer_room, build_platformer_stage, theme_colors
from aseprite_io import Sprite
from lighting_logic import platformer_default_lights, stamp_lighting

loc = make_platformer_room(
    name="castle_01", width=320, height=176, tile=16,
    theme="castle",   # castle|cave|forest|dungeon|rooftop
    style="linear",   # linear|ascent|arena|pit
    platforms=6, seed=3,
)
s, loc = build_platformer_stage(Sprite, loc)
# Lighting
setup = platformer_default_lights(
    loc.width, loc.height, loc.ground_y,
    time="dusk", windows=loc.windows, lamps=loc.lamps,
)
s.add_frame(100)  # if animating lights — copy world/props first
stamp_lighting(s, setup, frame=0)
s.save("stage.aseprite")
```

`LocationSpec` includes: solids, one_way ledges, hazards, climbables, player_spawn, exits, props, windows/lamps, parallax scroll hints.

## Layer stack (platformer)

1. `sky` / `far` / `mid` — parallax (scroll 0 / 0.25 / 0.5)
2. `world` — tiles, solids, terrain
3. `props` — torches, banners, doors, chests
4. `entities` — player/enemies (often separate spritesheets)
5. `shade` — multiply time-of-day / AO
6. `beams` — screen shafts
7. `glow` — addition lamps / magic
8. `fx` — dust, sparks

## Character animation

Use `anim_helpers.py` — do **not** hand-tune every frame from scratch:

| Action | Helper | Typical frames | Duration |
|---|---|---|---|
| Idle | `idle_breath` | 4–6 | 100–140ms |
| Run | `run_cycle` | 6–8 | 60–80ms |
| Jump | `jump_arc` | 4–6 | 70–90ms |
| Land | `land_squash` | 2–3 | 60–80ms |
| Attack | `attack_swing` | 4–6 | 50–70ms |

```python
from anim_helpers import anim_tag_plan, pose_for, run_cycle, jump_arc

plan = anim_tag_plan(["idle", "run", "jump", "fall", "land"])
# plan → [{name, from, to, duration_ms}, …] — feed into s.add_tag / set_frame_duration

pose = run_cycle(frame, frames=8, stride=3, bob=1.2)
y = base_y - int(round(pose["body_y"]))  # positive body_y = up
```

Stable **foot pivot** across all frames. Volume must not grow/shrink wildly between run frames.

## Lighting logic

```python
from lighting_logic import LightingSetup, apply_time_of_day, stamp_lighting

setup = LightingSetup(time_of_day="night")
apply_time_of_day(setup)
setup.add_point(80, 60, color=(255, 170, 80), radius=32)
setup.add_shaft(120, 20, aim_deg=100, length=90, cone_deg=28)
stamp_lighting(s, setup, frame=f)
```

Times: `dawn` | `day` | `dusk` | `night` | `magic` — each sets multiply wash color + strength.

Rules:
- Gameplay-critical silhouettes must read with glow layers hidden
- Lamps flicker with stable seeds (reproducible builds)
- One hot addition core + softer screen wash reads better than one flat blob

## Theme checklist

When the user asks for a location, pick a theme and stick to its ramp:

- **castle** — cold stone, red carpet/banners, brass
- **cave** — purple-brown rock, bioluminescent accents
- **forest** — mossy greens, warm shafts through canopy
- **autumn_forest** — dark fantasy autumn: plum bark, rust foliage, violet mist, embers
- **dungeon** — near-black stone, magenta magic lights
- **rooftop** — cool night sky, warm window glow below

## Delivery for a platformer stage

1. `stage.aseprite` (layers + tags)
2. `stage.png` / `stage.gif` preview
3. Print or save `loc.collision_map()` JSON beside the art
4. Keep `build.py` as source of truth

See also: [environments-and-scenes-guide.md](environments-and-scenes-guide.md), [lighting-and-particles-guide.md](lighting-and-particles-guide.md)

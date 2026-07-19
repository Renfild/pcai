# Platformer Pixel Art Guide

Use this skill for **side-view platformer** stages, characters, and props — not just showcase scenes.

## Canvas & tile grid

| Role | Typical size | Notes |
|---|---|---|
| Character | 16×16 / 24×24 / 32×32 | Keep pivot on feet center |
| Tiles | 16×16 (or 8×8) | All solids snap to grid |
| Stage chunk | 256–384 wide × 144–224 tall | ≈ one camera view |
| Parallax strip | ≥ camera width × 1.5 | Seamless loop |

Always decide **tile size first**, then place platforms on that grid. Export with `LocationSpec.export_game()` (preferred) or `collision_map()`.

## Location generation workflow

```python
from location_gen import make_platformer_room, build_platformer_stage, theme_colors, PlatformerPhysics
from aseprite_io import Sprite
from lighting_logic import platformer_default_lights, stamp_lighting, stamp_diffused
from atmosphere import soft_sky_pixels, stamp_water, drifting_clouds_frame, falling_leaves_frame
import json

phys = PlatformerPhysics(tile=16, jump_height=48, jump_gap=64)
loc = make_platformer_room(
    name="castle_01", width=320, height=176, tile=16,
    theme="castle",   # castle|cave|forest|autumn_forest|dungeon|rooftop
    style="linear",   # linear|ascent|arena|pit
    platforms=6, seed=3,
    game_ready=True,  # snap, dedupe, validate, camera, checkpoint
    physics=phys,
)
s, loc = build_platformer_stage(Sprite, loc)
setup = platformer_default_lights(
    loc.width, loc.height, loc.ground_y,
    time="dusk", windows=loc.windows, lamps=loc.lamps, diffused=True,
)
stamp_diffused(s, color=(255, 210, 160), strength=0.35, frame=0)
stamp_lighting(s, setup, frame=0)
json.dump(loc.export_game(), open("stage.json", "w"), indent=2)
s.save("stage.aseprite")
```

`LocationSpec` includes: solids, one_way, hazards, kill_zones, climbables, player_spawn, checkpoints, exits, props, windows/lamps, parallax, camera, physics.

### Game-ready rules

1. **Snap** — `ensure_game_ready()` / `snap_all()` align gameplay geometry to the tile grid.
2. **Reachability** — generators keep horizontal gaps ≤ `jump_gap` and rises ≤ `jump_height`.
3. **Spawn** — feet on a platform top; body clearance checked in `validate_layout()`.
4. **Export** — `export_game()` → collision AABBs + tilemap grid + spawn/camera/physics + validation report.
5. **Kill zones** — pits should include a `kill` strip (void/lava) under the hazard water/spikes.

Tilemap codes: `0` empty · `1` solid · `2` one_way · `3` hazard · `4` climb · `5` kill.

## Layer stack (platformer)

1. `far` / `sky` — soft gradient + distant silhouette (scroll ~0.2)
2. `world` — tiles, solids, terrain, water body
3. `mid` — leaf litter, water surface, mid canopy
4. `props` — torches, doors, chests, vines
5. `near` — overhang leaves / FG props (scroll ~1.25)
6. `shade` — multiply time-of-day / AO
7. `beams` — screen diffused fill + soft shafts + BG clouds
8. `glow` — addition lamps / caustics / magic
9. `leaves` / `clouds_fg` — falling leaves, foreground fog

## Atmosphere (soft BG, clouds, water, leaves)

```python
from atmosphere import soft_sky_pixels, soft_silhouette_band, stamp_water
from atmosphere import drifting_clouds_frame, falling_leaves_frame, leaf_litter_pixels

s.stamp(soft_sky_pixels(W, H, top, bottom, haze=haze), layer="far")
s.stamp(soft_silhouette_band(W, horizon_y=60, color=(20, 16, 28, 140)), layer="far")
stamp_water(s, pit.x, pit.y, pit.w, pit.h, pal["water"], frame=f)  # volume + foam + caustics
s.stamp(drifting_clouds_frame(W, H, f, layer="fg"), layer="clouds_fg")
s.stamp(falling_leaves_frame(W, H, f, colors=pal["leaf"]), layer="leaves")
s.stamp(leaf_litter_pixels(plat.x, plat.y, plat.w, pal["leaf"]), layer="mid")
```

Prefer **diffused fill** (`stamp_diffused`) as the base mood light; add shafts for canopy gaps, not as the only light.

## Character animation

Use `anim_helpers.py` — do **not** hand-tune every frame from scratch:

| Action | Helper | Typical frames | Duration |
|---|---|---|---|
| Idle | `idle_breath` | 4–6 | 100–140ms |
| Run | `run_cycle` | 6–8 | 60–80ms |
| Jump | `jump_arc` | 4–6 | 70–90ms |
| Land | `land_squash` | 2–3 | 60–80ms |
| Attack | `attack_swing` | 4–6 | 50–70ms |

Stable **foot pivot** across all frames. Volume must not grow/shrink wildly between run frames.

## Lighting logic

```python
from lighting_logic import LightingSetup, apply_time_of_day, stamp_lighting, stamp_diffused

setup = LightingSetup(time_of_day="night")
apply_time_of_day(setup)
setup.add_point(80, 60, color=(255, 170, 80), radius=32)
setup.add_shaft(120, 20, aim_deg=100, length=90, cone_deg=34)  # wider = softer
stamp_diffused(s, color=(255, 200, 150), strength=0.35, frame=f)
stamp_lighting(s, setup, frame=f)
```

Times: `dawn` | `day` | `dusk` | `night` | `magic`.

Rules:
- Gameplay-critical silhouettes must read with glow layers hidden
- Lamps flicker with stable seeds (reproducible builds)
- Diffused screen fill + soft bounce before hard shafts

## Theme checklist

- **castle** — cold stone, red carpet/banners, brass
- **cave** — purple-brown rock, bioluminescent accents
- **forest** — mossy greens, warm shafts through canopy
- **autumn_forest** — dark fantasy autumn: plum bark, rust foliage, violet mist, embers, volumetric creek
- **dungeon** — near-black stone, magenta magic lights
- **rooftop** — cool night sky, warm window glow below

## Delivery for a platformer stage

1. `stage.aseprite` (layers + tags)
2. `stage.png` / `stage.gif` preview
3. `stage.json` from `loc.export_game()` (collision + tilemap + spawn + validation)
4. Keep `build.py` as source of truth
5. Confirm `validation.ok` is true (or document remaining hard gaps)

See also: [environments-and-scenes-guide.md](environments-and-scenes-guide.md), [lighting-and-particles-guide.md](lighting-and-particles-guide.md)

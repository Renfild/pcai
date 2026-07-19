# aseprskill

Cursor skill for **game-ready pixel art** as real `.aseprite` files (pure Python, Pillow — no Aseprite app required).

## Install

```bash
# Option A — clone into your project's skill folder
mkdir -p .cursor/skills
git clone https://github.com/Renfild/aseprskill.git .cursor/skills/aseprite-pixel-art

# Option B — copy this repo (SKILL.md at root) into:
#   .cursor/skills/aseprite-pixel-art/
```

Or unpack `aseprite-pixel-art.skill` from `.cursor/skills/` after running:

```bash
python3 scripts/package_skill.py
```

Deps: `pip install pillow`

## What it does

- **Platformer stages** — Maglione-style layers (foreground / main / close-bg / parallax), collision + tilemap export, jump validation
- **Atmosphere** — diffused light, soft sky, FG/BG clouds, volumetric water, leaf volume
- **Side-view animation** — Slynyrd keyframe economy (3/4/6/8-frame runs), energy-preserving timing
- **Top-down characters** — 4- or 8-dir, variable bob, flip economy, sheet planning

## Guides baked in

| Topic | Source |
|---|---|
| Keyframes & run energy | [Slynyrd Pixelblog 8](https://www.slynyrd.com/blog/2018/8/19/pixelblog-8-intro-to-animation) |
| Level layer roles | [Sandro Maglione — Platformer Level Design](https://www.sandromaglione.com/articles/pixel-art-platformer-level-design-full-guide) |
| Top-down 8-dir animation | [Slynyrd Pixelblog 55](https://www.slynyrd.com/blog/2025/3/24/pixelblog-55-top-down-character-animation) |

See `SKILL.md` and `references/`.

## Quick test

```bash
python3 examples/test_platformer_modules.py
python3 examples/test_regression.py
```

## Layout

```
SKILL.md          # Cursor skill entry
scripts/          # aseprite_io, location_gen, anim_helpers, topdown_anim, …
references/       # animation, platformer, top-down, lighting guides
examples/         # demos + tests
.cursor/skills/aseprite-pixel-art/  # drop-in mirror for Cursor
```

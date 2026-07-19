#!/usr/bin/env python3
"""Platformer stage demo — location_gen + lighting_logic + ambient lamp flicker."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from aseprite_io import Cel, Sprite
from location_gen import make_platformer_room, build_platformer_stage
from lighting_logic import platformer_default_lights, stamp_lighting

OUT = ROOT / "examples" / "out"
OUT.mkdir(parents=True, exist_ok=True)
FRAMES = 6


def main() -> None:
    loc = make_platformer_room(
        name="castle_ramparts",
        width=320,
        height=176,
        tile=16,
        theme="castle",
        style="linear",
        platforms=6,
        seed=11,
    )
    s, loc = build_platformer_stage(Sprite, loc)

    # Extra frames for flickering lamps
    for i in range(1, FRAMES):
        s.add_frame(110)
        for name in ("world", "props", "shade"):
            layer = s._resolve_layer(name)
            src = layer.cels[0]
            if src:
                layer.cels[i] = Cel(x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels))

    setup = platformer_default_lights(
        loc.width, loc.height, loc.ground_y,
        time="dusk",
        windows=loc.windows or [(160, 40)],
        lamps=loc.lamps,
    )
    for f in range(FRAMES):
        for fx in ("shade", "beams", "glow"):
            s.ensure_cel(fx, f).clear()
        stamp_lighting(s, setup, frame=f, stamp_shade=(f == 0))
        # Reuse frame-0 shade on later frames
        if f > 0:
            src = s._resolve_layer("shade").cels[0]
            if src:
                s._resolve_layer("shade").cels[f] = Cel(
                    x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels)
                )
        s.set_frame_duration(f, 110)

    s.add_tag("ambient", 0, FRAMES - 1, direction="pingpong")
    ase = s.save(OUT / "platformer_stage.aseprite")
    png = s.preview(OUT / "platformer_stage.png", scale=2, frame=0)
    order = list(range(FRAMES)) + list(range(FRAMES - 2, 0, -1))
    gif = s.preview_gif(OUT / "platformer_stage.gif", scale=2, frames=order)

    coll = loc.collision_map()
    (OUT / "platformer_stage_collision.json").write_text(
        __import__("json").dumps({"spawn": loc.player_spawn, "exits": loc.exits, "collision": coll}, indent=2)
    )
    print(f"saved {ase}")
    print(f"saved {png}")
    print(f"saved {gif}")
    print(f"theme={loc.theme} solids={len(loc.solids)} one_way={len(loc.one_way)} props={len(loc.props)}")
    print(f"lights windows={len(loc.windows)} lamps={len(loc.lamps)} collision_boxes={len(coll)}")


if __name__ == "__main__":
    main()

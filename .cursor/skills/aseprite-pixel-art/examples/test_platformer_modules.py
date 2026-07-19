#!/usr/bin/env python3
"""Quick tests for anim_helpers, lighting_logic, location_gen."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from aseprite_io import Sprite
from anim_helpers import idle_breath, run_cycle, jump_arc, land_squash, anim_tag_plan, pose_for
from lighting_logic import LightingSetup, bake_lights, apply_time_of_day, platformer_default_lights
from location_gen import make_platformer_room, build_platformer_stage


def test_anim() -> None:
    idle = idle_breath(0, frames=6)
    assert "body_y" in idle
    run = [run_cycle(i, frames=8) for i in range(8)]
    assert max(r["body_y"] for r in run) > min(r["body_y"] for r in run)
    passing = [r["body_y"] for r in run if r["phase"] == "passing"]
    assert max(passing) == max(r["body_y"] for r in run)
    j = jump_arc(2, frames=6, height=8)
    assert j["body_y"] > 0
    land_squash(0, frames=3)
    plan = anim_tag_plan(["idle", "run", "jump"])
    assert plan[0]["from"] == 0 and plan[-1]["to"] >= 2
    assert pose_for("run", 3)["phase"] in ("contact", "down", "passing", "up")
    print("OK anim_helpers")


def test_lighting() -> None:
    setup = LightingSetup(time_of_day="night")
    apply_time_of_day(setup)
    setup.add_point(40, 40, radius=20)
    setup.add_shaft(60, 10, length=50, cone_deg=30)
    layers = bake_lights(setup, 96, 64, frame=0)
    assert layers["shade"] and layers["glow"]
    assert len(layers["beams"]) > 10
    a = bake_lights(setup, 96, 64, 0)
    b = bake_lights(setup, 96, 64, 3)
    assert a["glow"] != b["glow"]
    print("OK lighting_logic", f"glow0={len(a['glow'])} glow3={len(b['glow'])}")


def test_location() -> None:
    loc = make_platformer_room(theme="cave", style="ascent", seed=5, platforms=5)
    assert loc.solids and loc.ground_y > 0
    coll = loc.collision_map()
    assert any(c["type"] == "solid" for c in coll)
    s, loc2 = build_platformer_stage(Sprite, loc)
    assert s.width == loc.width
    img = s.composite_frame(0)
    assert img.size == (loc.width, loc.height)
    setup = platformer_default_lights(loc.width, loc.height, loc.ground_y, "night", loc.windows, loc.lamps)
    layers = bake_lights(setup, loc.width, loc.height, 0)
    assert layers["shade"]
    print("OK location_gen", loc.theme, f"solids={len(loc.solids)} coll={len(coll)}")


def main() -> None:
    test_anim()
    test_lighting()
    test_location()
    print("\nAll platformer module tests passed.")


if __name__ == "__main__":
    main()

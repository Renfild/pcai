#!/usr/bin/env python3
"""Quick tests for anim_helpers, lighting_logic, location_gen."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from aseprite_io import Sprite
from anim_helpers import (
    idle_breath, run_cycle, jump_arc, land_squash, anim_tag_plan, pose_for,
    economize_run_frames, frame_duration_ms, run_keyframe_guide,
)
from atmosphere import (
    soft_sky_pixels, cloud_pixels, water_volume_pixels,
    leaf_cluster_pixels, falling_leaves_frame, diffused_fill_pixels,
)
from lighting_logic import (
    LightingSetup, bake_lights, apply_time_of_day, platformer_default_lights,
    diffused_ambient_pixels, stamp_diffused,
)
from location_gen import (
    make_platformer_room, build_platformer_stage, ensure_game_ready, validate_layout,
    platformer_layer_stack,
)
from topdown_anim import (
    TopDownProfile, topdown_run, topdown_idle, authoring_directions,
    resolve_orientation, topdown_sheet_plan, facing_from_velocity, sync_check_bobs,
)


def test_anim() -> None:
    idle = idle_breath(0, frames=6, hold_extremes=True)
    assert "body_y" in idle and "durations_ms" in idle
    run = [run_cycle(i, frames=6, variable_bob=True) for i in range(6)]
    assert max(r["body_y"] for r in run) > min(r["body_y"] for r in run)
    assert run_cycle(0, frames=3)["phase"] in ("stride", "pass")
    assert frame_duration_ms(4) == 160
    assert economize_run_frames(8, 6) == [0, 2, 3, 4, 6, 7]
    assert len(run_keyframe_guide(6)) == 6
    j = jump_arc(2, frames=6, height=8)
    assert j["body_y"] > 0
    land_squash(0, frames=3)
    plan = anim_tag_plan(["idle", "run", "jump"])
    assert plan[0]["from"] == 0 and plan[1]["frames"] == 6
    assert pose_for("run", 3, frames=6)["phase"] in (
        "contact", "down", "passing", "up", "stride", "pass",
    )
    print("OK anim_helpers")


def test_topdown() -> None:
    assert authoring_directions(8) == ["N", "NE", "E", "SE", "S"]
    src, flip = resolve_orientation("NW")
    assert src == "NE" and flip is True
    assert facing_from_velocity(1, 0, 8) == "E"
    pose = topdown_run(2, frames=6, direction="SE")
    assert pose["flip_x"] is False and pose["source_direction"] == "SE"
    idle = topdown_idle(1, direction="W")
    assert idle["flip_x"] is True
    sheet = topdown_sheet_plan(TopDownProfile())
    assert sheet["profile"]["footprint"] == [2, 2]
    bobs = {
        "S": [topdown_run(i, direction="S") for i in range(6)],
        "E": [topdown_run(i, direction="E") for i in range(6)],
    }
    assert sync_check_bobs(bobs) == []
    print("OK topdown_anim", sheet["authoring_directions"])


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
    loc = make_platformer_room(theme="cave", style="ascent", seed=5, platforms=5, game_ready=True)
    assert loc.solids and loc.ground_y > 0
    coll = loc.collision_map()
    assert any(c["type"] == "solid" for c in coll)
    game = loc.export_game()
    assert "tilemap" in game and "spawn" in game and "validation" in game
    assert game["tilemap"]["cols"] == loc.width // loc.tile
    stack = platformer_layer_stack()
    assert any(l["name"] == "close_bg" for l in stack)
    assert any(l["name"] == "world" and l.get("outline") for l in stack)
    s, loc2 = build_platformer_stage(Sprite, loc)
    assert s.width == loc.width
    names = [L.name for L in s.layers]
    assert "close_bg" in names and "world" in names
    img = s.composite_frame(0)
    assert img.size == (loc.width, loc.height)
    setup = platformer_default_lights(loc.width, loc.height, loc.ground_y, "night", loc.windows, loc.lamps)
    layers = bake_lights(setup, loc.width, loc.height, 0)
    assert layers["shade"]
    print("OK location_gen", loc.theme, f"solids={len(loc.solids)} coll={len(coll)} ok={game['validation']['ok']}")


def test_atmosphere() -> None:
    sky = soft_sky_pixels(64, 48, (20, 16, 30, 255), (40, 30, 50, 255), haze=(60, 40, 80, 255))
    assert len(sky) == 64 * 48
    clouds = cloud_pixels(32, 20, scale=1.0, seed=1)
    assert len(clouds) > 20
    water = water_volume_pixels(10, 30, 24, 16, [(20, 28, 48, 255), (36, 50, 80, 255), (60, 90, 120, 255)], frame=2)
    assert water["body"] and water["surface"] and water["glow"]
    leaves = leaf_cluster_pixels(40, 20, [(140, 40, 36, 255), (190, 70, 40, 255), (220, 130, 50, 255)], radius=8, count=12)
    assert len(leaves) > 20
    fall = falling_leaves_frame(80, 60, 3, 8, count=10)
    assert len(fall) > 10
    diff = diffused_fill_pixels(48, 32, strength=0.4, seed=2)
    assert len(diff) > 50
    amb = diffused_ambient_pixels(48, 32, strength=0.35)
    assert len(amb) > 50
    s = Sprite(48, 32)
    s.add_layer("beams", blend_mode="screen")
    stamp_diffused(s, strength=0.3, frame=0)
    print("OK atmosphere", f"sky={len(sky)} water_glow={len(water['glow'])} fall={len(fall)}")


def test_game_ready_gaps() -> None:
    loc = make_platformer_room(theme="forest", style="linear", seed=2, platforms=6, game_ready=True)
    v = validate_layout(loc)
    assert "hard_gaps" in v
    assert loc.physics is not None
    ensure_game_ready(loc)
    print("OK game_ready", f"warnings={len(v['warnings'])} platforms={v['platform_count']}")


def main() -> None:
    test_anim()
    test_topdown()
    test_lighting()
    test_location()
    test_atmosphere()
    test_game_ready_gaps()
    print("\nAll platformer module tests passed.")


if __name__ == "__main__":
    main()

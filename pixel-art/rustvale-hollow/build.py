#!/usr/bin/env python3
"""Rustvale Hollow — rebuilt with proper pixel craft.

Fixes:
  - Terraria-style parallax stack (sky / bg_far / bg_mid / bg_near / close_bg / world / fg)
  - Multi-layer platforms (body + lip + leaf heaps + underside)
  - Water: banded volume, soft surface (no hatch lines)
  - Clouds/leaves: one-way travel, despawn off-screen, respawn (no wrap)
  - Lighting: soft shafts, tiny lamp flicker (no lighting curves)
  - Ambient tag: forward 12 frames (not pingpong) so weather doesn't reverse
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / ".cursor" / "skills" / "aseprite-pixel-art"
sys.path.insert(0, str(SKILL / "scripts"))

from aseprite_io import Cel, Sprite
from atmosphere import soft_silhouette_band, soft_sky_pixels
from lighting_logic import LightingSetup, apply_time_of_day, stamp_diffused, stamp_lighting
from location_gen import (
    LocationSpec, PlatformerPhysics, Prop, Rect,
    ensure_game_ready, make_platformer_room, theme_colors,
)
from loop_fx import (
    PARALLAX_STACK, bake_drift_frames, make_cloud_field, make_leaf_field,
    stamp_platform, stamp_water,
)
from atmosphere import leaf_cluster_pixels

OUT = Path(__file__).resolve().parent
W, H, TILE = 320, 176, 16
FRAMES = 12  # smoother ambient; forward-only tag


def put(s, x, y, c, layer, frame=0):
    if 0 <= x < s.width and 0 <= y < s.height:
        s.put_pixel(x, y, c, layer=layer, frame=frame)


def build_layout(seed: int = 27) -> LocationSpec:
    phys = PlatformerPhysics(tile=TILE, jump_height=48, jump_gap=56)
    loc = make_platformer_room(
        name="rustvale_hollow", width=W, height=H, tile=TILE,
        theme="autumn_forest", style="ascent", platforms=0, seed=seed,
        game_ready=False, physics=phys,
    )
    loc.solids = [r for r in loc.solids if r.y == 0 or r.x == 0 or r.x >= W - TILE]
    loc.one_way.clear(); loc.hazards.clear(); loc.kill_zones.clear()
    loc.props.clear(); loc.windows.clear(); loc.lamps.clear()
    loc.exits.clear(); loc.climbables.clear(); loc.checkpoints.clear()

    t, gy = TILE, loc.ground_y
    pit = Rect(t * 7, gy, t * 4, H - gy)
    loc.hazards.append(pit)
    loc.kill_zones.append(Rect(pit.x, H - t, pit.w, t))
    loc.solids.append(Rect(t, gy, pit.x - t, H - gy))
    loc.solids.append(Rect(pit.x + pit.w, gy, W - t - (pit.x + pit.w), H - gy))
    loc.solids.append(Rect(pit.x - t // 2, gy - t + 2, pit.w + t, 8))

    ledges = [
        (t * 2, gy - t * 2, t * 3, True, "dirt"),
        (t * 5, gy - t * 3, t * 2, False, "dirt"),
        (t * 11, gy - t * 2, t * 3, True, "stone"),
        (t * 14, gy - t * 3, t * 2, False, "dirt"),
        (t * 10, gy - t * 5, t * 3, True, "dirt"),
        (t * 3, gy - t * 5, t * 2, False, "dirt"),
        (t * 13, gy - t * 6, t * 3, True, "stone"),
        (t * 6, gy - t * 7, t * 2, False, "dirt"),
        (t * 9, gy - t * 8, t * 3, True, "dirt"),
    ]
    loc._ledge_meta = []  # type: ignore
    for x, y, w, solid, style in ledges:
        h = t if solid else t // 2 + 2
        r = Rect(x, y, w, h)
        (loc.solids if solid else loc.one_way).append(r)
        loc._ledge_meta.append((r, style, solid))  # type: ignore

    loc.windows = [(64, 24), (150, 20), (230, 26)]
    loc.lamps = [(40, gy - t * 2 - 10), (t * 11 + 12, gy - t * 2 - 10),
                 (t * 13 + 10, gy - t * 6 - 10), (280, gy - 20)]
    loc.props = [
        Prop("torch", loc.lamps[0][0], loc.lamps[0][1] + 6, {"kind": "ember"}),
        Prop("torch", loc.lamps[1][0], loc.lamps[1][1] + 6, {"kind": "ember"}),
        Prop("torch", loc.lamps[2][0], loc.lamps[2][1] + 6, {"kind": "ember"}),
        Prop("torch", loc.lamps[3][0], loc.lamps[3][1] + 6, {"kind": "ember"}),
        Prop("chest", t * 9 + 8, gy - t * 8, {}),
        Prop("door", W - t * 2, gy - t * 2, {"exit": "east"}),
        Prop("decor", 72, gy - 2, {"kind": "mushroom"}),
        Prop("decor", 248, gy - 2, {"kind": "mushroom"}),
        Prop("checkpoint", t * 2 + 8, gy - t * 2, {}),
    ]
    loc.player_spawn = (t * 2 + 8, gy - t * 2)
    loc.checkpoints = [(t * 2 + 8, gy - t * 2), (t * 10 + 8, gy - t * 5)]
    loc.exits.append({"name": "east", "x": W - t * 2, "y": gy - t * 2, "w": t, "h": t * 2, "target": "next"})
    loc.climbables.append(Rect(t * 8, gy - t * 7, 6, t * 5))
    loc.parallax = list(PARALLAX_STACK)
    return ensure_game_ready(loc, phys)


def draw_parallax(s: Sprite, pal: dict, loc: LocationSpec) -> None:
    bg = pal["bg"]
    haze = pal.get("haze", [(90, 60, 110, 255)])[0]
    # sky — static
    s.stamp(soft_sky_pixels(W, H, (34, 24, 54, 255), bg[-1], haze=haze, haze_y=0.38, haze_width=0.4),
            layer="sky", frame=0)
    # bg_far — scroll 0.15 — few-color silhouettes
    s.stamp(soft_silhouette_band(W, H // 3 + 8, (26, 18, 40, 150), height=40, seed=2, blobs=10),
            layer="bg_far", frame=0)
    rng = random.Random(4)
    for i in range(8):
        tx = 20 + i * 40 + rng.randint(-3, 3)
        for y in range(H // 3 - 30, H // 3 + 6):
            put(s, tx, y, (32, 22, 44, 160), "bg_far")
    # bg_mid — scroll 0.35 — richer distant trees
    for i, (cx, h) in enumerate(((45, 55), (120, 65), (200, 50), (275, 60))):
        bark = (50, 32, 48, 200)
        for y in range(loc.ground_y - h, loc.ground_y - 10):
            put(s, cx, y, bark, "bg_mid")
            put(s, cx + 1, y, bark, "bg_mid")
        s.stamp(leaf_cluster_pixels(cx, loc.ground_y - h + 8, pal["leaf"], radius=9, count=14, seed=20 + i),
                layer="bg_mid", frame=0)
    # bg_near — scroll 0.65 — larger trunks, still no hard outline
    for i, (cx, h, lean) in enumerate(((90, 75, -1), (210, 80, 1))):
        for y in range(loc.ground_y - h, loc.ground_y - 4):
            t = (y - (loc.ground_y - h)) / h
            half = 2 + int(t * 2)
            xoff = int(lean * (1 - t))
            for dx in range(-half, half + 1):
                put(s, cx + dx + xoff, y, (62, 40, 52, 230), "bg_near")
        s.stamp(leaf_cluster_pixels(cx, loc.ground_y - h + 6, pal["leaf"], radius=11, count=18, seed=40 + i),
                layer="bg_near", frame=0)
    # close_bg — scroll 1.0 — atmosphere trees behind play (no outline)
    for i, (cx, h) in enumerate(((55, 70), (165, 78), (255, 72))):
        soft_leaf = [(min(255, c[0] + 18), min(255, c[1] + 10), min(255, c[2] + 5), 210) for c in pal["leaf"]]
        for y in range(loc.ground_y - h, loc.ground_y - 2):
            put(s, cx, y, (70, 48, 58, 240), "close_bg")
            put(s, cx + 1, y, (80, 54, 64, 240), "close_bg")
        s.stamp(leaf_cluster_pixels(cx, loc.ground_y - h + 5, soft_leaf, radius=10, count=16, seed=60 + i),
                layer="close_bg", frame=0)


def draw_world(s: Sprite, loc: LocationSpec, pal: dict) -> None:
    stone, leaf = pal["stone"], pal["leaf"]
    gy = loc.ground_y
    # Ground floors
    for r in loc.solids:
        if r.y >= gy:
            stamp_platform(s, r.x, r.y, r.w, r.h, stone, surface=leaf, style="dirt", seed=r.x)
        elif r.y == 0 or r.x == 0 or r.x >= W - TILE:
            stamp_platform(s, r.x, r.y, r.w, min(r.h, H - r.y), stone, style="stone", seed=r.x + r.y)

    # Bridge + ledges with varied styles
    meta = getattr(loc, "_ledge_meta", [])
    bridge = [r for r in loc.solids if r.h <= 10 and r.y < gy and r.w > TILE]
    for r in bridge:
        stamp_platform(s, r.x, r.y, r.w, r.h, stone, surface=leaf, style="wood", seed=r.x)

    drawn = set()
    for r, style, solid in meta:
        stamp_platform(s, r.x, r.y, r.w, r.h, stone, surface=leaf if not solid or style == "dirt" else None,
                       style=style, seed=r.x + r.y)
        drawn.add((r.x, r.y, r.w, r.h))
    for r in loc.one_way:
        if (r.x, r.y, r.w, r.h) not in drawn:
            stamp_platform(s, r.x, r.y, r.w, r.h, stone, surface=leaf, style="dirt", seed=r.x)

    # Water
    for r in loc.hazards:
        stamp_water(s, r.x, r.y, r.w, r.h, pal["water"], frame=0, frames=FRAMES,
                    body_layer="world", surface_layer="props", glow_layer="glow")

    # Edge framing trees on world (outlined)
    for cx, h, lean in ((16, 68, 2), (304, 72, -2)):
        for y in range(gy - h, gy):
            t = (y - (gy - h)) / h
            half = 3 + int(t * 3)
            xoff = int(lean * (1 - t))
            for dx in range(-half, half + 1):
                c = stone[0] if abs(dx) == half else (stone[1] if dx < 0 else stone[2])
                put(s, cx + dx + xoff, y, c, "world")
        s.stamp(leaf_cluster_pixels(cx, gy - h + 4, leaf, radius=12, count=20, seed=cx), layer="world", frame=0)


def draw_props(s: Sprite, loc: LocationSpec, pal: dict) -> None:
    gold, accent = pal["gold"], pal["accent"]
    for p in loc.props:
        if p.kind == "torch":
            put(s, p.x, p.y, pal["stone"][1], "props")
            put(s, p.x, p.y + 1, pal["stone"][1], "props")
            put(s, p.x, p.y - 1, gold[0], "props")
            put(s, p.x, p.y - 2, accent[2], "props")
        elif p.kind == "chest":
            for dy in range(5):
                for dx in range(-4, 5):
                    put(s, p.x + dx, p.y - dy, gold[0] if dy > 2 else gold[1], "props")
        elif p.kind == "door":
            for y in range(p.y, p.y + TILE * 2):
                for x in range(p.x, p.x + TILE):
                    put(s, x, y, pal["stone"][0], "props")
            put(s, p.x, p.y, pal["moss"][1], "props")
        elif p.meta.get("kind") == "mushroom":
            put(s, p.x, p.y, pal["stone"][2], "props")
            put(s, p.x, p.y - 1, accent[0], "props")
            put(s, p.x - 1, p.y - 1, accent[1], "props")
            put(s, p.x + 1, p.y - 1, accent[1], "props")
        elif p.kind == "checkpoint":
            put(s, p.x, p.y - 1, gold[1], "props")
    for r in loc.climbables:
        for y in range(r.y, r.y + r.h):
            put(s, r.x, y, pal["moss"][1], "props")


def draw_foreground(s: Sprite, pal: dict, loc: LocationSpec) -> None:
    """FG scroll 1.25 — margins only, sparse (never covers player lane)."""
    leaf, moss = pal["leaf"], pal["moss"]
    rng = random.Random(13)
    for x in list(range(0, 28, 5)) + list(range(W - 28, W, 5)):
        s.stamp(leaf_cluster_pixels(x, 8 + rng.randint(0, 10), leaf, radius=6, count=10, seed=x + 3),
                layer="fg", frame=0)
    for x in list(range(2, 32, 4)) + list(range(W - 32, W - 2, 4)):
        for dy in range(rng.randint(2, 5)):
            put(s, x, loc.ground_y - 2 - dy, moss[dy % 2], "fg")


def make_lights(loc: LocationSpec) -> LightingSetup:
    setup = LightingSetup(time_of_day="dusk")
    apply_time_of_day(setup)
    setup.ambient = (120, 100, 140)
    setup.ambient_strength = 0.32
    for i, (wx, wy) in enumerate(loc.windows):
        setup.add_shaft(wx, wy, aim_deg=95 + (i - 1) * 8, length=H - wy - 24,
                        cone_deg=36, color=(255, 180, 110), intensity=0.42, flicker_seed=10 + i)
    for i, (lx, ly) in enumerate(loc.lamps):
        setup.add_point(lx, ly, color=(255, 150, 70), intensity=0.95, radius=26, flicker_seed=40 + i)
    setup.add_point(W // 2, loc.ground_y - 2, color=(180, 130, 90), intensity=0.22, radius=W * 0.4, flicker_seed=0)
    return setup


def copy_static(s: Sprite) -> None:
    names = ["sky", "bg_far", "bg_mid", "bg_near", "close_bg", "world", "props", "fg", "shade"]
    for fi in range(1, FRAMES):
        for name in names:
            layer = s._resolve_layer(name)
            src = layer.cels[0]
            if src:
                layer.cels[fi] = Cel(x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels))


def build():
    loc = build_layout(27)
    pal = theme_colors(loc.theme)
    s = Sprite(W, H)
    # Terraria-style stack
    for L in PARALLAX_STACK:
        s.add_layer(L["name"])
    s.add_layer("shade", blend_mode="multiply", opacity=100)
    s.add_layer("beams", blend_mode="screen")
    s.add_layer("glow", blend_mode="addition")
    s.add_layer("fx_cloud_bg", blend_mode="screen")
    s.add_layer("fx_cloud_fg", blend_mode="normal", opacity=150)
    s.add_layer("fx_leaves", blend_mode="normal")

    for _ in range(1, FRAMES):
        s.add_frame(100)

    draw_parallax(s, pal, loc)
    draw_world(s, loc, pal)
    draw_props(s, loc, pal)
    draw_foreground(s, pal, loc)
    copy_static(s)

    # Pre-bake one-way weather (no wrap, no pingpong reverse)
    bg_clouds = bake_drift_frames(
        make_cloud_field(W, H, count=3, seed=8, direction=1, fg=False,
                         color=tuple(pal.get("cloud_bg", [(145, 125, 175, 48)])[0])),
        FRAMES, steps_per_frame=1,
    )
    fg_clouds = bake_drift_frames(
        make_cloud_field(W, H, count=2, seed=19, direction=1, fg=True,
                         color=tuple(pal.get("cloud_fg", [(30, 22, 40, 50)])[0])),
        FRAMES, steps_per_frame=1,
    )
    leaves = bake_drift_frames(
        make_leaf_field(W, H, count=26, seed=7, colors=pal["leaf"]),
        FRAMES, steps_per_frame=1,
    )

    setup = make_lights(loc)
    for f in range(FRAMES):
        for fx in ("shade", "beams", "glow", "fx_cloud_bg", "fx_cloud_fg", "fx_leaves"):
            s.ensure_cel(fx, f).clear()
        stamp_diffused(s, color=(255, 185, 130), strength=0.4, frame=f, open_sky=0.65)
        stamp_lighting(s, setup, frame=f, stamp_shade=(f == 0))
        if f > 0:
            src = s._resolve_layer("shade").cels[0]
            if src:
                s._resolve_layer("shade").cels[f] = Cel(
                    x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels)
                )
        for r in loc.hazards:
            stamp_water(s, r.x, r.y, r.w, r.h, pal["water"], frame=f, frames=FRAMES,
                        body_layer="world", surface_layer="props", glow_layer="glow")
        s.stamp(bg_clouds[f], layer="fx_cloud_bg", frame=f)
        s.stamp(fg_clouds[f], layer="fx_cloud_fg", frame=f)
        s.stamp(leaves[f], layer="fx_leaves", frame=f)
        s.set_frame_duration(f, 100)

    # Forward only — weather shouldn't reverse
    s.add_tag("ambient", 0, FRAMES - 1, direction="forward")
    return s, loc


def main():
    s, loc = build()
    s.save(OUT / "rustvale_hollow.aseprite")
    s.preview(OUT / "rustvale_hollow.png", scale=2, frame=0, background=(8, 6, 14, 255))
    # Forward loop GIF (no pingpong)
    s.preview_gif(OUT / "rustvale_hollow.gif", scale=2, background=(8, 6, 14, 255),
                  frames=list(range(FRAMES)))
    game = loc.export_game()
    game["parallax"] = list(PARALLAX_STACK)
    game["ambient"] = {"frames": FRAMES, "direction": "forward", "duration_ms": 100}
    game["prompt"] = (
        "Rustvale Hollow v2 — Terraria parallax, multi-layer platforms, banded water, "
        "one-way clouds/leaves (spawn/despawn), soft lighting."
    )
    (OUT / "rustvale_hollow_game.json").write_text(json.dumps(game, indent=2))
    print("Rustvale Hollow", game["validation"], f"frames={FRAMES} parallax={len(PARALLAX_STACK)}")


if __name__ == "__main__":
    main()

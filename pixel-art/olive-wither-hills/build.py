#!/usr/bin/env python3
"""Olive Wither Hills — Blasphemous-inspired cold olive grove (game-ready).

Snow dither, twisted olives, ash stone paths, muted crimson accents.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / ".cursor" / "skills" / "aseprite-pixel-art"
sys.path.insert(0, str(SKILL / "scripts"))

from aseprite_io import Cel, Sprite
from atmosphere import drifting_clouds_frame, soft_sky_pixels
from lighting_logic import LightingSetup, apply_time_of_day, stamp_diffused, stamp_lighting
from location_gen import (
    LocationSpec, PlatformerPhysics, Prop, Rect,
    ensure_game_ready, make_platformer_room, platformer_layer_stack, theme_colors,
)
from penitent_style import blood_stain, olive_tree, snow_dither_band, stone_block

OUT = Path(__file__).resolve().parent
W, H, TILE = 320, 176, 16
FRAMES = 8


def put(s, x, y, c, layer, frame=0):
    if 0 <= x < s.width and 0 <= y < s.height:
        s.put_pixel(x, y, c, layer=layer, frame=frame)


def build_layout() -> LocationSpec:
    phys = PlatformerPhysics(tile=TILE, jump_height=48, jump_gap=56)
    loc = make_platformer_room(
        name="olive_wither_hills", width=W, height=H, tile=TILE,
        theme="olive_wither", style="linear", platforms=0, seed=55,
        game_ready=False, physics=phys,
    )
    loc.solids = [r for r in loc.solids if r.y == 0 or r.x == 0 or r.x >= W - TILE]
    loc.one_way.clear(); loc.hazards.clear(); loc.kill_zones.clear()
    loc.props.clear(); loc.windows.clear(); loc.lamps.clear()
    loc.exits.clear(); loc.climbables.clear(); loc.checkpoints.clear()

    t, gy = TILE, loc.ground_y
    # Ravine
    pit = Rect(t * 8, gy, t * 4, H - gy)
    loc.hazards.append(pit)
    loc.kill_zones.append(Rect(pit.x, H - t, pit.w, t))
    loc.solids.append(Rect(t, gy, pit.x - t, H - gy))
    loc.solids.append(Rect(pit.x + pit.w, gy, W - t - (pit.x + pit.w), H - gy))
    # Fallen trunk bridge
    loc.solids.append(Rect(pit.x - 6, gy - 8, pit.w + 12, 5))

    ledges = [
        (t * 2, gy - t * 2, t * 3, True),
        (t * 5, gy - t * 3, t * 2, False),
        (t * 12, gy - t * 2, t * 3, True),
        (t * 15, gy - t * 3, t * 2, True),
        (t * 10, gy - t * 5, t * 3, False),
        (t * 4, gy - t * 5, t * 2, True),
        (t * 13, gy - t * 6, t * 2, True),
    ]
    for x, y, w, solid in ledges:
        (loc.solids if solid else loc.one_way).append(Rect(x, y, w, t if solid else t // 2 + 2))

    loc.windows = [(100, 20), (220, 18)]  # pale sky gaps
    loc.lamps = [(60, gy - 30), (250, gy - 30)]
    loc.props = [
        Prop("torch", 60, gy - 26, {"kind": "lantern"}),
        Prop("torch", 250, gy - 26, {"kind": "lantern"}),
        Prop("chest", t * 13 + 6, gy - t * 6, {}),
        Prop("door", W - t * 2, gy - t * 2, {"exit": "east"}),
        Prop("checkpoint", t * 2 + 8, gy - t * 2, {}),
    ]
    loc.player_spawn = (t * 2 + 8, gy - t * 2)
    loc.checkpoints = [loc.player_spawn]
    loc.exits.append({"name": "east", "x": W - t * 2, "y": gy - t * 2, "w": t, "h": t * 2, "target": "next"})
    return ensure_game_ready(loc, phys)


def draw_static(s: Sprite, loc: LocationSpec) -> None:
    pal = theme_colors(loc.theme)
    stone, snow, olive, wood, bg = pal["stone"], pal["snow"], pal["olive"], pal["wood"], pal["bg"]
    accent, gold = pal["accent"], pal["gold"]

    sky = soft_sky_pixels(W, H, (90, 100, 115, 255), bg[0], haze=pal["haze"][0], haze_y=0.45, haze_width=0.4)
    s.stamp(sky, layer="sky", frame=0)

    # Far hills (few colors)
    for i in range(6):
        hx = 30 + i * 55
        for dy in range(25):
            for dx in range(-30 + dy, 30 - dy):
                put(s, hx + dx, 55 + dy, (55, 60, 72, 140), "far")

    # Close-bg olives (no outline)
    for i, (cx, h) in enumerate(((50, 70), (140, 85), (230, 75), (300, 68))):
        soft_wood = [(c[0] + 12, c[1] + 8, c[2] + 8, 220) for c in wood]
        soft_fol = [(c[0] + 15, c[1] + 12, c[2] + 10, 200) for c in olive]
        s.stamp(olive_tree(cx, loc.ground_y - 2, h, soft_wood, soft_fol, snow, seed=10 + i), "close_bg")

    # Main terrain
    for r in loc.solids:
        if r.y >= loc.ground_y:
            s.stamp(stone_block(r.x, r.y, r.w, r.h, stone, outline=True), "world")
            # Snow cap on walkable top
            for x in range(r.x, r.x + r.w):
                put(s, x, r.y - 1, snow[1], "props")
                if (x + r.y) % 3 == 0:
                    put(s, x, r.y - 2, snow[0], "props")
        elif r.h <= 8 and r.y < loc.ground_y and r.w > TILE:
            # trunk bridge
            for y in range(r.y, r.y + r.h):
                for x in range(r.x, r.x + r.w):
                    put(s, x, y, wood[1] if y == r.y else wood[0], "world")
            for x in range(r.x, r.x + r.w):
                put(s, x, r.y, stone[3] if len(stone) > 3 else stone[-1], "world")
                put(s, x, r.y - 1, snow[0], "props")
        elif r.y < loc.ground_y and r.w < W // 2:
            s.stamp(stone_block(r.x, r.y, r.w, r.h, stone, outline=True), "world")
            for x in range(r.x, r.x + r.w):
                put(s, x, r.y - 1, snow[1], "props")
        elif r.y == 0 or r.x == 0 or r.x >= W - TILE:
            s.stamp(stone_block(r.x, r.y, r.w, min(r.h, H - r.y), stone, outline=True), "world")

    for r in loc.one_way:
        s.stamp(stone_block(r.x, r.y, r.w, r.h, stone, outline=True), "world")
        for x in range(r.x, r.x + r.w):
            put(s, x, r.y - 1, snow[0], "props")

    # Ravine void + blood-stained snow
    for r in loc.hazards:
        for y in range(r.y, min(r.y + r.h, H)):
            for x in range(r.x, r.x + r.w):
                put(s, x, y, (20, 22, 28, 255), "world")
        s.stamp(blood_stain(r.x + r.w // 2, r.y - 2, accent, seed=3), "props")

    # Main olives at edges (outlined trunks via wood dark edge in helper)
    s.stamp(olive_tree(18, loc.ground_y, 65, wood, olive, snow, seed=90), "world")
    s.stamp(olive_tree(302, loc.ground_y, 70, wood, olive, snow, seed=91), "world")

    for p in loc.props:
        if p.kind == "torch":
            put(s, p.x, p.y, wood[0], "props")
            put(s, p.x, p.y - 1, gold[0], "props")
            put(s, p.x, p.y - 2, (255, 200, 100, 255), "props")
        elif p.kind == "chest":
            for dy in range(5):
                for dx in range(-4, 5):
                    put(s, p.x + dx, p.y - dy, gold[0], "props")
        elif p.kind == "door":
            for y in range(p.y, p.y + TILE * 2):
                for x in range(p.x, p.x + TILE):
                    put(s, x, y, stone[0], "props")
            put(s, p.x + TILE // 2, p.y + 8, gold[1], "props")
        elif p.kind == "checkpoint":
            put(s, p.x, p.y - 1, gold[1], "props")

    # FG snow tufts at margins
    for x in list(range(2, 36, 4)) + list(range(W - 36, W - 2, 4)):
        put(s, x, loc.ground_y - 3, snow[1], "near")
        put(s, x + 1, loc.ground_y - 4, snow[0], "near")


def make_lights(loc: LocationSpec) -> LightingSetup:
    setup = LightingSetup(time_of_day="day")
    apply_time_of_day(setup)
    setup.ambient = (160, 170, 190)
    setup.ambient_strength = 0.22
    for i, (wx, wy) in enumerate(loc.windows):
        setup.add_shaft(wx, wy, aim_deg=100, length=100, cone_deg=36,
                        color=(220, 230, 245), intensity=0.45, flicker_seed=5 + i)
    for i, (lx, ly) in enumerate(loc.lamps):
        setup.add_point(lx, ly, color=(255, 180, 100), intensity=0.85, radius=24, flicker_seed=30 + i)
    return setup


def copy_static(s: Sprite) -> None:
    for fi in range(1, FRAMES):
        for name in ("sky", "far", "close_bg", "world", "props", "near", "shade"):
            layer = s._resolve_layer(name)
            src = layer.cels[0]
            if src:
                layer.cels[fi] = Cel(x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels))


def build():
    loc = build_layout()
    s = Sprite(W, H)
    for layer in platformer_layer_stack():
        n = layer["name"]
        if n == "fg_fx":
            continue
        if n == "shade":
            s.add_layer(n, blend_mode="multiply", opacity=90)
        elif n == "beams":
            s.add_layer(n, blend_mode="screen")
        elif n == "glow":
            s.add_layer(n, blend_mode="addition")
        else:
            s.add_layer(n)
    s.add_layer("snow_fx", blend_mode="normal")
    for _ in range(1, FRAMES):
        s.add_frame(120)
    draw_static(s, loc)
    copy_static(s)
    setup = make_lights(loc)
    pal = theme_colors(loc.theme)
    for f in range(FRAMES):
        for fx in ("shade", "beams", "glow", "snow_fx"):
            s.ensure_cel(fx, f).clear()
        stamp_diffused(s, color=(200, 210, 230), strength=0.32, frame=f, open_sky=0.7)
        stamp_lighting(s, setup, frame=f, stamp_shade=(f == 0))
        if f > 0:
            src = s._resolve_layer("shade").cels[0]
            if src:
                s._resolve_layer("shade").cels[f] = Cel(x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels))
        # Falling snow
        for i in range(35):
            x = (i * 37 + f * 3) % W
            y = (i * 53 + f * 4) % H
            put(s, x, y, pal["snow"][i % 2], "snow_fx", f)
        # Soft bg clouds
        s.stamp(drifting_clouds_frame(W, H, f, FRAMES, layer="bg", seed=3, count=2,
                                      color=(190, 195, 210, 45)), layer="beams", frame=f)
        s.set_frame_duration(f, 120)
    s.add_tag("ambient", 0, FRAMES - 1, direction="pingpong")
    return s, loc


def main():
    s, loc = build()
    s.save(OUT / "olive_wither_hills.aseprite")
    s.preview(OUT / "olive_wither_hills.png", scale=2, frame=0, background=(50, 55, 65, 255))
    order = list(range(FRAMES)) + list(range(FRAMES - 2, 0, -1))
    s.preview_gif(OUT / "olive_wither_hills.gif", scale=2, background=(50, 55, 65, 255), frames=order)
    game = loc.export_game()
    game["style"] = "blasphemous_olive_wither"
    game["prompt"] = "Olive Wither Hills — cold ash paths, twisted olives, snow dither, ravine, muted crimson."
    (OUT / "olive_wither_hills_game.json").write_text(json.dumps(game, indent=2))
    print("Olive Wither Hills", game["validation"], f"platforms={game['validation']['platform_count']}")


if __name__ == "__main__":
    main()

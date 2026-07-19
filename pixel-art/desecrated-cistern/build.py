#!/usr/bin/env python3
"""Desecrated Cistern — Blasphemous-inspired underground (game-ready).

Wet stone, bilge moss, black water volume, rust chains, sick gold candles.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / ".cursor" / "skills" / "aseprite-pixel-art"
sys.path.insert(0, str(SKILL / "scripts"))

from aseprite_io import Cel, Sprite
from atmosphere import soft_sky_pixels, stamp_water
from lighting_logic import LightingSetup, apply_time_of_day, stamp_diffused, stamp_lighting
from location_gen import (
    LocationSpec, PlatformerPhysics, Prop, Rect,
    ensure_game_ready, make_platformer_room, platformer_layer_stack, theme_colors,
)
from penitent_style import candle, column, stone_block

OUT = Path(__file__).resolve().parent
W, H, TILE = 320, 176, 16
FRAMES = 8


def put(s, x, y, c, layer, frame=0):
    if 0 <= x < s.width and 0 <= y < s.height:
        s.put_pixel(x, y, c, layer=layer, frame=frame)


def build_layout() -> LocationSpec:
    phys = PlatformerPhysics(tile=TILE, jump_height=48, jump_gap=52)
    loc = make_platformer_room(
        name="desecrated_cistern", width=W, height=H, tile=TILE,
        theme="cistern", style="pit", platforms=0, seed=66,
        game_ready=False, physics=phys,
    )
    loc.solids = [r for r in loc.solids if r.y == 0 or r.x == 0 or r.x >= W - TILE]
    loc.one_way.clear(); loc.hazards.clear(); loc.kill_zones.clear()
    loc.props.clear(); loc.windows.clear(); loc.lamps.clear()
    loc.exits.clear(); loc.climbables.clear(); loc.checkpoints.clear()

    t, gy = TILE, loc.ground_y
    # Wide flooded channel
    pit = Rect(t * 6, gy - 4, t * 8, H - (gy - 4))
    loc.hazards.append(pit)
    loc.kill_zones.append(Rect(pit.x, H - t, pit.w, t))
    loc.solids.append(Rect(t, gy, pit.x - t, H - gy))
    loc.solids.append(Rect(pit.x + pit.w, gy, W - t - (pit.x + pit.w), H - gy))

    # Stepping stones / walkways over water (reachable)
    stones = [
        (pit.x + 8, gy - t, t * 2, True),
        (pit.x + t * 3, gy - t * 2, t * 2, False),
        (pit.x + t * 5, gy - t, t * 2, True),
        (t * 2, gy - t * 3, t * 3, True),
        (t * 14, gy - t * 3, t * 3, True),
        (t * 5, gy - t * 5, t * 2, False),
        (t * 10, gy - t * 5, t * 2, False),
        (t * 7, gy - t * 7, t * 3, True),
        (t * 12, gy - t * 7, t * 2, True),
    ]
    for x, y, w, solid in stones:
        (loc.solids if solid else loc.one_way).append(Rect(x, y, w, t if solid else t // 2 + 2))

    loc.windows = []  # underground — no sky shafts; grate light instead
    loc.lamps = [(40, gy - 40), (160, gy - t * 5 - 10), (280, gy - 40), (120, 50)]
    loc.props = [
        Prop("torch", 40, gy - 36, {"kind": "candle"}),
        Prop("torch", 280, gy - 36, {"kind": "candle"}),
        Prop("torch", 160, gy - t * 5 - 6, {"kind": "candle"}),
        Prop("chest", t * 7 + 10, gy - t * 7, {}),
        Prop("door", W - t * 2, gy - t * 2, {"exit": "east"}),
        Prop("decor", 100, 30, {"kind": "grate"}),
        Prop("decor", 220, 30, {"kind": "grate"}),
        Prop("checkpoint", t * 2 + 8, gy - t * 3, {}),
    ]
    loc.player_spawn = (t * 2 + 8, gy - t * 3)
    loc.checkpoints = [loc.player_spawn, (t * 14 + 8, gy - t * 3)]
    loc.exits.append({"name": "east", "x": W - t * 2, "y": gy - t * 2, "w": t, "h": t * 2, "target": "next"})
    loc.climbables.append(Rect(t * 9, gy - t * 7, 5, t * 5))
    return ensure_game_ready(loc, phys)


def draw_static(s: Sprite, loc: LocationSpec) -> None:
    pal = theme_colors(loc.theme)
    stone, water, accent, gold, rust, bg = (
        pal["stone"], pal["water"], pal["accent"], pal["gold"], pal["rust"], pal["bg"]
    )

    sky = soft_sky_pixels(W, H, bg[0], bg[-1], haze=pal["haze"][0], haze_y=0.5, haze_width=0.5)
    s.stamp(sky, layer="sky", frame=0)

    # Far wet walls (flat)
    for y in range(TILE, loc.ground_y):
        for x in range(TILE, W - TILE):
            if (x // 6 + y // 5) % 3 == 0:
                put(s, x, y, (20, 28, 30, 255), "far")
            else:
                put(s, x, y, (14, 20, 22, 255), "far")

    # Close-bg pillars (no outline)
    soft = [(c[0] + 10, c[1] + 14, c[2] + 12, 255) for c in stone[:3]]
    for cx in (80, 160, 240):
        s.stamp(column(cx, 20, loc.ground_y - 8, soft, width=4), "close_bg")
        # Moss streaks
        for y in range(40, loc.ground_y - 10, 7):
            put(s, cx - 2, y, accent[0], "close_bg")

    # Main solids
    for r in loc.solids:
        if r.y == 0 or r.x == 0 or r.x >= W - TILE:
            s.stamp(stone_block(r.x, r.y, r.w, min(r.h, H - r.y), stone, outline=True), "world")
        elif r.y >= loc.ground_y or (r.y < loc.ground_y and r.w < W // 2):
            s.stamp(stone_block(r.x, r.y, r.w, r.h, stone, outline=True), "world")
            # Wet lip
            for x in range(r.x, r.x + r.w, 2):
                put(s, x, r.y, (stone[2][0] + 20, stone[2][1] + 25, stone[2][2] + 20, 255), "props")

    for r in loc.one_way:
        s.stamp(stone_block(r.x, r.y, r.w, r.h, stone, outline=True), "world")
        for x in range(r.x, r.x + r.w):
            put(s, x, r.y - 1, accent[1], "props")

    # Water body
    for r in loc.hazards:
        stamp_water(s, r.x, r.y, r.w, r.h, water, frame=0, frames=FRAMES,
                    body_layer="world", surface_layer="props", glow_layer="glow")
        # Rust pipes into water
        for px in (r.x + 10, r.x + r.w - 12):
            for y in range(r.y - 20, r.y):
                put(s, px, y, rust[0], "props")
                put(s, px + 1, y, rust[1], "props")

    for p in loc.props:
        if p.meta.get("kind") == "candle" or p.kind == "torch":
            s.stamp(candle(p.x, p.y, gold), "props")
        elif p.meta.get("kind") == "grate":
            for dy in range(12):
                for dx in range(-8, 9):
                    if dx % 3 == 0 or dy % 3 == 0:
                        put(s, p.x + dx, p.y + dy, stone[2], "close_bg")
        elif p.kind == "chest":
            for dy in range(5):
                for dx in range(-4, 5):
                    put(s, p.x + dx, p.y - dy, rust[1] if dy < 2 else gold[0], "props")
        elif p.kind == "door":
            for y in range(p.y, p.y + TILE * 2):
                for x in range(p.x, p.x + TILE):
                    put(s, x, y, stone[0], "props")
            put(s, p.x + 3, p.y + 10, gold[0], "props")
        elif p.kind == "checkpoint":
            put(s, p.x, p.y - 1, gold[1], "props")

    for r in loc.climbables:
        for y in range(r.y, r.y + r.h):
            put(s, r.x, y, rust[0], "props")
            if y % 3 == 0:
                put(s, r.x + 1, y, rust[1], "props")

    # FG drips / moss at margins
    for x in (6, 10, W - 12, W - 8):
        for y in range(30, loc.ground_y, 11):
            put(s, x, y, accent[0], "near")
            put(s, x, y + 1, water[1], "near")


def make_lights(loc: LocationSpec) -> LightingSetup:
    setup = LightingSetup(time_of_day="night")
    apply_time_of_day(setup)
    setup.ambient = (50, 70, 75)
    setup.ambient_strength = 0.58
    # Grate light from above
    for gx in (100, 220):
        setup.add_shaft(gx, 28, aim_deg=90, length=70, cone_deg=22,
                        color=(140, 180, 160), intensity=0.4, flicker_seed=gx)
    for i, (lx, ly) in enumerate(loc.lamps):
        setup.add_point(lx, ly, color=(255, 160, 70), intensity=1.0, radius=26, flicker_seed=40 + i)
    # Water bounce
    setup.add_point(W // 2, loc.ground_y + 4, color=(40, 90, 90), intensity=0.3, radius=80, flicker_seed=0)
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
            s.add_layer(n, blend_mode="multiply", opacity=120)
        elif n == "beams":
            s.add_layer(n, blend_mode="screen")
        elif n == "glow":
            s.add_layer(n, blend_mode="addition")
        else:
            s.add_layer(n)
    for _ in range(1, FRAMES):
        s.add_frame(130)
    draw_static(s, loc)
    copy_static(s)
    setup = make_lights(loc)
    pal = theme_colors(loc.theme)
    for f in range(FRAMES):
        for fx in ("shade", "beams", "glow"):
            s.ensure_cel(fx, f).clear()
        stamp_diffused(s, color=(80, 120, 110), strength=0.22, frame=f, open_sky=0.2)
        stamp_lighting(s, setup, frame=f, stamp_shade=(f == 0))
        if f > 0:
            src = s._resolve_layer("shade").cels[0]
            if src:
                s._resolve_layer("shade").cels[f] = Cel(x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels))
        for r in loc.hazards:
            stamp_water(s, r.x, r.y, r.w, r.h, pal["water"], frame=f, frames=FRAMES,
                        body_layer="world", surface_layer="props", glow_layer="glow")
        for lx, ly in loc.lamps:
            a = 160 + int(25 * math.sin(f * 0.8 + lx * 0.1))
            put(s, lx, ly - 3, (255, 200, 100, max(0, a)), "glow", f)
        s.set_frame_duration(f, 130)
    s.add_tag("ambient", 0, FRAMES - 1, direction="pingpong")
    return s, loc


def main():
    s, loc = build()
    s.save(OUT / "desecrated_cistern.aseprite")
    s.preview(OUT / "desecrated_cistern.png", scale=2, frame=0, background=(6, 10, 12, 255))
    order = list(range(FRAMES)) + list(range(FRAMES - 2, 0, -1))
    s.preview_gif(OUT / "desecrated_cistern.gif", scale=2, background=(6, 10, 12, 255), frames=order)
    game = loc.export_game()
    game["style"] = "blasphemous_cistern"
    game["prompt"] = "Desecrated Cistern — wet stone, bilge moss, black water, rust chains, grate light, votive candles."
    (OUT / "desecrated_cistern_game.json").write_text(json.dumps(game, indent=2))
    print("Desecrated Cistern", game["validation"], f"platforms={game['validation']['platform_count']}")


if __name__ == "__main__":
    main()

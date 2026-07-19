#!/usr/bin/env python3
"""Mother of Thorns — Blasphemous-inspired gothic cathedral (game-ready).

Purist pixel: ash stone, faded gold, penitent crimson. Maglione layers.
Hard outlines on collidables; close-bg columns without outline.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / ".cursor" / "skills" / "aseprite-pixel-art"
sys.path.insert(0, str(SKILL / "scripts"))

from aseprite_io import Cel, Sprite
from atmosphere import soft_sky_pixels
from lighting_logic import LightingSetup, apply_time_of_day, stamp_diffused, stamp_lighting
from location_gen import (
    LocationSpec, PlatformerPhysics, Prop, Rect,
    ensure_game_ready, make_platformer_room, platformer_layer_stack, theme_colors,
)
from penitent_style import (
    blood_stain, candle, column, gold_filigree_line, gothic_arch,
    hanging_cage, stained_glass, stone_block, thorn_cluster,
)

OUT = Path(__file__).resolve().parent
W, H, TILE = 320, 176, 16
FRAMES = 8


def put(s, x, y, c, layer, frame=0):
    if 0 <= x < s.width and 0 <= y < s.height:
        s.put_pixel(x, y, c, layer=layer, frame=frame)


def stamp(s, pixels, layer, frame=0):
    s.stamp(pixels, layer=layer, frame=frame)


def build_layout() -> LocationSpec:
    phys = PlatformerPhysics(tile=TILE, jump_height=48, jump_gap=56)
    loc = make_platformer_room(
        name="mother_of_thorns", width=W, height=H, tile=TILE,
        theme="penitent", style="ascent", platforms=0, seed=41,
        game_ready=False, physics=phys,
    )
    loc.solids = [r for r in loc.solids if r.y == 0 or r.x == 0 or r.x >= W - TILE]
    loc.one_way.clear(); loc.hazards.clear(); loc.kill_zones.clear()
    loc.props.clear(); loc.windows.clear(); loc.lamps.clear()
    loc.exits.clear(); loc.climbables.clear(); loc.checkpoints.clear()

    t, gy = TILE, loc.ground_y
    # Pit of thorns (hazard + kill)
    pit = Rect(t * 9, gy, t * 3, H - gy)
    loc.hazards.append(pit)
    loc.kill_zones.append(Rect(pit.x, H - t, pit.w, t))
    loc.solids.append(Rect(t, gy, pit.x - t, H - gy))
    loc.solids.append(Rect(pit.x + pit.w, gy, W - t - (pit.x + pit.w), H - gy))
    # Bridge of Calvary
    loc.solids.append(Rect(pit.x - 4, gy - 10, pit.w + 8, 6))

    ledges = [
        (t * 2, gy - t * 2, t * 3, True),
        (t * 5, gy - t * 3, t * 2, False),
        (t * 12, gy - t * 2, t * 3, True),
        (t * 15, gy - t * 4, t * 2, True),
        (t * 8, gy - t * 5, t * 3, False),
        (t * 3, gy - t * 6, t * 2, True),
        (t * 11, gy - t * 7, t * 3, True),
        (t * 6, gy - t * 8, t * 2, False),
    ]
    for x, y, w, solid in ledges:
        (loc.solids if solid else loc.one_way).append(Rect(x, y, w, t if solid else t // 2 + 2))

    loc.windows = [(80, 28), (160, 24), (240, 28)]
    loc.lamps = [(48, gy - 36), (200, gy - 48), (280, gy - 28), (120, gy - t * 5 - 12)]
    loc.props = [
        Prop("torch", 48, gy - 32, {"kind": "candle"}),
        Prop("torch", 200, gy - 44, {"kind": "candle"}),
        Prop("torch", 280, gy - 24, {"kind": "candle"}),
        Prop("chest", t * 11 + 10, gy - t * 7, {"kind": "relic"}),
        Prop("door", W - t * 2, gy - t * 2, {"exit": "east"}),
        Prop("decor", 100, 40, {"kind": "cage"}),
        Prop("decor", 220, 36, {"kind": "cage"}),
        Prop("checkpoint", t * 2 + 8, gy - t * 2, {}),
    ]
    loc.player_spawn = (t * 2 + 8, gy - t * 2)
    loc.checkpoints = [loc.player_spawn, (t * 15 + 8, gy - t * 4)]
    loc.exits.append({"name": "east", "x": W - t * 2, "y": gy - t * 2, "w": t, "h": t * 2, "target": "next"})
    loc.climbables.append(Rect(t * 7, gy - t * 8, 6, t * 6))
    return ensure_game_ready(loc, phys)


def draw_static(s: Sprite, loc: LocationSpec) -> None:
    pal = theme_colors(loc.theme)
    stone, gold, accent, bg = pal["stone"], pal["gold"], pal["accent"], pal["bg"]
    glass = pal["glass"]

    # Sky / void nave
    sky = soft_sky_pixels(W, H, bg[0], bg[-1], haze=pal.get("haze", [bg[1]])[0], haze_y=0.4, haze_width=0.35)
    s.stamp(sky, layer="sky", frame=0)

    # Far: dark buttress silhouettes
    for i in range(8):
        x = 20 + i * 40
        for y in range(20, loc.ground_y - 20):
            put(s, x, y, (22, 16, 20, 160), "far")
            put(s, x + 1, y, (22, 16, 20, 120), "far")

    # Close-bg: columns WITHOUT outline (saturated flatter) + brick fill
    soft_stone = [(min(255, c[0] + 15), min(255, c[1] + 10), min(255, c[2] + 12), 255) for c in stone[:3]]
    for y in range(TILE + 4, loc.ground_y - 4):
        for x in range(TILE + 2, W - TILE - 2):
            row, col = (y - TILE) // 5, x // 8
            base = soft_stone[1] if (row + col) % 2 == 0 else soft_stone[0]
            if (y - TILE) % 5 == 0:
                base = soft_stone[0]
            put(s, x, y, (*base[:3], 200), "close_bg")
    for cx in (56, 160, 264):
        stamp(s, column(cx, 24, loc.ground_y - 4, soft_stone, gold=None, width=5), "close_bg")
    # Blood streaks on close_bg walls
    for bx in (90, 180, 250):
        stamp(s, blood_stain(bx, loc.ground_y - 30, accent, seed=bx), "close_bg")
        stamp(s, thorn_cluster(bx, 50, seed=bx + 1, color=pal["thorn"][0]), "close_bg")

    # Main floor + walls
    for r in loc.solids:
        if r.y >= loc.ground_y or (r.h >= TILE and r.y < loc.ground_y and r.w >= TILE * 2 and r.h <= TILE):
            stamp(s, stone_block(r.x, r.y, r.w, r.h, stone, outline=True), "world")
        elif r.y == 0 or r.x == 0 or r.x >= W - TILE:
            stamp(s, stone_block(r.x, r.y, r.w, min(r.h, H - r.y), stone, outline=True), "world")
        elif r.h <= 8 and r.y < loc.ground_y:
            stamp(s, stone_block(r.x, r.y, r.w, r.h, stone, outline=True), "world")
            stamp(s, gold_filigree_line(r.x + 2, r.y, r.w - 4, gold), "props")

    for r in loc.one_way:
        stamp(s, stone_block(r.x, r.y, r.w, r.h, stone, outline=True), "world")
        stamp(s, gold_filigree_line(r.x, r.y, r.w, gold), "props")

    # Thorn pit
    for r in loc.hazards:
        for y in range(r.y, min(r.y + r.h, H)):
            for x in range(r.x, r.x + r.w):
                put(s, x, y, (16, 12, 14, 255), "world")
        for x in range(r.x, r.x + r.w, 5):
            stamp(s, thorn_cluster(x + 2, r.y + 2, seed=x, color=pal["thorn"][1]), "props")
            stamp(s, blood_stain(x + 2, r.y + 6, accent, seed=x), "props")

    # Stained glass shafts anchors
    for i, (wx, wy) in enumerate(loc.windows):
        stamp(s, stained_glass(wx, wy, 10, 36, glass, stone), "world")

    # Props
    for p in loc.props:
        if p.meta.get("kind") == "candle" or p.kind == "torch":
            stamp(s, candle(p.x, p.y, gold), "props")
        elif p.meta.get("kind") == "cage":
            stamp(s, hanging_cage(p.x, p.y, stone, accent), "close_bg")
        elif p.kind == "chest":
            for dy in range(0, 6):
                for dx in range(-5, 6):
                    put(s, p.x + dx, p.y - dy, gold[0] if dy > 2 else gold[1], "props")
            put(s, p.x, p.y - 3, accent[1], "props")
        elif p.kind == "door":
            stamp(s, gothic_arch(p.x + TILE // 2, p.y, TILE // 2, TILE * 2, stone, fill=stone[0]), "props")
            stamp(s, gold_filigree_line(p.x + 2, p.y + 4, TILE - 4, gold), "props")
        elif p.kind == "checkpoint":
            put(s, p.x, p.y - 1, gold[1], "props")
            put(s, p.x, p.y - 2, accent[1], "props")

    for r in loc.climbables:
        for y in range(r.y, r.y + r.h):
            put(s, r.x, y, accent[0], "props")
            if y % 4 == 0:
                put(s, r.x + 1, y, gold[0], "props")

    # FG thorns at margins only
    for x in (4, 12, W - 14, W - 6):
        stamp(s, thorn_cluster(x, loc.ground_y - 4, seed=x + 3, color=pal["thorn"][0]), "near")
    # Ceiling filigree
    stamp(s, gold_filigree_line(TILE, TILE + 2, W - TILE * 2, gold), "near")


def make_lights(loc: LocationSpec) -> LightingSetup:
    setup = LightingSetup(time_of_day="night")
    apply_time_of_day(setup)
    setup.ambient = (70, 55, 65)
    setup.ambient_strength = 0.52
    for i, (wx, wy) in enumerate(loc.windows):
        setup.add_shaft(wx, wy + 20, aim_deg=95, length=90, cone_deg=28,
                        color=(180, 140, 100), intensity=0.55, flicker_seed=10 + i)
    for i, (lx, ly) in enumerate(loc.lamps):
        setup.add_point(lx, ly, color=(255, 170, 80), intensity=1.0, radius=22, flicker_seed=40 + i)
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
            s.add_layer(n, blend_mode="multiply", opacity=115)
        elif n == "beams":
            s.add_layer(n, blend_mode="screen")
        elif n == "glow":
            s.add_layer(n, blend_mode="addition")
        else:
            s.add_layer(n)
    for _ in range(1, FRAMES):
        s.add_frame(140)
    draw_static(s, loc)
    copy_static(s)
    setup = make_lights(loc)
    for f in range(FRAMES):
        for fx in ("shade", "beams", "glow"):
            s.ensure_cel(fx, f).clear()
        stamp_diffused(s, color=(200, 150, 110), strength=0.28, frame=f, open_sky=0.35)
        stamp_lighting(s, setup, frame=f, stamp_shade=(f == 0))
        if f > 0:
            src = s._resolve_layer("shade").cels[0]
            if src:
                s._resolve_layer("shade").cels[f] = Cel(x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels))
        # Candle flicker dust
        for lx, ly in loc.lamps:
            a = 180 + int(20 * (0.5 + 0.5 * __import__("math").sin(f * 0.9 + lx)))
            s.put_pixel(lx, ly - 3, (255, 220, 140, a), layer="glow", frame=f)
        s.set_frame_duration(f, 140)
    s.add_tag("ambient", 0, FRAMES - 1, direction="pingpong")
    return s, loc


def main():
    s, loc = build()
    s.save(OUT / "mother_of_thorns.aseprite")
    s.preview(OUT / "mother_of_thorns.png", scale=2, frame=0, background=(8, 6, 10, 255))
    order = list(range(FRAMES)) + list(range(FRAMES - 2, 0, -1))
    s.preview_gif(OUT / "mother_of_thorns.gif", scale=2, background=(8, 6, 10, 255), frames=order)
    game = loc.export_game()
    game["style"] = "blasphemous_penitent"
    game["prompt"] = "Mother of Thorns — ash gothic nave, stained glass, thorn pit, gold filigree, cages, votive candles."
    (OUT / "mother_of_thorns_game.json").write_text(json.dumps(game, indent=2))
    print("Mother of Thorns", game["validation"], f"platforms={game['validation']['platform_count']}")


if __name__ == "__main__":
    main()

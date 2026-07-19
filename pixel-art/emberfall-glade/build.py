#!/usr/bin/env python3
"""Emberfall Glade — dark fantasy autumn forest platformer stage.

Prompt:
  Canvas 320x176, tile 16. Dark fantasy autumn forest: plum bark, rust/amber
  foliage, violet mist, warm ember accents. Ascent + creek pit. Canopy god-rays,
  will-o'-wisps, ember lamps. Drifting leaves, 8-frame pingpong ambient.
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / ".cursor" / "skills" / "aseprite-pixel-art"
sys.path.insert(0, str(SKILL / "scripts"))

from aseprite_io import Cel, Sprite
from fx_helpers import flicker, wave_curve
from lighting_logic import LightingSetup, apply_time_of_day, stamp_lighting
from location_gen import LocationSpec, Prop, Rect, make_platformer_room, theme_colors

OUT = Path(__file__).resolve().parent
W, H, TILE = 320, 176, 16
FRAMES = 8


def put(s, x, y, c, layer, frame=0):
    if 0 <= x < s.width and 0 <= y < s.height:
        s.put_pixel(x, y, c, layer=layer, frame=frame)


def fill(s, x0, y0, x1, y1, c, layer, frame=0):
    s.fill_rect(x0, y0, x1, y1, c, layer=layer, frame=frame)


def build_layout(seed: int = 19) -> LocationSpec:
    """Custom Emberfall layout: ground, creek pit, climbing ledges, log bridge."""
    loc = make_platformer_room(
        name="emberfall_glade",
        width=W,
        height=H,
        tile=TILE,
        theme="autumn_forest",
        style="ascent",
        platforms=0,  # we'll place our own
        seed=seed,
    )
    # Clear auto platforms from ascent with platforms=0 — still has floor/walls
    loc.solids = [r for r in loc.solids if r.y >= loc.ground_y or r.w <= TILE or r.x == 0 or r.x >= W - TILE]
    loc.one_way.clear()
    loc.hazards.clear()
    loc.props.clear()
    loc.windows.clear()
    loc.lamps.clear()
    loc.exits.clear()

    t, gy = TILE, loc.ground_y

    # Creek pit in the middle
    pit = Rect(t * 8, gy, t * 5, H - gy)
    loc.hazards.append(pit)
    # Split floor around pit
    loc.solids = [r for r in loc.solids if not (r.y >= gy and r.x == 0 and r.w == W)]
    loc.solids.append(Rect(0, 0, W, t))          # canopy ceiling band
    loc.solids.append(Rect(0, 0, t, H))
    loc.solids.append(Rect(W - t, 0, t, H))
    loc.solids.append(Rect(t, gy, pit.x - t, H - gy))
    loc.solids.append(Rect(pit.x + pit.w, gy, W - t - (pit.x + pit.w), H - gy))

    # Log bridge over creek (solid)
    loc.solids.append(Rect(pit.x - 4, gy - t, pit.w + 8, 6))

    # Climbing moss ledges (mix solid + one-way leaf piles)
    ledges = [
        (t * 2, gy - t * 2, t * 3, True),
        (t * 5, gy - t * 3, t * 2, False),
        (t * 12, gy - t * 2, t * 3, True),
        (t * 15, gy - t * 4, t * 2, False),
        (t * 10, gy - t * 5, t * 3, True),
        (t * 4, gy - t * 6, t * 2, False),
        (t * 13, gy - t * 7, t * 3, True),
        (t * 7, gy - t * 8, t * 2, False),
    ]
    for x, y, w, solid in ledges:
        r = Rect(x, y, w, t // 2 + 2)
        (loc.solids if solid else loc.one_way).append(r)

    # Canopy light gaps (shaft anchors)
    loc.windows = [(70, 28), (160, 22), (240, 30)]
    # Ember lamps / wisps
    loc.lamps = [(48, gy - 28), (200, gy - 40), (280, gy - 24), (120, gy - t * 5 - 8)]
    loc.props = [
        Prop("torch", 48, gy - 24, {"kind": "ember"}),
        Prop("torch", 200, gy - 36, {"kind": "ember"}),
        Prop("torch", 280, gy - 20, {"kind": "ember"}),
        Prop("chest", t * 13 + 8, gy - t * 7 - 8, {}),
        Prop("door", W - t * 2, gy - t * 2, {"exit": "east"}),
        Prop("decor", 90, gy - 8, {"kind": "mushroom"}),
        Prop("decor", 250, gy - 8, {"kind": "mushroom"}),
        Prop("decor", 180, gy - t - 4, {"kind": "root"}),
    ]
    loc.player_spawn = (t * 2 + 8, gy - t * 2)
    loc.exits.append({"name": "east", "x": W - t * 2, "y": gy - t * 2, "w": t, "h": t * 2, "target": "next_glade"})
    loc.climbables.append(Rect(t * 6, gy - t * 8, 6, t * 6))
    return loc


def draw_sky_and_mist(s: Sprite, pal: dict) -> None:
    bg = pal["bg"]
    for y in range(H):
        t = y / H
        # Violet dusk gradient
        c = (
            int(bg[0][0] + (bg[-1][0] - bg[0][0]) * t),
            int(bg[0][1] + (bg[-1][1] - bg[0][1]) * t),
            int(bg[0][2] + (bg[-1][2] - bg[0][2]) * t),
            255,
        )
        for x in range(W):
            put(s, x, y, c, "far")
    # Distant silhouette treeline
    bark = pal["stone"]
    leaf = pal["leaf"]
    rng = random.Random(3)
    for i in range(18):
        tx = 10 + i * 18 + rng.randint(-3, 3)
        th = rng.randint(28, 50)
        for y in range(H // 3 - th, H // 3):
            put(s, tx, y, bark[0], "far")
            put(s, tx + 1, y, bark[0], "far")
        # Canopy blob
        cy = H // 3 - th + 6
        for dy in range(-10, 8):
            for dx in range(-12, 13):
                if dx * dx / 140 + dy * dy / 80 <= 1:
                    put(s, tx + dx, cy + dy, leaf[i % len(leaf)], "far")


def draw_tree(s: Sprite, cx: int, base_y: int, height: int, pal: dict, lean: int = 0) -> None:
    bark, leaf, moss = pal["stone"], pal["leaf"], pal["moss"]
    # Trunk
    for y in range(base_y - height, base_y):
        t = (y - (base_y - height)) / max(1, height)
        half = int(3 + t * 4)
        xoff = int(lean * (1 - t))
        for dx in range(-half, half + 1):
            c = bark[1] if dx < 0 else bark[2]
            if abs(dx) == half:
                c = bark[0]
            put(s, cx + dx + xoff, y, c, "world")
        # Moss patches
        if y % 7 == 0:
            put(s, cx - half + xoff, y, moss[1], "world")
    # Root flare
    for dx in range(-8, 9):
        put(s, cx + dx, base_y - 1, bark[1], "world")
        if abs(dx) < 6:
            put(s, cx + dx, base_y - 2, bark[2], "world")
    # Canopy clusters
    top = base_y - height + 4
    for ox, oy, r, li in ((-6, 0, 11, 0), (8, -4, 12, 1), (0, -10, 10, 2), (-10, -8, 8, 3), (12, 2, 7, 1)):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    # Darker underside
                    c = leaf[li % len(leaf)] if dy < r // 3 else leaf[(li + 1) % len(leaf)]
                    if dx * dx + dy * dy > (r - 2) * (r - 2) and dy > 0:
                        c = leaf[0]
                    put(s, cx + ox + dx + lean // 2, top + oy + dy, c, "mid")


def draw_creek(s: Sprite, pit: Rect, pal: dict) -> None:
    water = pal["water"]
    for y in range(pit.y, min(pit.y2 + 1, H)):
        for x in range(pit.x, pit.x2 + 1):
            depth = (y - pit.y) / max(1, pit.h)
            c = water[0] if depth < 0.35 else (water[1] if depth < 0.7 else water[2])
            put(s, x, y, c, "world")
            if (x + y) % 5 == 0:
                put(s, x, y, water[min(2, 1)], "world")
    # Bank mud
    bark = pal["stone"]
    for x in range(pit.x - 3, pit.x):
        for y in range(pit.y - 2, pit.y + 4):
            put(s, x, y, bark[1], "world")
    for x in range(pit.x2 + 1, pit.x2 + 4):
        for y in range(pit.y - 2, pit.y + 4):
            put(s, x, y, bark[1], "world")


def draw_log_bridge(s: Sprite, r: Rect, pal: dict) -> None:
    bark = pal["stone"]
    moss = pal["moss"]
    for y in range(r.y, r.y + r.h):
        for x in range(r.x, r.x + r.w):
            c = bark[2] if (y - r.y) < 2 else bark[1]
            put(s, x, y, c, "world")
    # Bark rings
    for x in range(r.x + 2, r.x + r.w, 5):
        put(s, x, r.y + 1, bark[0], "world")
    put(s, r.x + 3, r.y, moss[1], "world")
    put(s, r.x + r.w - 4, r.y, moss[0], "world")


def draw_ledge(s: Sprite, r: Rect, pal: dict, leafy: bool) -> None:
    bark, leaf, moss = pal["stone"], pal["leaf"], pal["moss"]
    for y in range(r.y, r.y + r.h):
        for x in range(r.x, r.x + r.w):
            put(s, x, y, bark[2] if y == r.y else bark[1], "world")
    if leafy:
        for x in range(r.x, r.x + r.w):
            put(s, x, r.y - 1, leaf[(x // 2) % len(leaf)], "mid")
            if x % 3 == 0:
                put(s, x, r.y - 2, leaf[1], "mid")
    else:
        for x in range(r.x, r.x + r.w, 4):
            put(s, x, r.y, moss[1], "world")


def draw_ground(s: Sprite, loc: LocationSpec, pal: dict) -> None:
    bark, leaf, moss = pal["stone"], pal["leaf"], pal["moss"]
    gy = loc.ground_y
    for r in loc.solids:
        if r.y < gy:
            continue
        for y in range(r.y, min(r.y + r.h, H)):
            for x in range(r.x, r.x + r.w):
                depth = (y - gy) / max(1, H - gy)
                c = bark[2] if depth < 0.15 else (bark[1] if depth < 0.5 else bark[0])
                put(s, x, y, c, "world")
        # Leaf litter on top
        for x in range(r.x, r.x + r.w):
            if (x * 3) % 7 != 0:
                put(s, x, gy - 1, leaf[x % len(leaf)], "mid")
            if x % 5 == 0:
                put(s, x, gy - 2, moss[0], "mid")


def draw_props(s: Sprite, loc: LocationSpec, pal: dict) -> None:
    leaf, gold, accent = pal["leaf"], pal["gold"], pal["accent"]
    for p in loc.props:
        if p.kind == "torch" or p.meta.get("kind") == "ember":
            # Twisted ember lantern on stake
            fill(s, p.x, p.y, p.x + 1, p.y + 6, pal["stone"][1], "props")
            put(s, p.x, p.y - 1, gold[0], "props")
            put(s, p.x + 1, p.y - 1, gold[1], "props")
            put(s, p.x, p.y - 2, accent[2], "props")
            put(s, p.x + 1, p.y - 2, (255, 200, 100, 255), "props")
        elif p.kind == "chest":
            fill(s, p.x - 4, p.y - 3, p.x + 4, p.y, gold[0], "props")
            fill(s, p.x - 4, p.y - 6, p.x + 4, p.y - 3, gold[1], "props")
            put(s, p.x, p.y - 4, accent[1], "props")
        elif p.kind == "door":
            # Vine-choked arch exit
            fill(s, p.x, p.y, p.x + TILE - 1, p.y + TILE * 2 - 1, pal["stone"][0], "props")
            for y in range(p.y, p.y + TILE * 2):
                put(s, p.x, y, pal["moss"][1], "props")
                put(s, p.x + TILE - 1, y, pal["moss"][0], "props")
        elif p.meta.get("kind") == "mushroom":
            put(s, p.x, p.y, pal["stone"][2], "props")
            put(s, p.x, p.y - 1, accent[0], "props")
            put(s, p.x - 1, p.y - 1, accent[1], "props")
            put(s, p.x + 1, p.y - 1, accent[1], "props")
            put(s, p.x, p.y - 2, accent[2], "props")
        elif p.meta.get("kind") == "root":
            for i in range(8):
                put(s, p.x + i, p.y - i // 3, pal["stone"][1], "props")


def draw_canopy_overlay(s: Sprite, pal: dict) -> None:
    """Overhanging leaves at top of frame."""
    leaf = pal["leaf"]
    rng = random.Random(9)
    for x in range(0, W, 2):
        depth = rng.randint(8, 22)
        for y in range(0, depth):
            if rng.random() < 0.7:
                put(s, x, y, leaf[(x + y) % len(leaf)], "near")
            if y < 4:
                put(s, x, y, leaf[0], "near")


def draw_static_scene(s: Sprite, loc: LocationSpec) -> None:
    pal = theme_colors(loc.theme)
    draw_sky_and_mist(s, pal)
    # Background trees
    for cx, h, lean in ((40, 90, -2), (100, 110, 1), (170, 100, -1), (230, 115, 2), (290, 95, -2)):
        draw_tree(s, cx, loc.ground_y, h, pal, lean=lean)
    draw_ground(s, loc, pal)
    for r in loc.hazards:
        draw_creek(s, r, pal)
    for r in loc.solids:
        if r.h <= 8 and r.y < loc.ground_y and r.w > TILE:
            draw_log_bridge(s, r, pal)
        elif r.y < loc.ground_y and TILE // 2 <= r.h <= TILE and r.w < W // 2:
            draw_ledge(s, r, pal, leafy=False)
    for r in loc.one_way:
        draw_ledge(s, r, pal, leafy=True)
    # Mid trees framing
    draw_tree(s, 20, loc.ground_y, 70, pal, lean=3)
    draw_tree(s, 300, loc.ground_y, 75, pal, lean=-3)
    draw_props(s, loc, pal)
    draw_canopy_overlay(s, pal)


def make_lighting(loc: LocationSpec) -> LightingSetup:
    setup = LightingSetup(time_of_day="dusk")
    apply_time_of_day(setup)
    # Cooler violet ambient for dark fantasy
    setup.ambient = (110, 90, 140)
    setup.ambient_strength = 0.48
    # Canopy shafts — warm autumn gold
    for i, (wx, wy) in enumerate(loc.windows):
        setup.add_shaft(
            wx, wy,
            aim_deg=95 + (i - 1) * 10,
            length=H - wy - 20,
            cone_deg=26,
            color=(255, 170, 90),
            intensity=0.9,
            flicker_seed=20 + i,
        )
    # Ember lamps
    for i, (lx, ly) in enumerate(loc.lamps):
        setup.add_point(lx, ly, color=(255, 140, 60), intensity=1.05, radius=26, flicker_seed=40 + i)
    # Will-o'-wisps (cool)
    setup.add_point(150, 70, color=(140, 220, 200), intensity=0.7, radius=18, flicker_seed=77)
    setup.add_point(210, 100, color=(160, 140, 255), intensity=0.55, radius=14, flicker_seed=88)
    return setup


def draw_falling_leaves(s: Sprite, frame: int, seed: int = 5) -> None:
    pal = theme_colors("autumn_forest")
    leaf = pal["leaf"]
    rng = random.Random(seed)
    for i in range(28):
        base_x = rng.randint(0, W - 1)
        speed = rng.uniform(0.6, 1.4)
        sway = rng.uniform(0.4, 1.2)
        phase = rng.random()
        y = int((rng.random() * H + frame * 2.2 * speed) % H)
        x = int(base_x + math.sin((frame / FRAMES + phase) * math.tau) * 6 * sway) % W
        c = leaf[i % len(leaf)]
        a = 200 if i % 3 else 140
        put(s, x, y, (c[0], c[1], c[2], a), "leaves", frame)
        if i % 4 == 0:
            put(s, x + 1, y, (c[0], c[1], c[2], a // 2), "leaves", frame)


def copy_static(s: Sprite) -> None:
    names = ["far", "world", "mid", "props", "near", "shade"]
    for fi in range(1, FRAMES):
        for name in names:
            layer = s._resolve_layer(name)
            src = layer.cels[0]
            if src is None:
                continue
            layer.cels[fi] = Cel(x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels))


def build() -> tuple[Sprite, LocationSpec]:
    loc = build_layout(19)
    s = Sprite(W, H)
    s.add_layer("far")
    s.add_layer("world")
    s.add_layer("mid")
    s.add_layer("props")
    s.add_layer("near")
    s.add_layer("shade", blend_mode="multiply", opacity=110)
    s.add_layer("beams", blend_mode="screen")
    s.add_layer("glow", blend_mode="addition")
    s.add_layer("leaves", blend_mode="normal")

    for _ in range(1, FRAMES):
        s.add_frame(130)

    draw_static_scene(s, loc)
    copy_static(s)

    setup = make_lighting(loc)
    for f in range(FRAMES):
        for fx in ("shade", "beams", "glow", "leaves"):
            s.ensure_cel(fx, f).clear()
        stamp_lighting(s, setup, frame=f, stamp_shade=(f == 0))
        if f > 0:
            src = s._resolve_layer("shade").cels[0]
            if src:
                s._resolve_layer("shade").cels[f] = Cel(
                    x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels)
                )
        draw_falling_leaves(s, f)
        s.set_frame_duration(f, 130)

    s.add_tag("ambient", 0, FRAMES - 1, direction="pingpong")
    return s, loc


def main() -> None:
    s, loc = build()
    ase = s.save(OUT / "emberfall_glade.aseprite")
    png = s.preview(OUT / "emberfall_glade.png", scale=2, frame=0, background=(8, 6, 14, 255))
    order = list(range(FRAMES)) + list(range(FRAMES - 2, 0, -1))
    gif = s.preview_gif(OUT / "emberfall_glade.gif", scale=2, background=(8, 6, 14, 255), frames=order)
    coll = {
        "name": loc.name,
        "theme": loc.theme,
        "spawn": loc.player_spawn,
        "exits": loc.exits,
        "collision": loc.collision_map(),
        "lamps": loc.lamps,
        "windows": loc.windows,
    }
    (OUT / "emberfall_glade_collision.json").write_text(json.dumps(coll, indent=2))
    print(f"saved {ase}")
    print(f"saved {png}")
    print(f"saved {gif}")
    print(f"solids={len(loc.solids)} one_way={len(loc.one_way)} hazards={len(loc.hazards)}")
    print(f"windows={loc.windows} lamps={len(loc.lamps)}")


if __name__ == "__main__":
    main()

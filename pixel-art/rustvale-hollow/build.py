#!/usr/bin/env python3
"""Rustvale Hollow — dark fantasy autumn forest (new-logic game-ready stage).

Uses Maglione layer roles, diffused light, volumetric water, leaf volume,
FG/BG clouds, and export_game() validation from the upgraded skill.

Prompt:
  Soft diffused amber canopy light over a violet mist hollow. Close-bg trunks
  without outlines; main platforms with hard walkable edges. Creek with volume,
  leaf heaps on ledges, foreground grass/branches at margins only. Reachable
  ascent + pit, 320x176, tile 16, 8-frame ambient pingpong.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / ".cursor" / "skills" / "aseprite-pixel-art"
sys.path.insert(0, str(SKILL / "scripts"))

from aseprite_io import Cel, Sprite
from atmosphere import (
    drifting_clouds_frame,
    falling_leaves_frame,
    leaf_cluster_pixels,
    leaf_litter_pixels,
    soft_bounce_pixels,
    soft_silhouette_band,
    soft_sky_pixels,
    stamp_water,
)
from lighting_logic import LightingSetup, apply_time_of_day, stamp_diffused, stamp_lighting
from location_gen import (
    LocationSpec,
    PlatformerPhysics,
    Prop,
    Rect,
    ensure_game_ready,
    make_platformer_room,
    platformer_layer_stack,
    theme_colors,
)

OUT = Path(__file__).resolve().parent
W, H, TILE = 320, 176, 16
FRAMES = 8


def put(s, x, y, c, layer, frame=0):
    if 0 <= x < s.width and 0 <= y < s.height:
        s.put_pixel(x, y, c, layer=layer, frame=frame)


def fill(s, x0, y0, x1, y1, c, layer, frame=0):
    s.fill_rect(x0, y0, x1, y1, c, layer=layer, frame=frame)


def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))


# ---------------------------------------------------------------------------
# Layout — jump-budgeted, game-ready
# ---------------------------------------------------------------------------

def build_layout(seed: int = 27) -> LocationSpec:
    phys = PlatformerPhysics(tile=TILE, jump_height=48, jump_gap=56, player_w=12, player_h=16)
    loc = make_platformer_room(
        name="rustvale_hollow",
        width=W,
        height=H,
        tile=TILE,
        theme="autumn_forest",
        style="ascent",
        platforms=0,
        seed=seed,
        game_ready=False,
        physics=phys,
    )
    # Keep only ceiling + side walls from generator
    loc.solids = [r for r in loc.solids if r.y == 0 or r.x == 0 or r.x >= W - TILE]
    loc.one_way.clear()
    loc.hazards.clear()
    loc.kill_zones.clear()
    loc.props.clear()
    loc.windows.clear()
    loc.lamps.clear()
    loc.exits.clear()
    loc.climbables.clear()
    loc.checkpoints.clear()

    t, gy = TILE, loc.ground_y

    # Creek pit (center-left) + kill strip
    pit = Rect(t * 7, gy, t * 4, H - gy)
    loc.hazards.append(pit)
    loc.kill_zones.append(Rect(pit.x, H - t, pit.w, t))

    # Split ground floors
    loc.solids.append(Rect(t, gy, pit.x - t, H - gy))
    loc.solids.append(Rect(pit.x + pit.w, gy, W - t - (pit.x + pit.w), H - gy))

    # Log bridge over creek
    loc.solids.append(Rect(pit.x - t // 2, gy - t + 2, pit.w + t, 6))

    # Reachable ledges (rise ≤ 32, gap ≤ 48) — mix solid + one-way leaf shelves
    # (x, y, w, solid?)
    ledges = [
        (t * 2, gy - t * 2, t * 3, True),
        (t * 5, gy - t * 3, t * 2, False),
        (t * 11, gy - t * 2, t * 3, True),
        (t * 14, gy - t * 3, t * 2, False),
        (t * 10, gy - t * 5, t * 3, True),
        (t * 3, gy - t * 5, t * 2, False),
        (t * 13, gy - t * 6, t * 3, True),
        (t * 6, gy - t * 7, t * 2, False),
        (t * 9, gy - t * 8, t * 3, True),
    ]
    for x, y, w, solid in ledges:
        h = t if solid else t // 2 + 2
        r = Rect(x, y, w, h)
        (loc.solids if solid else loc.one_way).append(r)

    # Canopy light gaps + ember lamps
    loc.windows = [(64, 24), (150, 20), (230, 26)]
    loc.lamps = [
        (t * 2 + 8, gy - t * 2 - 10),
        (t * 11 + 12, gy - t * 2 - 10),
        (t * 13 + 10, gy - t * 6 - 10),
        (280, gy - 20),
    ]
    loc.props = [
        Prop("torch", loc.lamps[0][0], loc.lamps[0][1] + 6, {"kind": "ember"}),
        Prop("torch", loc.lamps[1][0], loc.lamps[1][1] + 6, {"kind": "ember"}),
        Prop("torch", loc.lamps[2][0], loc.lamps[2][1] + 6, {"kind": "ember"}),
        Prop("torch", loc.lamps[3][0], loc.lamps[3][1] + 6, {"kind": "ember"}),
        Prop("chest", t * 9 + 8, gy - t * 8, {}),
        Prop("door", W - t * 2, gy - t * 2, {"exit": "east"}),
        Prop("decor", 72, gy - 2, {"kind": "mushroom"}),
        Prop("decor", 248, gy - 2, {"kind": "mushroom"}),
        Prop("decor", 160, gy - t, {"kind": "root"}),
        Prop("checkpoint", t * 2 + 8, gy - t * 2, {}),
    ]
    loc.player_spawn = (t * 2 + 8, gy - t * 2)
    loc.checkpoints = [(t * 2 + 8, gy - t * 2), (t * 10 + 8, gy - t * 5)]
    loc.exits.append({
        "name": "east", "x": W - t * 2, "y": gy - t * 2,
        "w": t, "h": t * 2, "target": "next_hollow",
    })
    loc.climbables.append(Rect(t * 8, gy - t * 7, 6, t * 5))
    return ensure_game_ready(loc, phys)


# ---------------------------------------------------------------------------
# Drawing — Maglione roles
# ---------------------------------------------------------------------------

def draw_sky(s: Sprite, pal: dict) -> None:
    bg = pal["bg"]
    haze = pal.get("haze", [(90, 60, 110, 255)])[0]
    top = (32, 22, 52, 255)
    sky = soft_sky_pixels(
        W, H, top=top, bottom=bg[-1],
        haze=(clamp(haze[0] + 25), clamp(haze[1] + 15), clamp(haze[2] + 20), 255),
        haze_y=0.36, haze_width=0.42,
    )
    s.stamp(sky, layer="sky", frame=0)
    # Soft mist strips on sky
    for y in range(H // 4, H // 2, 4):
        for x in range(0, W, 2):
            put(s, x, y, (70, 50, 95, 22 + (x + y) % 18), "sky")


def draw_far_parallax(s: Sprite, pal: dict) -> None:
    """Saturated, few-color distant silhouettes (parallax_far)."""
    sil = soft_silhouette_band(
        W, horizon_y=H // 3 + 6,
        color=(28, 18, 42, 150),
        height=42, seed=11, blobs=12,
    )
    s.stamp(sil, layer="far", frame=0)
    # Single-color distant tree spikes
    bark = (36, 24, 48, 180)
    leaf = (120, 45, 40, 160)
    rng = random.Random(4)
    for i in range(10):
        tx = 16 + i * 32 + rng.randint(-4, 4)
        th = rng.randint(22, 40)
        for y in range(H // 3 - th, H // 3 + 4):
            put(s, tx, y, bark, "far")
        cy = H // 3 - th + 4
        for dy in range(-8, 6):
            for dx in range(-9, 10):
                if dx * dx / 90 + dy * dy / 50 <= 1:
                    put(s, tx + dx, cy + dy, leaf, "far")


def draw_close_bg_tree(s: Sprite, cx: int, base_y: int, height: int, pal: dict, lean: int = 0, seed: int = 0) -> None:
    """Close background trunks — NO hard outline, more saturated (non-collidable look)."""
    bark, leaf = pal["stone"], pal["leaf"]
    # Saturated / softer — no black outline
    soft_bark = [
        (clamp(c[0] + 18), clamp(c[1] + 8), clamp(c[2] + 12), 255) for c in bark[:3]
    ]
    for y in range(base_y - height, base_y):
        t = (y - (base_y - height)) / max(1, height)
        half = int(2 + t * 3)
        xoff = int(lean * (1 - t))
        for dx in range(-half, half + 1):
            c = soft_bark[1] if dx < 0 else soft_bark[min(2, len(soft_bark) - 1)]
            put(s, cx + dx + xoff, y, c, "close_bg")
    top = base_y - height + 6
    for i, (ox, oy, r) in enumerate(((-4, 0, 9), (5, -3, 10), (0, -8, 8))):
        # Slightly more saturated leaf tones for close_bg
        cols = [
            (clamp(c[0] + 20), clamp(c[1] + 10), clamp(c[2] + 5), 230) for c in leaf
        ]
        s.stamp(
            leaf_cluster_pixels(cx + ox + lean // 2, top + oy, cols, radius=r, count=10 + r, seed=seed + i),
            layer="close_bg", frame=0,
        )


def draw_main_tree(s: Sprite, cx: int, base_y: int, height: int, pal: dict, lean: int = 0, seed: int = 0) -> None:
    """Main-layer framing trees — higher contrast, darker edges (collidable feel if solid)."""
    bark, leaf, moss = pal["stone"], pal["leaf"], pal["moss"]
    for y in range(base_y - height, base_y):
        t = (y - (base_y - height)) / max(1, height)
        half = int(3 + t * 4)
        xoff = int(lean * (1 - t))
        for dx in range(-half, half + 1):
            c = bark[1] if dx < 0 else bark[2]
            if abs(dx) == half:
                c = bark[0]  # hard edge = main-layer read
            put(s, cx + dx + xoff, y, c, "world")
        if y % 8 == 0:
            put(s, cx - half + xoff, y, moss[1], "world")
    for dx in range(-7, 8):
        put(s, cx + dx, base_y - 1, bark[1], "world")
    top = base_y - height + 4
    for i, (ox, oy, r) in enumerate(((-6, 0, 11), (8, -4, 12), (0, -10, 10), (-10, -7, 8))):
        s.stamp(
            leaf_cluster_pixels(cx + ox + lean // 2, top + oy, leaf, radius=r, count=16 + r, seed=seed + i * 7),
            layer="world", frame=0,
        )


def draw_ground(s: Sprite, loc: LocationSpec, pal: dict) -> None:
    bark = pal["stone"]
    gy = loc.ground_y
    for r in loc.solids:
        if r.y < gy:
            continue
        for y in range(r.y, min(r.y + r.h, H)):
            for x in range(r.x, r.x + r.w):
                depth = (y - gy) / max(1, H - gy)
                c = bark[2] if depth < 0.12 else (bark[1] if depth < 0.45 else bark[0])
                put(s, x, y, c, "world")
        # Walkable top outline (main layer)
        for x in range(r.x, r.x + r.w):
            put(s, x, gy, bark[3], "world")
        s.stamp(leaf_litter_pixels(r.x, gy, r.w, pal["leaf"], density=0.7, seed=r.x, heaps=True), layer="props", frame=0)


def draw_log_bridge(s: Sprite, r: Rect, pal: dict) -> None:
    bark, moss = pal["stone"], pal["moss"]
    for y in range(r.y, r.y + r.h):
        for x in range(r.x, r.x + r.w):
            put(s, x, y, bark[2] if (y - r.y) < 2 else bark[1], "world")
    for x in range(r.x, r.x + r.w):
        put(s, x, r.y, bark[3], "world")  # outline top
    for x in range(r.x + 2, r.x + r.w, 5):
        put(s, x, r.y + 1, bark[0], "world")
    put(s, r.x + 4, r.y, moss[1], "world")
    s.stamp(leaf_litter_pixels(r.x, r.y, r.w, pal["leaf"], density=0.45, seed=r.x), layer="props", frame=0)


def draw_ledge(s: Sprite, r: Rect, pal: dict, leafy: bool) -> None:
    bark, moss = pal["stone"], pal["moss"]
    for y in range(r.y, r.y + r.h):
        for x in range(r.x, r.x + r.w):
            depth = (y - r.y) / max(1, r.h)
            c = bark[2] if depth < 0.35 else bark[1]
            put(s, x, y, c, "world")
    # Main-layer outline
    for x in range(r.x, r.x + r.w):
        put(s, x, r.y, bark[3], "world")
    put(s, r.x, r.y, bark[0], "world")
    put(s, r.x2, r.y, bark[0], "world")
    if leafy:
        s.stamp(leaf_litter_pixels(r.x, r.y, r.w, pal["leaf"], density=0.8, seed=r.x + r.y, heaps=True), layer="props", frame=0)
    else:
        for x in range(r.x, r.x + r.w, 4):
            put(s, x, r.y, moss[1], "world")


def draw_props(s: Sprite, loc: LocationSpec, pal: dict) -> None:
    gold, accent = pal["gold"], pal["accent"]
    for p in loc.props:
        if p.kind == "torch" or p.meta.get("kind") == "ember":
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
        elif p.kind == "checkpoint":
            put(s, p.x, p.y - 1, gold[1], "props")
            put(s, p.x, p.y - 2, accent[2], "props")


def draw_foreground(s: Sprite, pal: dict) -> None:
    """FG at margins only — never cover playable center (Maglione rule)."""
    leaf, moss = pal["leaf"], pal["moss"]
    rng = random.Random(13)
    # Left / right overhang branches
    for side, x0 in (("L", 0), ("R", W - 28)):
        for i in range(5):
            cx = x0 + 6 + i * 5 + rng.randint(-2, 2)
            cy = 10 + rng.randint(0, 14)
            s.stamp(leaf_cluster_pixels(cx, cy, leaf, radius=7, count=12, seed=40 + i + x0), layer="near", frame=0)
    # Bottom margin grass tufts (sides only — player path clear in center)
    for x in list(range(2, 40, 3)) + list(range(W - 40, W - 2, 3)):
        h = rng.randint(2, 5)
        for dy in range(h):
            put(s, x, H - 18 - dy, moss[dy % 2], "near")
            if rng.random() < 0.4:
                put(s, x + 1, H - 18 - dy, leaf[1], "near")
    # Top canopy fringe
    for x in range(0, W, 4):
        s.stamp(leaf_cluster_pixels(x, 6 + (x % 5), leaf, radius=5, count=8, seed=100 + x), layer="near", frame=0)


def draw_static(s: Sprite, loc: LocationSpec) -> None:
    pal = theme_colors(loc.theme)
    draw_sky(s, pal)
    draw_far_parallax(s, pal)
    # Close-bg trees (no outline) — atmosphere behind playfield
    for i, (cx, h, lean) in enumerate(((70, 78, -1), (160, 88, 1), (250, 82, -2))):
        draw_close_bg_tree(s, cx, loc.ground_y - 4, h, pal, lean=lean, seed=30 + i)
    draw_ground(s, loc, pal)
    for r in loc.hazards:
        stamp_water(s, r.x, r.y, r.w, r.h, pal["water"], frame=0, frames=FRAMES,
                    body_layer="world", surface_layer="props", glow_layer="glow")
    for r in loc.solids:
        if r.h <= 8 and r.y < loc.ground_y and r.w > TILE:
            draw_log_bridge(s, r, pal)
        elif r.y < loc.ground_y and TILE // 2 <= r.h <= TILE and r.w < W // 2:
            draw_ledge(s, r, pal, leafy=False)
    for r in loc.one_way:
        draw_ledge(s, r, pal, leafy=True)
    # Main framing trees at edges
    draw_main_tree(s, 14, loc.ground_y, 70, pal, lean=3, seed=90)
    draw_main_tree(s, 306, loc.ground_y, 74, pal, lean=-3, seed=91)
    draw_props(s, loc, pal)
    for r in loc.climbables:
        for y in range(r.y, r.y + r.h):
            put(s, r.x, y, pal["moss"][1], "props")
            if y % 3 == 0:
                put(s, r.x + 1, y, pal["moss"][0], "props")
    draw_foreground(s, pal)


def make_lighting(loc: LocationSpec) -> LightingSetup:
    setup = LightingSetup(time_of_day="dusk")
    apply_time_of_day(setup)
    setup.ambient = (118, 95, 140)
    setup.ambient_strength = 0.34
    for i, (wx, wy) in enumerate(loc.windows):
        setup.add_shaft(
            wx, wy, aim_deg=94 + (i - 1) * 9, length=H - wy - 18,
            cone_deg=40, color=(255, 175, 105), intensity=0.5, flicker_seed=15 + i,
        )
    for i, (lx, ly) in enumerate(loc.lamps):
        setup.add_point(lx, ly, color=(255, 145, 65), intensity=1.05, radius=28, flicker_seed=40 + i)
    setup.add_point(140, 72, color=(130, 220, 200), intensity=0.55, radius=16, flicker_seed=70)
    setup.add_point(200, 96, color=(150, 130, 255), intensity=0.45, radius=14, flicker_seed=71)
    setup.add_point(W // 2, loc.ground_y - 2, color=(190, 130, 85), intensity=0.32, radius=W * 0.42, flicker_seed=0)
    return setup


def copy_static(s: Sprite) -> None:
    names = ["sky", "far", "close_bg", "world", "props", "near", "shade"]
    for fi in range(1, FRAMES):
        for name in names:
            layer = s._resolve_layer(name)
            src = layer.cels[0]
            if src is None:
                continue
            layer.cels[fi] = Cel(x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels))


def animate(s: Sprite, loc: LocationSpec, setup: LightingSetup, f: int) -> None:
    pal = theme_colors(loc.theme)
    for fx in ("shade", "beams", "glow", "leaves", "clouds_fg"):
        s.ensure_cel(fx, f).clear()

    stamp_diffused(s, color=(255, 185, 125), strength=0.46, frame=f, open_sky=0.68)
    stamp_lighting(s, setup, frame=f, stamp_shade=(f == 0))
    if f > 0:
        src = s._resolve_layer("shade").cels[0]
        if src:
            s._resolve_layer("shade").cels[f] = Cel(
                x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels)
            )

    for lx, ly in loc.lamps:
        s.stamp(soft_bounce_pixels(lx, loc.ground_y - 1, 34, (255, 140, 70), 0.22), layer="beams", frame=f)

    bg_clouds = drifting_clouds_frame(
        W, H, f, FRAMES, layer="bg", seed=8, count=3,
        color=tuple(pal.get("cloud_bg", [(145, 125, 175, 50)])[0]),
    )
    s.stamp(bg_clouds, layer="beams", frame=f)

    # FG fog — lower band / margins so it doesn't hide the player
    fg = drifting_clouds_frame(
        W, H, f, FRAMES, layer="fg", seed=19, count=3,
        color=tuple(pal.get("cloud_fg", [(28, 20, 38, 55)])[0]),
    )
    s.stamp(fg, layer="clouds_fg", frame=f)

    for r in loc.hazards:
        stamp_water(
            s, r.x, r.y, r.w, r.h, pal["water"], frame=f, frames=FRAMES,
            body_layer="world", surface_layer="props", glow_layer="glow",
        )

    leaves = falling_leaves_frame(W, H, f, FRAMES, colors=pal["leaf"], count=40, seed=7)
    s.stamp(leaves, layer="leaves", frame=f)
    s.set_frame_duration(f, 130)


def build() -> tuple[Sprite, LocationSpec]:
    loc = build_layout(27)
    s = Sprite(W, H)
    # Maglione stack
    for layer in platformer_layer_stack():
        name = layer["name"]
        if name in ("shade",):
            s.add_layer(name, blend_mode="multiply", opacity=100)
        elif name == "beams":
            s.add_layer(name, blend_mode="screen")
        elif name == "glow":
            s.add_layer(name, blend_mode="addition")
        elif name == "fg_fx":
            continue  # use dedicated leaves/clouds instead
        else:
            s.add_layer(name)
    s.add_layer("leaves", blend_mode="normal")
    s.add_layer("clouds_fg", blend_mode="normal", opacity=160)

    for _ in range(1, FRAMES):
        s.add_frame(130)

    draw_static(s, loc)
    copy_static(s)
    setup = make_lighting(loc)
    for f in range(FRAMES):
        animate(s, loc, setup, f)

    s.add_tag("ambient", 0, FRAMES - 1, direction="pingpong")
    return s, loc


def main() -> None:
    s, loc = build()
    ase = s.save(OUT / "rustvale_hollow.aseprite")
    png = s.preview(OUT / "rustvale_hollow.png", scale=2, frame=0, background=(8, 6, 14, 255))
    order = list(range(FRAMES)) + list(range(FRAMES - 2, 0, -1))
    gif = s.preview_gif(OUT / "rustvale_hollow.gif", scale=2, background=(8, 6, 14, 255), frames=order)
    game = loc.export_game()
    game["prompt"] = (
        "Rustvale Hollow — dark fantasy autumn forest. Soft diffused amber canopy light, "
        "violet mist, Maglione layers (sky/far/close_bg/main/near), volumetric creek, "
        "leaf heaps, FG margin foliage, game-ready collision/tilemap."
    )
    game["layers"] = platformer_layer_stack()
    (OUT / "rustvale_hollow_game.json").write_text(json.dumps(game, indent=2))
    print(f"saved {ase}")
    print(f"saved {png}")
    print(f"saved {gif}")
    print(f"solids={len(loc.solids)} one_way={len(loc.one_way)} hazards={len(loc.hazards)}")
    print(f"validation={game['validation']}")
    print(f"tilemap {game['tilemap']['cols']}x{game['tilemap']['rows']}")
    print(f"spawn={game['spawn']} checkpoints={game['checkpoints']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Emberfall Glade — dark fantasy autumn forest (game-ready platformer stage).

Prompt:
  Soft diffused canopy light, soft violet mist background, foreground fog-clouds.
  Volumetric creek water, dense autumn leaves with volume. Playable ascent + pit
  with jump-reachable ledges, collision/tilemap/spawn export.
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


def build_layout(seed: int = 19) -> LocationSpec:
    """Custom Emberfall: reachable ascent, creek pit, log bridge, climb vine."""
    phys = PlatformerPhysics(tile=TILE, jump_height=52, jump_gap=56, player_w=12, player_h=16)
    loc = make_platformer_room(
        name="emberfall_glade",
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
    # Keep walls/ceiling only
    loc.solids = [r for r in loc.solids if r.x == 0 or r.x >= W - TILE or r.y == 0]
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

    # Creek pit — hazard + kill strip at bottom
    pit = Rect(t * 8, gy, t * 5, H - gy)
    loc.hazards.append(pit)
    loc.kill_zones.append(Rect(pit.x, H - t, pit.w, t))

    # Split floor around pit
    loc.solids.append(Rect(t, gy, pit.x - t, H - gy))
    loc.solids.append(Rect(pit.x + pit.w, gy, W - t - (pit.x + pit.w), H - gy))

    # Log bridge (thin solid, snapped x)
    loc.solids.append(Rect(pit.x - 4, gy - t, pit.w + 8, 6))

    # Climbing ledges — gaps/rises within jump budget
    # (x, y, w, solid?)
    ledges = [
        (t * 2, gy - t * 2, t * 3, True),
        (t * 5, gy - t * 3, t * 2, False),
        (t * 11, gy - t * 2, t * 3, True),
        (t * 14, gy - t * 4, t * 2, False),
        (t * 9, gy - t * 5, t * 3, True),
        (t * 4, gy - t * 6, t * 2, False),
        (t * 12, gy - t * 7, t * 3, True),
        (t * 7, gy - t * 8, t * 2, False),
    ]
    for x, y, w, solid in ledges:
        r = Rect(x, y, w, t // 2 + 2)
        (loc.solids if solid else loc.one_way).append(r)

    loc.windows = [(70, 28), (160, 22), (240, 30)]
    loc.lamps = [(48, gy - 28), (200, gy - 40), (280, gy - 24), (120, gy - t * 5 - 8)]
    loc.props = [
        Prop("torch", 48, gy - 24, {"kind": "ember"}),
        Prop("torch", 200, gy - 36, {"kind": "ember"}),
        Prop("torch", 280, gy - 20, {"kind": "ember"}),
        Prop("chest", t * 12 + 8, gy - t * 7, {}),
        Prop("door", W - t * 2, gy - t * 2, {"exit": "east"}),
        Prop("decor", 90, gy - 2, {"kind": "mushroom"}),
        Prop("decor", 250, gy - 2, {"kind": "mushroom"}),
        Prop("decor", 180, gy - t - 2, {"kind": "root"}),
        Prop("checkpoint", t * 2 + 8, gy - t * 2, {}),
    ]
    loc.player_spawn = (t * 2 + 8, gy - t * 2)
    loc.checkpoints = [(t * 2 + 8, gy - t * 2), (t * 12 + 8, gy - t * 7)]
    loc.exits.append({
        "name": "east", "x": W - t * 2, "y": gy - t * 2,
        "w": t, "h": t * 2, "target": "next_glade",
    })
    loc.climbables.append(Rect(t * 6, gy - t * 8, 6, t * 6))
    return ensure_game_ready(loc, phys)


def draw_soft_background(s: Sprite, pal: dict) -> None:
    bg = pal["bg"]
    haze = pal.get("haze", [(90, 60, 110, 255)])[0]
    # Brighter open-sky top so diffused light + depth read behind canopy
    top = (28, 20, 48, 255)
    bot = bg[-1]
    sky = soft_sky_pixels(
        W, H,
        top=top,
        bottom=bot,
        haze=(_clamp_c(haze[0] + 30), _clamp_c(haze[1] + 20), _clamp_c(haze[2] + 25), 255),
        haze_y=0.38,
        haze_width=0.45,
    )
    s.stamp(sky, layer="far", frame=0)
    sil = soft_silhouette_band(
        W, horizon_y=H // 3 + 4,
        color=(22, 16, 34, 160),
        height=40, seed=3, blobs=14,
    )
    s.stamp(sil, layer="far", frame=0)
    # Soft mist bands mid-frame (depth cue between far trees and playfield)
    for y in range(H // 3, H // 2 + 10, 3):
        for x in range(0, W, 2):
            a = 28 + (x * 3 + y * 5) % 20
            put(s, x, y, (60, 45, 85, a), "far")


def _clamp_c(v: int) -> int:
    return max(0, min(255, v))


def draw_tree(s: Sprite, cx: int, base_y: int, height: int, pal: dict, lean: int = 0, seed: int = 0, layer_canopy: str = "mid") -> None:
    bark, leaf, moss = pal["stone"], pal["leaf"], pal["moss"]
    for y in range(base_y - height, base_y):
        t = (y - (base_y - height)) / max(1, height)
        half = int(3 + t * 4)
        xoff = int(lean * (1 - t))
        for dx in range(-half, half + 1):
            c = bark[1] if dx < 0 else bark[2]
            if abs(dx) == half:
                c = bark[0]
            put(s, cx + dx + xoff, y, c, "world")
        if y % 7 == 0:
            put(s, cx - half + xoff, y, moss[1], "world")
    for dx in range(-8, 9):
        put(s, cx + dx, base_y - 1, bark[1], "world")
        if abs(dx) < 6:
            put(s, cx + dx, base_y - 2, bark[2], "world")
    top = base_y - height + 4
    # Volumetric leaf clusters instead of flat ellipses
    for i, (ox, oy, r) in enumerate(((-6, 0, 11), (8, -4, 12), (0, -10, 10), (-10, -8, 8), (12, 2, 7))):
        cluster = leaf_cluster_pixels(
            cx + ox + lean // 2, top + oy, leaf, radius=r, count=14 + r, seed=seed + i * 9,
        )
        s.stamp(cluster, layer=layer_canopy, frame=0)


def draw_log_bridge(s: Sprite, r: Rect, pal: dict) -> None:
    bark, moss = pal["stone"], pal["moss"]
    for y in range(r.y, r.y + r.h):
        for x in range(r.x, r.x + r.w):
            c = bark[2] if (y - r.y) < 2 else bark[1]
            put(s, x, y, c, "world")
    for x in range(r.x + 2, r.x + r.w, 5):
        put(s, x, r.y + 1, bark[0], "world")
    put(s, r.x + 3, r.y, moss[1], "world")
    put(s, r.x + r.w - 4, r.y, moss[0], "world")
    # Leaf litter on bridge
    s.stamp(leaf_litter_pixels(r.x, r.y, r.w, pal["leaf"], density=0.4, seed=r.x), layer="mid", frame=0)


def draw_ledge(s: Sprite, r: Rect, pal: dict, leafy: bool) -> None:
    bark, moss = pal["stone"], pal["moss"]
    for y in range(r.y, r.y + r.h):
        for x in range(r.x, r.x + r.w):
            put(s, x, y, bark[2] if y == r.y else bark[1], "world")
    if leafy:
        s.stamp(leaf_litter_pixels(r.x, r.y, r.w, pal["leaf"], density=0.75, seed=r.x + r.y), layer="mid", frame=0)
    else:
        for x in range(r.x, r.x + r.w, 4):
            put(s, x, r.y, moss[1], "world")


def draw_ground(s: Sprite, loc: LocationSpec, pal: dict) -> None:
    bark = pal["stone"]
    gy = loc.ground_y
    for r in loc.solids:
        if r.y < gy:
            continue
        for y in range(r.y, min(r.y + r.h, H)):
            for x in range(r.x, r.x + r.w):
                depth = (y - gy) / max(1, H - gy)
                c = bark[2] if depth < 0.15 else (bark[1] if depth < 0.5 else bark[0])
                put(s, x, y, c, "world")
        s.stamp(leaf_litter_pixels(r.x, gy, r.w, pal["leaf"], density=0.65, seed=r.x), layer="mid", frame=0)


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


def draw_canopy_overlay(s: Sprite, pal: dict) -> None:
    leaf = pal["leaf"]
    rng = random.Random(9)
    for x in range(0, W, 3):
        depth = rng.randint(10, 24)
        cluster = leaf_cluster_pixels(x, depth // 2, leaf, radius=depth // 2 + 2, count=10, seed=9 + x)
        s.stamp(cluster, layer="near", frame=0)


def draw_static_scene(s: Sprite, loc: LocationSpec) -> None:
    pal = theme_colors(loc.theme)
    draw_soft_background(s, pal)
    # Fewer/taller BG trees so soft sky + mist stay visible between trunks
    for i, (cx, h, lean) in enumerate(((55, 85, -2), (155, 95, 1), (255, 88, -1))):
        draw_tree(s, cx, loc.ground_y, h, pal, lean=lean, seed=20 + i, layer_canopy="far")
    draw_ground(s, loc, pal)
    for r in loc.hazards:
        stamp_water(s, r.x, r.y, r.w, r.h, pal["water"], frame=0, frames=FRAMES,
                    body_layer="world", surface_layer="mid", glow_layer="glow")
    for r in loc.solids:
        if r.h <= 8 and r.y < loc.ground_y and r.w > TILE:
            draw_log_bridge(s, r, pal)
        elif r.y < loc.ground_y and TILE // 2 <= r.h <= TILE and r.w < W // 2:
            draw_ledge(s, r, pal, leafy=False)
    for r in loc.one_way:
        draw_ledge(s, r, pal, leafy=True)
    # Near-field framing trees (canopy on mid/near)
    draw_tree(s, 18, loc.ground_y, 72, pal, lean=3, seed=90, layer_canopy="mid")
    draw_tree(s, 302, loc.ground_y, 78, pal, lean=-3, seed=91, layer_canopy="mid")
    draw_props(s, loc, pal)
    draw_canopy_overlay(s, pal)
    for r in loc.climbables:
        for y in range(r.y, r.y + r.h):
            put(s, r.x, y, pal["moss"][1], "props")
            if y % 3 == 0:
                put(s, r.x + 1, y, pal["moss"][0], "props")


def make_lighting(loc: LocationSpec) -> LightingSetup:
    setup = LightingSetup(time_of_day="dusk")
    apply_time_of_day(setup)
    setup.ambient = (120, 100, 145)
    setup.ambient_strength = 0.36  # softer multiply — diffused carries the mood
    for i, (wx, wy) in enumerate(loc.windows):
        setup.add_shaft(
            wx, wy,
            aim_deg=95 + (i - 1) * 10,
            length=H - wy - 20,
            cone_deg=38,
            color=(255, 175, 100),
            intensity=0.55,  # softer shafts over diffused fill
            flicker_seed=20 + i,
        )
    for i, (lx, ly) in enumerate(loc.lamps):
        setup.add_point(lx, ly, color=(255, 140, 60), intensity=1.0, radius=28, flicker_seed=40 + i)
    setup.add_point(150, 70, color=(140, 220, 200), intensity=0.65, radius=18, flicker_seed=77)
    setup.add_point(210, 100, color=(160, 140, 255), intensity=0.5, radius=14, flicker_seed=88)
    setup.add_point(W // 2, loc.ground_y - 2, color=(180, 120, 80), intensity=0.35, radius=W * 0.45, flicker_seed=0)
    return setup


def copy_static(s: Sprite) -> None:
    names = ["far", "world", "mid", "props", "near", "shade"]
    for fi in range(1, FRAMES):
        for name in names:
            layer = s._resolve_layer(name)
            src = layer.cels[0]
            if src is None:
                continue
            layer.cels[fi] = Cel(x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels))


def animate_frame(s: Sprite, loc: LocationSpec, setup: LightingSetup, f: int) -> None:
    pal = theme_colors(loc.theme)
    for fx in ("shade", "beams", "glow", "leaves", "clouds_fg"):
        s.ensure_cel(fx, f).clear()

    # Diffused soft light first
    stamp_diffused(s, color=(255, 185, 130), strength=0.48, frame=f, open_sky=0.7)
    stamp_lighting(s, setup, frame=f, stamp_shade=(f == 0))
    if f > 0:
        src = s._resolve_layer("shade").cels[0]
        if src:
            s._resolve_layer("shade").cels[f] = Cel(
                x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels)
            )

    # Extra soft bounce under lamps
    for lx, ly in loc.lamps:
        s.stamp(soft_bounce_pixels(lx, loc.ground_y - 1, 36, (255, 140, 70), 0.25), layer="beams", frame=f)

    # Background soft clouds (stamp into far by blending via clouds on screen? keep on beams soft)
    bg_clouds = drifting_clouds_frame(
        W, H, f, FRAMES, layer="bg", seed=11, count=3,
        color=tuple(pal.get("cloud_bg", [(140, 120, 170, 55)])[0]),
    )
    s.stamp(bg_clouds, layer="beams", frame=f)

    # Foreground fog-clouds
    fg = drifting_clouds_frame(
        W, H, f, FRAMES, layer="fg", seed=22, count=4,
        color=tuple(pal.get("cloud_fg", [(30, 22, 40, 70)])[0]),
    )
    s.stamp(fg, layer="clouds_fg", frame=f)

    # Volumetric water caustics / surface animation
    for r in loc.hazards:
        # Clear mid water surface strip then restamp animated water (body already in world)
        stamp_water(
            s, r.x, r.y, r.w, r.h, pal["water"], frame=f, frames=FRAMES,
            body_layer="world", surface_layer="mid", glow_layer="glow",
        )

    # Falling volumetric leaves
    leaves = falling_leaves_frame(W, H, f, FRAMES, colors=pal["leaf"], count=36, seed=5)
    s.stamp(leaves, layer="leaves", frame=f)
    s.set_frame_duration(f, 130)


def build() -> tuple[Sprite, LocationSpec]:
    loc = build_layout(19)
    s = Sprite(W, H)
    s.add_layer("far")
    s.add_layer("world")
    s.add_layer("mid")
    s.add_layer("props")
    s.add_layer("near")
    s.add_layer("shade", blend_mode="multiply", opacity=105)
    s.add_layer("beams", blend_mode="screen")
    s.add_layer("glow", blend_mode="addition")
    s.add_layer("leaves", blend_mode="normal")
    s.add_layer("clouds_fg", blend_mode="normal", opacity=180)

    for _ in range(1, FRAMES):
        s.add_frame(130)

    draw_static_scene(s, loc)
    copy_static(s)
    setup = make_lighting(loc)
    for f in range(FRAMES):
        animate_frame(s, loc, setup, f)

    s.add_tag("ambient", 0, FRAMES - 1, direction="pingpong")
    return s, loc


def main() -> None:
    s, loc = build()
    ase = s.save(OUT / "emberfall_glade.aseprite")
    png = s.preview(OUT / "emberfall_glade.png", scale=2, frame=0, background=(8, 6, 14, 255))
    order = list(range(FRAMES)) + list(range(FRAMES - 2, 0, -1))
    gif = s.preview_gif(OUT / "emberfall_glade.gif", scale=2, background=(8, 6, 14, 255), frames=order)
    game = loc.export_game()
    (OUT / "emberfall_glade_collision.json").write_text(json.dumps(game, indent=2))
    print(f"saved {ase}")
    print(f"saved {png}")
    print(f"saved {gif}")
    print(f"solids={len(loc.solids)} one_way={len(loc.one_way)} hazards={len(loc.hazards)}")
    print(f"validation={game['validation']}")
    print(f"tilemap {game['tilemap']['cols']}x{game['tilemap']['rows']}")


if __name__ == "__main__":
    main()

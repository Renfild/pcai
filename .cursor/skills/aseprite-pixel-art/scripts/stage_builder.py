"""Physics-aware stage builder — layouts + craft render for game-ready rooms.

Uses PlatformerPhysics for jump/gap budgets, ensure_game_ready validation,
Terraria parallax, multi-layer platforms, banded water, one-way ambient FX.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from aseprite_io import Cel, Sprite
from atmosphere import soft_silhouette_band, soft_sky_pixels, leaf_cluster_pixels
from lighting_logic import LightingSetup, apply_time_of_day, stamp_diffused, stamp_lighting
from location_gen import (
    LocationSpec, PlatformerPhysics, Prop, Rect,
    ensure_game_ready, make_platformer_room, theme_colors,
)
from loop_fx import (
    PARALLAX_STACK, bake_drift_frames, make_cloud_field, make_leaf_field,
    make_snow_field, stamp_platform, stamp_water,
)

W_DEFAULT, H_DEFAULT, TILE_DEFAULT = 320, 176, 16
FRAMES_DEFAULT = 12


@dataclass
class Ledge:
    x: int
    y: int
    w: int
    solid: bool = True
    style: str = "dirt"  # dirt | stone | wood | snow


@dataclass
class StageBrief:
    """Authoring brief for one physics stage."""

    name: str
    theme: str
    title: str
    prompt: str
    seed: int = 1
    style_gen: str = "linear"  # unused if custom ledges
    time: str = "dusk"
    width: int = W_DEFAULT
    height: int = H_DEFAULT
    tile: int = TILE_DEFAULT
    frames: int = FRAMES_DEFAULT
    # Physics (px)
    jump_height: int = 48
    jump_gap: int = 56
    # Pit: None or (tile_x, tile_w)
    pit: Optional[Tuple[int, int]] = None
    bridge: bool = True
    ledges: List[Ledge] = field(default_factory=list)
    windows: List[Tuple[int, int]] = field(default_factory=list)
    lamps: List[Tuple[int, int]] = field(default_factory=list)
    climb: Optional[Tuple[int, int, int]] = None  # x, y, h
    sky_top: Tuple[int, int, int] = (30, 24, 48)
    diffused: Tuple[int, int, int] = (255, 190, 140)
    diffused_strength: float = 0.36
    ambient: Tuple[int, int, int] = (120, 105, 140)
    ambient_strength: float = 0.34
    weather: str = "leaves"  # leaves | snow | none | dust
    cloud_dir: int = 1
    surface_key: str = "leaf"  # palette key for platform dressing
    water_key: str = "water"


def put(s: Sprite, x: int, y: int, c, layer: str, frame: int = 0) -> None:
    if 0 <= x < s.width and 0 <= y < s.height:
        s.put_pixel(x, y, c, layer=layer, frame=frame)


def build_physics_layout(brief: StageBrief) -> LocationSpec:
    t = brief.tile
    phys = PlatformerPhysics(
        tile=t, jump_height=brief.jump_height, jump_gap=brief.jump_gap,
        player_w=12, player_h=16,
    )
    loc = make_platformer_room(
        name=brief.name, width=brief.width, height=brief.height, tile=t,
        theme=brief.theme, style="ascent", platforms=0, seed=brief.seed,
        game_ready=False, physics=phys,
    )
    loc.solids = [r for r in loc.solids if r.y == 0 or r.x == 0 or r.x >= brief.width - t]
    loc.one_way.clear(); loc.hazards.clear(); loc.kill_zones.clear()
    loc.props.clear(); loc.windows.clear(); loc.lamps.clear()
    loc.exits.clear(); loc.climbables.clear(); loc.checkpoints.clear()

    gy = loc.ground_y
    W, H = brief.width, brief.height

    if brief.pit:
        px, pw = brief.pit
        pit = Rect(px * t, gy, pw * t, H - gy)
        loc.hazards.append(pit)
        loc.kill_zones.append(Rect(pit.x, H - t, pit.w, t))
        loc.solids.append(Rect(t, gy, pit.x - t, H - gy))
        loc.solids.append(Rect(pit.x + pit.w, gy, W - t - (pit.x + pit.w), H - gy))
        if brief.bridge:
            loc.solids.append(Rect(pit.x - t // 2, gy - t + 2, pit.w + t, 8))
    else:
        loc.solids.append(Rect(t, gy, W - 2 * t, H - gy))

    meta = []
    for led in brief.ledges:
        h = t if led.solid else t // 2 + 2
        r = Rect(led.x * t if led.x < 40 else led.x, led.y, led.w * t if led.w < 40 else led.w, h)
        # Support both tile-index and pixel coords: if y looks like tile index
        if led.y < gy // t:
            r = Rect(led.x * t, gy - led.y * t, led.w * t, h)
        (loc.solids if led.solid else loc.one_way).append(r)
        meta.append((r, led.style, led.solid))
    loc._ledge_meta = meta  # type: ignore

    loc.windows = list(brief.windows) or [(W // 3, 24), (2 * W // 3, 22)]
    loc.lamps = list(brief.lamps)
    if not loc.lamps:
        loc.lamps = [(t * 3, gy - t * 2 - 8), (W - t * 4, gy - 24)]

    spawn = (t * 2 + 8, gy - t * 2)
    # If first ledge near spawn, put feet on it
    if meta:
        r0 = meta[0][0]
        if r0.x <= t * 3:
            spawn = (r0.x + r0.w // 2, r0.y)
    loc.player_spawn = spawn
    loc.checkpoints = [spawn]
    if len(meta) > 2:
        rt = meta[-1][0]
        loc.checkpoints.append((rt.x + rt.w // 2, rt.y))

    loc.exits.append({
        "name": "east", "x": W - t * 2, "y": gy - t * 2,
        "w": t, "h": t * 2, "target": "next",
    })
    loc.props = [
        Prop("torch", lx, ly + 4, {"kind": "lamp"}) for lx, ly in loc.lamps
    ]
    loc.props.append(Prop("door", W - t * 2, gy - t * 2, {"exit": "east"}))
    loc.props.append(Prop("chest", loc.checkpoints[-1][0], loc.checkpoints[-1][1], {}))
    loc.props.append(Prop("checkpoint", spawn[0], spawn[1], {}))

    if brief.climb:
        cx, cy_tiles, ch = brief.climb
        loc.climbables.append(Rect(cx * t, gy - cy_tiles * t, 6, ch * t))

    loc.parallax = list(PARALLAX_STACK)
    return ensure_game_ready(loc, phys)


def _draw_parallax(s: Sprite, loc: LocationSpec, brief: StageBrief, pal: dict) -> None:
    bg = pal["bg"]
    haze = pal.get("haze", [bg[min(1, len(bg) - 1)]])[0]
    top = (*brief.sky_top, 255)
    s.stamp(soft_sky_pixels(loc.width, loc.height, top, bg[-1], haze=haze, haze_y=0.4, haze_width=0.4),
            layer="sky", frame=0)
    s.stamp(soft_silhouette_band(loc.width, loc.height // 3 + 6, (bg[0][0] + 8, bg[0][1] + 6, bg[0][2] + 10, 145),
                                 height=38, seed=brief.seed, blobs=12), layer="bg_far", frame=0)
    rng = random.Random(brief.seed + 3)
    # bg_mid blobs
    for i in range(5):
        cx = 30 + i * 60 + rng.randint(-6, 6)
        for dy in range(20):
            for dx in range(-18 + dy // 2, 18 - dy // 2):
                put(s, cx + dx, 50 + dy, (bg[0][0] + 20, bg[0][1] + 14, bg[0][2] + 18, 150), "bg_mid")
    # bg_near pillars
    for cx in (70, 160, 250):
        for y in range(40, loc.ground_y - 8):
            put(s, cx, y, (pal["stone"][0][0] + 15, pal["stone"][0][1] + 10, pal["stone"][0][2] + 12, 200), "bg_near")
            put(s, cx + 1, y, (pal["stone"][1][0], pal["stone"][1][1], pal["stone"][1][2], 200), "bg_near")
    # close_bg soft columns
    for cx in (100, 200):
        for y in range(28, loc.ground_y - 4):
            put(s, cx, y, (pal["stone"][1][0] + 10, pal["stone"][1][1] + 8, pal["stone"][1][2] + 8, 220), "close_bg")


def _draw_world(s: Sprite, loc: LocationSpec, brief: StageBrief, pal: dict) -> None:
    stone = pal["stone"]
    surface = pal.get(brief.surface_key) or pal.get("leaf") or pal.get("moss") or pal.get("snow")
    gy = loc.ground_y
    t = loc.tile

    for r in loc.solids:
        if r.y >= gy:
            stamp_platform(s, r.x, r.y, r.w, r.h, stone, surface=surface, style="dirt", seed=r.x)
        elif r.y == 0 or r.x == 0 or r.x >= loc.width - t:
            stamp_platform(s, r.x, r.y, r.w, min(r.h, loc.height - r.y), stone, style="stone", seed=r.x + r.y)
        elif r.h <= 10 and r.y < gy and r.w > t:
            stamp_platform(s, r.x, r.y, r.w, r.h, stone, surface=surface, style="wood", seed=r.x)

    for r, style, solid in getattr(loc, "_ledge_meta", []):
        surf = surface if (not solid or style in ("dirt", "snow")) else None
        stamp_platform(s, r.x, r.y, r.w, r.h, stone, surface=surf, style=style, seed=r.x + r.y)

    for r in loc.one_way:
        # may already be in meta
        if not any(r.x == m[0].x and r.y == m[0].y for m in getattr(loc, "_ledge_meta", [])):
            stamp_platform(s, r.x, r.y, r.w, r.h, stone, surface=surface, style="dirt", seed=r.x)

    water_pal = pal.get(brief.water_key) or pal.get("water")
    if water_pal:
        for r in loc.hazards:
            stamp_water(s, r.x, r.y, r.w, r.h, water_pal, frame=0, frames=brief.frames,
                        body_layer="world", surface_layer="props", glow_layer="glow")


def _draw_props(s: Sprite, loc: LocationSpec, pal: dict) -> None:
    gold = pal.get("gold", [(180, 140, 60, 255), (220, 180, 80, 255)])
    accent = pal.get("accent", [(160, 50, 40, 255)])
    for p in loc.props:
        if p.kind == "torch":
            put(s, p.x, p.y, pal["stone"][1], "props")
            put(s, p.x, p.y - 1, gold[0], "props")
            put(s, p.x, p.y - 2, (255, 200, 100, 255), "props")
        elif p.kind == "chest":
            for dy in range(5):
                for dx in range(-4, 5):
                    put(s, p.x + dx, p.y - dy, gold[0] if dy > 2 else gold[min(1, len(gold) - 1)], "props")
        elif p.kind == "door":
            for y in range(p.y, p.y + loc.tile * 2):
                for x in range(p.x, p.x + loc.tile):
                    put(s, x, y, pal["stone"][0], "props")
        elif p.kind == "checkpoint":
            put(s, p.x, p.y - 1, gold[min(1, len(gold) - 1)], "props")
    for r in loc.climbables:
        moss = pal.get("moss", accent)
        for y in range(r.y, r.y + r.h):
            put(s, r.x, y, moss[0], "props")


def _draw_fg(s: Sprite, loc: LocationSpec, pal: dict) -> None:
    surf = pal.get("leaf") or pal.get("moss") or pal.get("snow") or pal["stone"][2:]
    rng = random.Random(9)
    for x in list(range(0, 26, 5)) + list(range(loc.width - 26, loc.width, 5)):
        if isinstance(surf, list) and len(surf) >= 2 and "leaf" in pal:
            s.stamp(leaf_cluster_pixels(x, 6 + rng.randint(0, 8), pal["leaf"], radius=5, count=8, seed=x),
                    layer="fg", frame=0)
        else:
            for dy in range(3):
                put(s, x, loc.ground_y - 2 - dy, surf[0] if isinstance(surf, list) else surf, "fg")


def _make_lights(loc: LocationSpec, brief: StageBrief) -> LightingSetup:
    setup = LightingSetup(time_of_day=brief.time)
    apply_time_of_day(setup)
    setup.ambient = brief.ambient
    setup.ambient_strength = brief.ambient_strength
    for i, (wx, wy) in enumerate(loc.windows):
        setup.add_shaft(wx, wy, aim_deg=95 + (i - 1) * 8, length=loc.height - wy - 20,
                        cone_deg=34, color=brief.diffused, intensity=0.4, flicker_seed=10 + i)
    for i, (lx, ly) in enumerate(loc.lamps):
        setup.add_point(lx, ly, color=(255, 160, 80), intensity=0.95, radius=24, flicker_seed=40 + i)
    setup.add_point(loc.width // 2, loc.ground_y - 2, color=(160, 140, 120), intensity=0.2,
                    radius=loc.width * 0.4, flicker_seed=0)
    return setup


def render_stage(brief: StageBrief, out_dir: Path) -> Tuple[Sprite, LocationSpec, Dict]:
    loc = build_physics_layout(brief)
    pal = theme_colors(loc.theme)
    s = Sprite(loc.width, loc.height)
    for L in PARALLAX_STACK:
        s.add_layer(L["name"])
    s.add_layer("shade", blend_mode="multiply", opacity=100)
    s.add_layer("beams", blend_mode="screen")
    s.add_layer("glow", blend_mode="addition")
    s.add_layer("fx_a", blend_mode="normal")
    s.add_layer("fx_b", blend_mode="screen")

    for _ in range(1, brief.frames):
        s.add_frame(100)

    _draw_parallax(s, loc, brief, pal)
    _draw_world(s, loc, brief, pal)
    _draw_props(s, loc, pal)
    _draw_fg(s, loc, pal)

    # copy static
    static = ["sky", "bg_far", "bg_mid", "bg_near", "close_bg", "world", "props", "fg", "shade"]
    for fi in range(1, brief.frames):
        for name in static:
            layer = s._resolve_layer(name)
            src = layer.cels[0]
            if src:
                layer.cels[fi] = Cel(x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels))

    # weather fields
    weather_frames = None
    cloud_frames = bake_drift_frames(
        make_cloud_field(loc.width, loc.height, count=3, seed=brief.seed, direction=brief.cloud_dir, fg=False),
        brief.frames, 1,
    )
    if brief.weather == "leaves" and "leaf" in pal:
        weather_frames = bake_drift_frames(
            make_leaf_field(loc.width, loc.height, count=22, seed=brief.seed + 1, colors=pal["leaf"]),
            brief.frames, 1,
        )
    elif brief.weather == "snow" and "snow" in pal:
        weather_frames = bake_drift_frames(
            make_snow_field(loc.width, loc.height, count=32, seed=brief.seed + 1, color=pal["snow"][1]),
            brief.frames, 1,
        )

    setup = _make_lights(loc, brief)
    for f in range(brief.frames):
        for fx in ("shade", "beams", "glow", "fx_a", "fx_b"):
            s.ensure_cel(fx, f).clear()
        stamp_diffused(s, color=brief.diffused, strength=brief.diffused_strength, frame=f, open_sky=0.6)
        stamp_lighting(s, setup, frame=f, stamp_shade=(f == 0))
        if f > 0:
            src = s._resolve_layer("shade").cels[0]
            if src:
                s._resolve_layer("shade").cels[f] = Cel(x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels))
        water_pal = pal.get(brief.water_key) or pal.get("water")
        if water_pal:
            for r in loc.hazards:
                stamp_water(s, r.x, r.y, r.w, r.h, water_pal, frame=f, frames=brief.frames,
                            body_layer="world", surface_layer="props", glow_layer="glow")
        s.stamp(cloud_frames[f], layer="fx_b", frame=f)
        if weather_frames:
            s.stamp(weather_frames[f], layer="fx_a", frame=f)
        s.set_frame_duration(f, 100)

    s.add_tag("ambient", 0, brief.frames - 1, direction="forward")

    out_dir.mkdir(parents=True, exist_ok=True)
    s.save(out_dir / f"{brief.name}.aseprite")
    s.preview(out_dir / f"{brief.name}.png", scale=2, frame=0, background=(8, 6, 12, 255))
    s.preview_gif(out_dir / f"{brief.name}.gif", scale=2, background=(8, 6, 12, 255),
                  frames=list(range(brief.frames)))
    game = loc.export_game()
    game["title"] = brief.title
    game["prompt"] = brief.prompt
    game["parallax"] = list(PARALLAX_STACK)
    game["ambient"] = {"frames": brief.frames, "direction": "forward", "duration_ms": 100}
    game["physics_brief"] = {
        "jump_height": brief.jump_height,
        "jump_gap": brief.jump_gap,
        "tile": brief.tile,
    }
    (out_dir / f"{brief.name}_game.json").write_text(json.dumps(game, indent=2))
    return s, loc, game


# ---------------------------------------------------------------------------
# Preset briefs
# ---------------------------------------------------------------------------

def preset_stages() -> List[StageBrief]:
    """Four new physics-validated locations."""
    return [
        StageBrief(
            name="saltspire_coast",
            theme="rooftop",
            title="Saltspire Coast",
            prompt="Windy coastal cliffs — salt stone, sea pit, linear traverse, cool daylight shafts.",
            seed=71,
            time="day",
            jump_height=48, jump_gap=56,
            pit=(8, 4),
            ledges=[
                Ledge(2, 2, 3, True, "stone"),
                Ledge(5, 3, 2, False, "stone"),
                Ledge(12, 2, 3, True, "stone"),
                Ledge(15, 3, 2, True, "stone"),
                Ledge(10, 5, 3, False, "wood"),
                Ledge(4, 5, 2, True, "stone"),
                Ledge(13, 6, 2, True, "stone"),
            ],
            windows=[(90, 20), (210, 18)],
            lamps=[(48, 100), (260, 100)],
            climb=(8, 6, 4),
            sky_top=(50, 70, 110),
            diffused=(200, 220, 245),
            diffused_strength=0.34,
            ambient=(150, 170, 200),
            ambient_strength=0.22,
            weather="none",
            surface_key="stone",
            water_key="water",
        ),
        StageBrief(
            name="gloomroot_cavern",
            theme="cave",
            title="Gloomroot Cavern",
            prompt="Bioluminescent cave ascent — wet stone, deep pit, climb vine, magic-green lamps.",
            seed=82,
            time="night",
            jump_height=48, jump_gap=52,
            pit=(7, 5),
            ledges=[
                Ledge(2, 2, 3, True, "stone"),
                Ledge(5, 3, 2, False, "dirt"),
                Ledge(12, 2, 3, True, "stone"),
                Ledge(15, 4, 2, True, "stone"),
                Ledge(9, 5, 3, False, "dirt"),
                Ledge(3, 6, 2, True, "stone"),
                Ledge(12, 7, 3, True, "stone"),
                Ledge(6, 8, 2, False, "dirt"),
            ],
            windows=[(100, 22), (200, 26)],
            lamps=[(44, 100), (180, 70), (270, 110)],
            climb=(7, 8, 5),
            sky_top=(16, 12, 22),
            diffused=(100, 200, 160),
            diffused_strength=0.28,
            ambient=(70, 90, 110),
            ambient_strength=0.5,
            weather="dust",
            surface_key="accent",
            water_key="water",
        ),
        StageBrief(
            name="ashen_ramparts",
            theme="castle",
            title="Ashen Ramparts",
            prompt="Burned castle battlements — brick platforms, banner hall gap, dusk gold light.",
            seed=93,
            time="dusk",
            jump_height=48, jump_gap=56,
            pit=(9, 3),
            ledges=[
                Ledge(2, 2, 3, True, "stone"),
                Ledge(5, 3, 2, False, "stone"),
                Ledge(12, 2, 3, True, "stone"),
                Ledge(15, 4, 2, True, "stone"),
                Ledge(8, 5, 3, True, "stone"),
                Ledge(3, 6, 2, False, "wood"),
                Ledge(11, 7, 3, True, "stone"),
            ],
            windows=[(80, 26), (160, 22), (240, 26)],
            lamps=[(50, 100), (200, 80), (280, 110)],
            climb=(6, 7, 5),
            sky_top=(40, 28, 36),
            diffused=(255, 170, 110),
            diffused_strength=0.38,
            ambient=(110, 90, 100),
            ambient_strength=0.4,
            weather="none",
            surface_key="gold",
            water_key="water",
        ),
        StageBrief(
            name="moonfen_marsh",
            theme="forest",
            title="Moonfen Marsh",
            prompt="Moonlit marsh — moss platforms, wide fen water, mist clouds, cool night shafts.",
            seed=104,
            time="night",
            jump_height=48, jump_gap=56,
            pit=(6, 7),
            ledges=[
                Ledge(2, 2, 3, True, "dirt"),
                Ledge(5, 3, 2, False, "dirt"),
                Ledge(13, 2, 3, True, "dirt"),
                Ledge(16, 3, 2, False, "wood"),
                Ledge(10, 5, 3, False, "dirt"),
                Ledge(4, 6, 2, True, "dirt"),
                Ledge(14, 7, 2, True, "wood"),
                Ledge(8, 8, 3, False, "dirt"),
            ],
            windows=[(70, 20), (180, 18), (260, 22)],
            lamps=[(48, 100), (170, 70), (270, 100)],
            climb=(9, 8, 5),
            sky_top=(20, 28, 48),
            diffused=(140, 180, 220),
            diffused_strength=0.32,
            ambient=(80, 100, 140),
            ambient_strength=0.48,
            weather="leaves",
            surface_key="leaf",
            water_key="water",
        ),
    ]

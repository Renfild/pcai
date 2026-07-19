"""Looping ambient FX — spawn/despawn, no mid-screen wrap.

Clouds, leaves, snow, dust: travel ONE direction, exit off-screen, respawn
off-screen on the opposite side. Never use modulo wrap across the playfield
(that reads as a teleport and looks broken).

Also: multi-layer platform stamps, improved water (banded volume, soft surface).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

Color = Tuple[int, int, int, int]
Pixel = Tuple[int, int, Color]


def _clamp(v: float, lo: int = 0, hi: int = 255) -> int:
    return max(lo, min(hi, int(round(v))))


def _mix(c0: Color, c1: Color, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    return (
        _clamp(c0[0] + (c1[0] - c0[0]) * t),
        _clamp(c0[1] + (c1[1] - c0[1]) * t),
        _clamp(c0[2] + (c1[2] - c0[2]) * t),
        _clamp(c0[3] + (c1[3] - c0[3]) * t),
    )


# ---------------------------------------------------------------------------
# Drift field — one-way travel + off-screen recycle
# ---------------------------------------------------------------------------

@dataclass
class DriftActor:
    x: float
    y: float
    vx: float
    vy: float
    life: float  # frames until forced recycle (optional)
    kind: str = "cloud"  # cloud | leaf | snow | dust
    scale: float = 1.0
    seed: int = 0
    phase: float = 0.0
    color: Color = (180, 170, 200, 80)


@dataclass
class DriftField:
    actors: List[DriftActor] = field(default_factory=list)
    width: int = 320
    height: int = 176
    direction: int = 1  # +1 = right, -1 = left
    margin: int = 48


def _spawn_cloud(field: DriftField, rng: random.Random, color: Color, fg: bool) -> DriftActor:
    y0, y1 = (int(field.height * 0.55), int(field.height * 0.88)) if fg else (
        int(field.height * 0.06), int(field.height * 0.38)
    )
    speed = rng.uniform(0.35, 0.7) if fg else rng.uniform(0.12, 0.28)
    if field.direction < 0:
        x = field.width + field.margin + rng.uniform(0, 30)
        vx = -speed
    else:
        x = -field.margin - rng.uniform(0, 30)
        vx = speed
    return DriftActor(
        x=x, y=rng.uniform(y0, y1), vx=vx, vy=rng.uniform(-0.02, 0.02),
        life=9999, kind="cloud", scale=rng.uniform(0.85, 1.35) * (1.2 if fg else 0.9),
        seed=rng.randint(0, 9999), phase=rng.random(), color=color,
    )


def _spawn_leaf(field: DriftField, rng: random.Random, colors: Sequence[Color]) -> DriftActor:
    return DriftActor(
        x=rng.uniform(-8, field.width + 8),
        y=-field.margin - rng.uniform(0, 40),
        vx=rng.uniform(-0.15, 0.15) * field.direction,
        vy=rng.uniform(0.45, 1.1),
        life=9999, kind="leaf", scale=1.0,
        seed=rng.randint(0, 9999), phase=rng.random(),
        color=colors[rng.randint(0, len(colors) - 1)],
    )


def _spawn_snow(field: DriftField, rng: random.Random, color: Color) -> DriftActor:
    return DriftActor(
        x=rng.uniform(-4, field.width + 4),
        y=-field.margin - rng.uniform(0, 20),
        vx=rng.uniform(-0.08, 0.08),
        vy=rng.uniform(0.35, 0.85),
        life=9999, kind="snow", scale=1.0,
        seed=rng.randint(0, 9999), phase=rng.random(), color=color,
    )


def make_cloud_field(
    width: int, height: int, count: int = 4, seed: int = 11,
    direction: int = 1, fg: bool = False,
    color: Optional[Color] = None,
) -> DriftField:
    rng = random.Random(seed)
    if color is None:
        color = (36, 28, 44, 65) if fg else (150, 140, 175, 50)
    field = DriftField(width=width, height=height, direction=direction)
    # Stagger initial positions across the path so the first frames aren't empty
    for i in range(count):
        a = _spawn_cloud(field, rng, color, fg)
        # Place along travel axis (still off or on screen, but no wrap)
        span = width + 2 * field.margin
        if direction > 0:
            a.x = -field.margin + (i + 0.5) / count * span * 0.7
        else:
            a.x = width + field.margin - (i + 0.5) / count * span * 0.7
        field.actors.append(a)
    return field


def make_leaf_field(
    width: int, height: int, count: int = 28, seed: int = 5,
    colors: Sequence[Color] = ((140, 40, 36, 255), (190, 70, 40, 255), (220, 130, 50, 255)),
) -> DriftField:
    rng = random.Random(seed)
    field = DriftField(width=width, height=height, direction=1)
    for i in range(count):
        a = _spawn_leaf(field, rng, colors)
        a.y = -field.margin + (i / count) * (height + field.margin)
        field.actors.append(a)
    return field


def make_snow_field(
    width: int, height: int, count: int = 40, seed: int = 3,
    color: Color = (230, 235, 245, 220),
) -> DriftField:
    rng = random.Random(seed)
    field = DriftField(width=width, height=height)
    for i in range(count):
        a = _spawn_snow(field, rng, color)
        a.y = -field.margin + (i / count) * (height + field.margin)
        field.actors.append(a)
    return field


def step_field(field: DriftField, steps: int = 1) -> None:
    """Advance actors; recycle off-screen (never wrap mid-view)."""
    rng = random.Random(field.width * 13 + len(field.actors))
    for _ in range(max(1, steps)):
        for i, a in enumerate(field.actors):
            a.x += a.vx
            # Gentle sway for leaves/snow — small, not a big sine curve across screen
            if a.kind in ("leaf", "snow"):
                a.x += math.sin(a.phase * math.tau + a.y * 0.08) * 0.12
            a.y += a.vy
            a.phase = (a.phase + 0.03) % 1.0

            recycled = False
            if a.kind == "cloud":
                if field.direction > 0 and a.x > field.width + field.margin:
                    recycled = True
                elif field.direction < 0 and a.x < -field.margin:
                    recycled = True
            else:
                if a.y > field.height + field.margin:
                    recycled = True

            if recycled:
                if a.kind == "cloud":
                    fg = a.scale > 1.05
                    field.actors[i] = _spawn_cloud(field, random.Random(a.seed + 17), a.color, fg)
                elif a.kind == "leaf":
                    field.actors[i] = _spawn_leaf(
                        field, random.Random(a.seed + 17),
                        (a.color, a.color, a.color),
                    )
                elif a.kind == "snow":
                    field.actors[i] = _spawn_snow(field, random.Random(a.seed + 17), a.color)


def _cloud_blob(cx: int, cy: int, scale: float, color: Color, seed: int) -> List[Pixel]:
    rng = random.Random(seed)
    pixels: List[Pixel] = []
    r, g, b, a0 = color
    for _ in range(rng.randint(3, 5)):
        lx = cx + int(rng.randint(-10, 10) * scale)
        ly = cy + int(rng.randint(-3, 3) * scale)
        rx = int((7 + rng.randint(0, 7)) * scale)
        ry = int((3 + rng.randint(0, 3)) * scale)
        for dy in range(-ry - 1, ry + 2):
            for dx in range(-rx - 1, rx + 2):
                e = (dx / max(1, rx)) ** 2 + (dy / max(1, ry)) ** 2
                if e > 1.1:
                    continue
                a = _clamp(a0 * (max(0.0, 1.0 - e) ** 1.4))
                if a > 3:
                    pixels.append((lx + dx, ly + dy, (r, g, b, a)))
    return pixels


_LEAF = (
    ((0, 0, 1), (1, 0, 0), (0, 1, 1), (-1, 0, 2)),
    ((0, 0, 1), (1, 0, 0), (-1, 0, 2), (0, -1, 0), (0, 1, 1)),
)


def stamp_field(field: DriftField) -> List[Pixel]:
    pixels: List[Pixel] = []
    for a in field.actors:
        ix, iy = int(round(a.x)), int(round(a.y))
        if a.kind == "cloud":
            pixels.extend(_cloud_blob(ix, iy, a.scale, a.color, a.seed))
        elif a.kind == "leaf":
            shape = _LEAF[a.seed % len(_LEAF)]
            hi = a.color
            mid = (_clamp(hi[0] - 30), _clamp(hi[1] - 20), _clamp(hi[2] - 10), hi[3])
            sh = (_clamp(hi[0] - 60), _clamp(hi[1] - 40), _clamp(hi[2] - 20), hi[3])
            ramp = (hi, mid, sh)
            flip = (a.seed + int(a.y)) % 2 == 0
            for dx, dy, tone in shape:
                sx = -dx if flip else dx
                c = ramp[min(tone, 2)]
                pixels.append((ix + sx, iy + dy, c))
        elif a.kind == "snow":
            pixels.append((ix, iy, a.color))
            if a.seed % 4 == 0:
                pixels.append((ix + 1, iy, (a.color[0], a.color[1], a.color[2], a.color[3] // 2)))
    return pixels


def bake_drift_frames(
    field: DriftField,
    frames: int,
    steps_per_frame: int = 1,
) -> List[List[Pixel]]:
    """Pre-simulate `frames` of one-way drift for an ambient tag (forward, not pingpong)."""
    out = []
    for _ in range(frames):
        out.append(stamp_field(field))
        step_field(field, steps_per_frame)
    return out


# ---------------------------------------------------------------------------
# Water — banded volume, soft surface (no vertical hatch lines)
# ---------------------------------------------------------------------------

def water_volume_pixels(
    x: int, y: int, w: int, h: int,
    palette: Sequence[Color],
    frame: int = 0,
    frames: int = 12,
    seed: int = 2,
) -> Dict[str, List[Pixel]]:
    """Readable water: horizontal depth bands + soft animated surface + foam at banks.

    Avoid vertical caustic streaks (they read as hatch/dirt, not liquid).
    """
    deep = palette[0]
    mid = palette[min(1, len(palette) - 1)]
    bright = palette[min(2, len(palette) - 1)] if len(palette) > 2 else mid
    surface_hi = (_clamp(bright[0] + 70), _clamp(bright[1] + 60), _clamp(bright[2] + 50), 255)
    body: List[Pixel] = []
    surface: List[Pixel] = []
    glow: List[Pixel] = []

    phase = (frame / max(1, frames)) * math.tau

    for row in range(h):
        t = row / max(1, h - 1)
        # Horizontal bands only
        if t < 0.18:
            band = _mix(surface_hi, bright, t / 0.18)
        elif t < 0.45:
            band = _mix(bright, mid, (t - 0.18) / 0.27)
        elif t < 0.75:
            band = _mix(mid, deep, (t - 0.45) / 0.3)
        else:
            band = deep
        for col in range(w):
            # Soft bowl darkening near banks (horizontal volume cue)
            edge = min(col, w - 1 - col) / max(1, w * 0.5)
            edge = max(0.0, min(1.0, edge))
            c = _mix(deep, band, 0.35 + 0.65 * edge)
            # Rare silt speck (not stripes)
            if ((col * 19 + row * 7 + seed) % 23) == 0 and t > 0.3:
                c = _mix(c, mid, 0.35)
            body.append((x + col, y + row, (c[0], c[1], c[2], 255)))

    # Soft surface wave — 2px thick, slow phase
    for col in range(w):
        wave = int(round(math.sin(phase + col * 0.22) * 1.0))
        sy = y + wave
        surface.append((x + col, sy, surface_hi))
        surface.append((x + col, sy + 1, (_clamp(bright[0] + 20), _clamp(bright[1] + 25), _clamp(bright[2] + 30), 200)))
        # Dark meniscus under surface = thickness
        surface.append((x + col, sy + 2, (deep[0], deep[1], deep[2], 180)))
        # Foam near banks
        if col < 3 or col >= w - 3:
            surface.append((x + col, sy - 1, (210, 220, 230, 140)))

    # Specular glints (few, moving horizontally — not vertical shafts)
    for g in range(3):
        gx = x + int((w * (g + 0.5) / 3 + math.sin(phase * 0.7 + g) * 4) % w)
        gy = y + 3 + (g % 2)
        glow.append((gx, gy, (160, 200, 220, 50)))
        glow.append((gx + 1, gy, (140, 180, 200, 30)))

    # Reflection strip above water
    for col in range(w):
        for dy in range(1, 4):
            a = 35 - dy * 10
            if a > 0:
                surface.append((x + col, y - dy, (_clamp(bright[0]), _clamp(bright[1] + 10), _clamp(bright[2] + 20), a)))

    return {"body": body, "surface": surface, "glow": glow}


def stamp_water(sprite, x, y, w, h, palette, frame=0, frames=12,
                body_layer="world", surface_layer="props", glow_layer="glow", **kw):
    layers = water_volume_pixels(x, y, w, h, palette, frame, frames, **kw)
    sprite.stamp(layers["body"], layer=body_layer, frame=frame)
    sprite.stamp(layers["surface"], layer=surface_layer, frame=frame)
    if layers["glow"]:
        sprite.stamp(layers["glow"], layer=glow_layer, frame=frame)


# ---------------------------------------------------------------------------
# Multi-layer platforms
# ---------------------------------------------------------------------------

def platform_layers(
    x: int, y: int, w: int, h: int,
    stone: Sequence[Color],
    surface: Optional[Sequence[Color]] = None,  # leaf/snow/moss dressing
    style: str = "dirt",  # dirt | stone | wood | snow
    seed: int = 0,
) -> Dict[str, List[Pixel]]:
    """Diversified platform: underside + body + top lip + surface dressing + edge nubs.

    Returns {body, detail, top} to stamp on world/props.
    """
    rng = random.Random(seed + x * 3 + y)
    dark = stone[0]
    mid = stone[min(1, len(stone) - 1)]
    lit = stone[min(2, len(stone) - 1)]
    lip = stone[min(3, len(stone) - 1)] if len(stone) > 3 else lit
    body: List[Pixel] = []
    detail: List[Pixel] = []
    top: List[Pixel] = []

    for row in range(h):
        t = row / max(1, h - 1)
        for col in range(w):
            px, py = x + col, y + row
            # Multi-band body
            if row == 0:
                c = lip
            elif t < 0.3:
                c = lit if (col + row + seed) % 5 != 0 else mid
            elif t < 0.7:
                # Tile / dirt clumps
                if style == "stone":
                    c = mid if ((col // 5 + row // 4) % 2) == 0 else dark
                elif style == "wood":
                    c = lit if row % 3 == 1 else mid
                    if col % 6 == 0:
                        c = dark
                else:
                    c = mid if ((col * 3 + row) % 7) < 4 else dark
            else:
                # Underside — darker + overhang shadow
                c = dark
            body.append((px, py, c))

    # Outline (main-layer read)
    for col in range(w):
        body.append((x + col, y, lip))
        body.append((x + col, y + h - 1, dark))
    for row in range(h):
        body.append((x, y + row, dark))
        body.append((x + w - 1, y + row, dark))

    # Underside drip / support nubs
    for col in range(2, w - 2, 4):
        detail.append((x + col, y + h, dark))
        if rng.random() < 0.5:
            detail.append((x + col + 1, y + h, mid))

    # Top lip thickness (2nd highlight row)
    for col in range(w):
        top.append((x + col, y, lip))
        if h > 2:
            top.append((x + col, y + 1, lit))

    # Surface dressing (leaves / snow / moss) — heaps, not flat carpet
    if surface:
        for col in range(w):
            if rng.random() < 0.55:
                c = surface[col % len(surface)]
                top.append((x + col, y - 1, c))
            if rng.random() < 0.2:
                c = surface[(col + 1) % len(surface)]
                top.append((x + col, y - 2, c))
        # Occasional heap
        for hx in range(3, w - 3, max(5, w // 4)):
            if rng.random() < 0.4:
                continue
            for py in range(3):
                for px in range(3):
                    c = surface[min(py, len(surface) - 1)]
                    top.append((x + hx + px - 1, y - 1 - py, c))

    # Edge wear / cracks
    for col in range(1, w - 1, 3):
        if rng.random() < 0.35:
            detail.append((x + col, y + 2, dark))

    return {"body": body, "detail": detail, "top": top}


def stamp_platform(sprite, x, y, w, h, stone, surface=None, style="dirt", seed=0,
                   body_layer="world", detail_layer="props", frame=0):
    layers = platform_layers(x, y, w, h, stone, surface, style, seed)
    sprite.stamp(layers["body"], layer=body_layer, frame=frame)
    sprite.stamp(layers["detail"], layer=detail_layer, frame=frame)
    sprite.stamp(layers["top"], layer=detail_layer, frame=frame)


# ---------------------------------------------------------------------------
# Terraria-style parallax metadata (for engines)
# ---------------------------------------------------------------------------

# scroll: camera multiply — 0 = static sky, 1 = gameplay, >1 = foreground
PARALLAX_STACK = [
    {"name": "sky", "scroll": 0.0, "z": 0, "role": "sky"},
    {"name": "bg_far", "scroll": 0.15, "z": 1, "role": "parallax_far"},
    {"name": "bg_mid", "scroll": 0.35, "z": 2, "role": "parallax_mid"},
    {"name": "bg_near", "scroll": 0.65, "z": 3, "role": "parallax_near"},
    {"name": "close_bg", "scroll": 1.0, "z": 4, "role": "close_bg"},  # room extension, no parallax lag
    {"name": "world", "scroll": 1.0, "z": 5, "role": "main"},
    {"name": "props", "scroll": 1.0, "z": 6, "role": "main"},
    {"name": "fg", "scroll": 1.25, "z": 7, "role": "foreground"},
]


def parallax_layer_names() -> List[str]:
    return [L["name"] for L in PARALLAX_STACK]

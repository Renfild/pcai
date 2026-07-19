"""Atmosphere FX — soft backgrounds, diffused light, clouds, water, leaves.

Stamp onto parallax / FX layers. Designed for game-ready platformer stages:
  far/sky  → soft depth + distant clouds
  beams    → diffused fill (screen)
  glow     → soft bounce / caustic highlights (addition)
  near/fg  → foreground clouds / overhang
  world    → volumetric water body
  mid/fx   → leaf clusters, litter, falling leaves with volume
"""

from __future__ import annotations

import math
import random
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Color = Tuple[int, int, int, int]
Pixel = Tuple[int, int, Color]


def _clamp(v: float, lo: int = 0, hi: int = 255) -> int:
    return max(lo, min(hi, int(round(v))))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _mix(c0: Color, c1: Color, t: float, a: Optional[int] = None) -> Color:
    return (
        _clamp(_lerp(c0[0], c1[0], t)),
        _clamp(_lerp(c0[1], c1[1], t)),
        _clamp(_lerp(c0[2], c1[2], t)),
        _clamp(a if a is not None else _lerp(c0[3], c1[3], t)),
    )


# ---------------------------------------------------------------------------
# Soft background / depth
# ---------------------------------------------------------------------------

def soft_sky_pixels(
    width: int,
    height: int,
    top: Color,
    bottom: Color,
    haze: Optional[Color] = None,
    haze_y: float = 0.55,
    haze_width: float = 0.35,
) -> List[Pixel]:
    """Vertical gradient with optional soft mid haze band (atmospheric depth)."""
    pixels: List[Pixel] = []
    for y in range(height):
        t = y / max(1, height - 1)
        base = _mix(top, bottom, t)
        if haze is not None:
            # Soft Gaussian-ish band around haze_y
            d = abs(t - haze_y) / max(0.05, haze_width)
            h = math.exp(-d * d * 2.2)
            if h > 0.02:
                base = _mix(base, haze, h * 0.55)
        for x in range(width):
            # Subtle horizontal vignette so BG feels soft, not flat
            vx = abs(x - width / 2) / (width / 2)
            edge = 1.0 - 0.08 * max(0.0, vx - 0.4)
            c = (
                _clamp(base[0] * edge),
                _clamp(base[1] * edge),
                _clamp(base[2] * edge),
                255,
            )
            pixels.append((x, y, c))
    return pixels


def soft_silhouette_band(
    width: int,
    horizon_y: int,
    color: Color,
    height: int = 28,
    seed: int = 1,
    blobs: int = 14,
) -> List[Pixel]:
    """Soft distant treeline / mountain silhouette (low contrast)."""
    rng = random.Random(seed)
    pixels: List[Pixel] = []
    # Base fill
    for y in range(max(0, horizon_y - height), horizon_y + 2):
        fade = 1.0 - (horizon_y - y) / max(1, height)
        a = _clamp(color[3] * (0.35 + 0.65 * fade))
        for x in range(width):
            pixels.append((x, y, (color[0], color[1], color[2], a)))
    # Soft canopy blobs
    for i in range(blobs):
        cx = int(width * (i + 0.5) / blobs) + rng.randint(-6, 6)
        cy = horizon_y - rng.randint(height // 3, height)
        rx = rng.randint(10, 22)
        ry = rng.randint(6, 14)
        for dy in range(-ry, ry + 1):
            for dx in range(-rx, rx + 1):
                e = (dx * dx) / max(1, rx * rx) + (dy * dy) / max(1, ry * ry)
                if e > 1.0:
                    continue
                soft = (1.0 - e) ** 1.4
                a = _clamp(color[3] * (0.4 + 0.5 * soft))
                pixels.append((cx + dx, cy + dy, (color[0], color[1], color[2], a)))
    return pixels


# ---------------------------------------------------------------------------
# Diffused light
# ---------------------------------------------------------------------------

def diffused_fill_pixels(
    width: int,
    height: int,
    color: Tuple[int, int, int] = (255, 200, 140),
    strength: float = 0.35,
    bias_y: float = 0.35,
    seed: int = 0,
) -> List[Pixel]:
    """Soft full-frame screen fill — diffused canopy/sky light, not hard shafts.

    Stamp on `beams` (screen). strength 0..1.
    """
    rng = random.Random(seed)
    # A few large soft patches instead of uniform wash
    patches = []
    for _ in range(5):
        patches.append((
            rng.uniform(0.1, 0.9) * width,
            rng.uniform(0.05, bias_y + 0.25) * height,
            rng.uniform(width * 0.25, width * 0.55),
            rng.uniform(height * 0.2, height * 0.45),
            rng.uniform(0.6, 1.0),
        ))
    cr, cg, cb = color
    pixels: List[Pixel] = []
    # Sample every pixel once, accumulate soft contribution
    for y in range(height):
        # Brighter toward top / open sky
        sky = 1.0 - (y / max(1, height - 1))
        for x in range(width):
            acc = 0.0
            for cx, cy, rx, ry, w in patches:
                e = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if e < 1.0:
                    acc += w * (1.0 - e) ** 2
            acc = min(1.0, acc * 0.55 + sky * 0.25)
            a = _clamp(90 * strength * acc)
            if a > 2:
                pixels.append((x, y, (cr, cg, cb, a)))
    return pixels


def soft_bounce_pixels(
    cx: float,
    cy: float,
    radius: float,
    color: Tuple[int, int, int] = (200, 160, 120),
    intensity: float = 0.4,
    falloff: float = 1.6,
) -> List[Pixel]:
    """Very soft ground-bounce / reflected fill for addition or screen."""
    pixels: List[Pixel] = []
    cr, cg, cb = color
    r_i = int(math.ceil(radius))
    for y in range(int(cy) - r_i // 3, int(cy) + r_i + 1):
        for x in range(int(cx) - r_i, int(cx) + r_i + 1):
            # Flatten vertically (ground bounce ellipse)
            dx = (x - cx) / radius
            dy = (y - cy) / (radius * 0.45)
            d = math.hypot(dx, dy)
            if d > 1.0:
                continue
            t = (1.0 - d) ** falloff
            a = _clamp(160 * t * intensity)
            if a > 0:
                pixels.append((x, y, (cr, cg, cb, a)))
    return pixels


# ---------------------------------------------------------------------------
# Clouds (background + foreground)
# ---------------------------------------------------------------------------

def cloud_pixels(
    cx: int,
    cy: int,
    scale: float = 1.0,
    color: Color = (180, 170, 200, 90),
    seed: int = 0,
    soft: bool = True,
) -> List[Pixel]:
    """Soft multi-lobe cloud. soft=True → feathered alpha; False → flatter."""
    rng = random.Random(seed)
    lobes = []
    n = rng.randint(3, 5)
    for i in range(n):
        lobes.append((
            cx + int(rng.randint(-10, 10) * scale),
            cy + int(rng.randint(-4, 3) * scale),
            int((8 + rng.randint(0, 8)) * scale),
            int((4 + rng.randint(0, 4)) * scale),
        ))
    pixels: List[Pixel] = []
    r, g, b, a0 = color
    for lx, ly, rx, ry in lobes:
        for dy in range(-ry - 1, ry + 2):
            for dx in range(-rx - 1, rx + 2):
                e = (dx / max(1, rx)) ** 2 + (dy / max(1, ry)) ** 2
                if e > 1.15:
                    continue
                if soft:
                    edge = max(0.0, 1.0 - e)
                    a = _clamp(a0 * (edge ** 1.3))
                else:
                    a = a0 if e <= 1.0 else _clamp(a0 * 0.35)
                if a > 2:
                    # Slight top highlight
                    if dy < -ry * 0.2:
                        rr, gg, bb = _clamp(r + 18), _clamp(g + 14), _clamp(b + 12)
                    elif dy > ry * 0.35:
                        rr, gg, bb = _clamp(r - 20), _clamp(g - 16), _clamp(b - 10)
                    else:
                        rr, gg, bb = r, g, b
                    pixels.append((lx + dx, ly + dy, (rr, gg, bb, a)))
    return pixels


def drifting_clouds_frame(
    width: int,
    height: int,
    frame: int,
    frames: int = 12,
    layer: str = "fg",  # fg | bg
    seed: int = 11,
    count: int = 4,
    color: Optional[Color] = None,
    direction: int = 1,
) -> List[Pixel]:
    """One-way drifting clouds (spawn/despawn off-screen — no mid-screen wrap).

    Prefer loop_fx.make_cloud_field + bake_drift_frames for multi-frame builds.
    This helper simulates `frame` steps from a fresh field (deterministic).
    """
    from loop_fx import make_cloud_field, step_field, stamp_field
    field = make_cloud_field(
        width, height, count=count, seed=seed, direction=direction,
        fg=(layer == "fg"), color=color,
    )
    for _ in range(frame):
        step_field(field, 1)
    return stamp_field(field)


# ---------------------------------------------------------------------------
# Volumetric water
# ---------------------------------------------------------------------------

def water_volume_pixels(
    x: int,
    y: int,
    w: int,
    h: int,
    palette: Sequence[Color],
    frame: int = 0,
    frames: int = 12,
    foam: bool = True,
    caustics: bool = True,
    reflection: bool = True,
    seed: int = 2,
) -> Dict[str, List[Pixel]]:
    """Banded volumetric water — see loop_fx.water_volume_pixels (no vertical hatch)."""
    from loop_fx import water_volume_pixels as _wv
    return _wv(x, y, w, h, palette, frame=frame, frames=frames, seed=seed)


def stamp_water(
    sprite,
    x: int, y: int, w: int, h: int,
    palette: Sequence[Color],
    frame: int = 0,
    frames: int = 12,
    body_layer: str = "world",
    surface_layer: str = "mid",
    glow_layer: str = "glow",
    **kw,
) -> None:
    from loop_fx import stamp_water as _sw
    _sw(sprite, x, y, w, h, palette, frame=frame, frames=frames,
        body_layer=body_layer, surface_layer=surface_layer, glow_layer=glow_layer)


# ---------------------------------------------------------------------------
# Leaves with volume
# ---------------------------------------------------------------------------

# Tiny leaf shapes (dx, dy) relative — mid + highlight + shadow encoded by value
_LEAF_SHAPES = (
    # teardrop
    ((0, 0, 1), (1, 0, 0), (0, 1, 1), (-1, 0, 2), (0, -1, 0)),
    # diamond
    ((0, 0, 1), (1, 0, 0), (-1, 0, 2), (0, 1, 1), (0, -1, 0), (1, -1, 0)),
    # oval
    ((0, 0, 1), (1, 0, 0), (-1, 0, 2), (0, 1, 2), (1, 1, 1), (-1, -1, 0)),
)


def leaf_sprite_pixels(
    cx: int,
    cy: int,
    colors: Sequence[Color],
    shape: int = 0,
    flip: bool = False,
    alpha: int = 255,
) -> List[Pixel]:
    """Single leaf with highlight (0) / mid (1) / shadow (2) volume."""
    shape = _LEAF_SHAPES[shape % len(_LEAF_SHAPES)]
    hi = colors[min(2, len(colors) - 1)]
    mid = colors[min(1, len(colors) - 1)]
    sh = colors[0]
    ramp = (hi, mid, sh)
    pixels: List[Pixel] = []
    for dx, dy, tone in shape:
        sx = -dx if flip else dx
        c = ramp[tone]
        pixels.append((cx + sx, cy + dy, (c[0], c[1], c[2], alpha)))
    return pixels


def leaf_cluster_pixels(
    cx: int,
    cy: int,
    colors: Sequence[Color],
    radius: int = 10,
    count: int = 18,
    seed: int = 0,
) -> List[Pixel]:
    """Dense canopy cluster with darker underside for volume."""
    rng = random.Random(seed)
    pixels: List[Pixel] = []
    for i in range(count):
        ang = rng.uniform(0, math.tau)
        d = radius * math.sqrt(rng.random())
        lx = int(cx + math.cos(ang) * d)
        ly = int(cy + math.sin(ang) * d * 0.75)
        # Underside darker
        local = list(colors)
        if ly > cy:
            local = [colors[0], colors[0], colors[min(1, len(colors) - 1)]]
        pixels.extend(leaf_sprite_pixels(
            lx, ly, local, shape=rng.randint(0, 2), flip=rng.random() < 0.5,
            alpha=rng.choice([200, 230, 255]),
        ))
    return pixels


def leaf_litter_pixels(
    x: int,
    y: int,
    w: int,
    colors: Sequence[Color],
    density: float = 0.55,
    seed: int = 0,
    heaps: bool = True,
) -> List[Pixel]:
    """Scattered leaves along a platform top — heaps give volume, not a flat carpet."""
    rng = random.Random(seed + x * 13 + y)
    pixels: List[Pixel] = []
    for i in range(x, x + w):
        if rng.random() > density:
            continue
        pixels.extend(leaf_sprite_pixels(
            i, y - rng.randint(0, 1),
            colors, shape=rng.randint(0, 2), flip=rng.random() < 0.5,
            alpha=rng.choice([180, 220, 255]),
        ))
        if rng.random() < 0.25:
            pixels.append((i, y + 1, (colors[0][0], colors[0][1], colors[0][2], 160)))
    if heaps:
        # Occasional multi-layer piles (shadow base + mid + highlight top)
        for hx in range(x + 2, x + w - 2, max(4, w // 5)):
            if rng.random() < 0.35:
                continue
            pile_w = rng.randint(3, 6)
            for py in range(3):
                for px in range(pile_w):
                    tone = 0 if py == 2 else (1 if py == 1 else 2)
                    c = colors[min(tone, len(colors) - 1)] if tone < 2 else colors[0]
                    if tone == 0:
                        c = colors[min(2, len(colors) - 1)]
                    elif tone == 1:
                        c = colors[min(1, len(colors) - 1)]
                    pixels.append((hx + px - pile_w // 2, y - py - 1, (c[0], c[1], c[2], 255)))
            # Side shadow
            pixels.append((hx - pile_w // 2 - 1, y - 1, (colors[0][0], colors[0][1], colors[0][2], 200)))
    return pixels


def falling_leaves_frame(
    width: int,
    height: int,
    frame: int,
    frames: int = 12,
    colors: Sequence[Color] = ((140, 40, 36, 255), (190, 70, 40, 255), (220, 130, 50, 255)),
    count: int = 28,
    seed: int = 5,
) -> List[Pixel]:
    """Falling leaves — fall down, despawn below, respawn above (no Y wrap)."""
    from loop_fx import make_leaf_field, step_field, stamp_field
    field = make_leaf_field(width, height, count=count, seed=seed, colors=colors)
    for _ in range(frame):
        step_field(field, 1)
    return stamp_field(field)

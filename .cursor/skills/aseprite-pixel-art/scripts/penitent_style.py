"""Penitent / Cvstodia draw kit — Blasphemous-inspired purist pixel traditions.

Visual rules (The Game Kitchen / Cabeza-adjacent craft):
  - Limited ash–gold–crimson (or snow/bilge) ramps — no neon, no glow-as-substance
  - Main collidables: hard dark outline + lighter walkable lip
  - Close-bg: NO outline, more saturated / flatter (never mistaken for collision)
  - Far: few colors, silhouettes, soft dither
  - FG: margin props only — never cover the player lane
  - Detail on the walkable outer edge; inner fill darker & quieter
  - Religious macabre props: thorns, cages, candles, gold filigree, blood stains

Use with theme keys: penitent | olive_wither | cistern
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Sequence, Tuple

Color = Tuple[int, int, int, int]
Pixel = Tuple[int, int, Color]


def _c(v: float) -> int:
    return max(0, min(255, int(round(v))))


def dither_fill(
    x0: int, y0: int, x1: int, y1: int,
    a: Color, b: Color, axis: str = "y",
) -> List[Pixel]:
    """Classic checker/Bayer-ish dither between two colors (purist gradients)."""
    pixels: List[Pixel] = []
    w = max(1, x1 - x0)
    h = max(1, y1 - y0)
    for y in range(y0, y1):
        for x in range(x0, x1):
            t = ((y - y0) / h) if axis == "y" else ((x - x0) / w)
            # 2x2 Bayer threshold
            threshold = (0.25, 0.75, 1.0, 0.5)[(x & 1) + ((y & 1) << 1)]
            use_b = t > threshold * 0.85 + 0.08
            # Mix: prefer a at low t
            if t < 0.35:
                c = a if ((x + y) & 1) or t < 0.15 else b
            elif t > 0.65:
                c = b if not ((x + y) & 1) or t > 0.85 else a
            else:
                c = b if use_b else a
            pixels.append((x, y, c))
    return pixels


def stone_block(
    x: int, y: int, w: int, h: int,
    stone: Sequence[Color],
    outline: bool = True,
) -> List[Pixel]:
    """Main-layer stone with quiet inner fill + walkable top lip."""
    pixels: List[Pixel] = []
    dark, mid, lit, lip = stone[0], stone[1], stone[min(2, len(stone) - 1)], stone[min(3, len(stone) - 1)]
    for row in range(h):
        for col in range(w):
            depth = row / max(1, h - 1)
            if row == 0:
                c = lip
            elif depth < 0.25:
                c = lit
            elif depth < 0.6:
                c = mid if ((col // 4 + row // 3) % 2) == 0 else dark
            else:
                c = dark
            # Mortar seams every tile-ish
            if col % 8 == 0 or row % 8 == 7:
                c = dark
            pixels.append((x + col, y + row, c))
    if outline:
        for col in range(w):
            pixels.append((x + col, y, lip))
            pixels.append((x + col, y + h - 1, dark))
        for row in range(h):
            pixels.append((x, y + row, dark))
            pixels.append((x + w - 1, y + row, dark))
    return pixels


def gothic_arch(
    cx: int, top: int, half_w: int, height: int,
    stone: Sequence[Color],
    fill: Optional[Color] = None,
) -> List[Pixel]:
    """Pointed gothic arch recess (stained glass / door niche)."""
    pixels: List[Pixel] = []
    mid = stone[1]
    dark = stone[0]
    for y in range(top, top + height):
        # Pointed: width grows then stays
        progress = (y - top) / max(1, height - 1)
        if progress < 0.45:
            # triangle point
            span = int(half_w * (progress / 0.45))
        else:
            span = half_w
        for dx in range(-span, span + 1):
            c = fill if fill and abs(dx) < span - 1 and y > top + 2 else mid
            if abs(dx) >= span - 1:
                c = dark
            pixels.append((cx + dx, y, c if c else mid))
    return pixels


def stained_glass(
    cx: int, top: int, half_w: int, height: int,
    glass: Sequence[Color],
    stone: Sequence[Color],
) -> List[Pixel]:
    pixels = gothic_arch(cx, top, half_w, height, stone, fill=None)
    # Pane colors inside
    for y in range(top + 3, top + height - 1):
        progress = (y - top) / max(1, height - 1)
        span = half_w if progress >= 0.45 else max(1, int(half_w * (progress / 0.45)))
        for dx in range(-span + 2, span - 1):
            # Lead lines
            if dx == 0 or (y - top) % 5 == 0:
                pixels.append((cx + dx, y, stone[0]))
            else:
                gi = abs(dx + y) % len(glass)
                pixels.append((cx + dx, y, glass[gi]))
    return pixels


def thorn_cluster(cx: int, cy: int, seed: int = 0, color: Color = (50, 36, 30, 255)) -> List[Pixel]:
    rng = random.Random(seed)
    pixels: List[Pixel] = []
    for _ in range(rng.randint(5, 9)):
        ang = rng.uniform(-2.4, -0.7)
        length = rng.randint(4, 9)
        for i in range(length):
            x = cx + int(math.cos(ang) * i)
            y = cy + int(math.sin(ang) * i)
            pixels.append((x, y, color))
            if i == length - 1:
                # barb
                pixels.append((x + 1, y, color))
                pixels.append((x, y - 1, color))
    return pixels


def candle(x: int, y: int, gold: Sequence[Color], wax: Color = (220, 210, 190, 255)) -> List[Pixel]:
    """Small votive — body on props, flame tip for glow layer separately."""
    return [
        (x, y, wax),
        (x, y + 1, wax),
        (x, y + 2, gold[0]),
        (x, y - 1, gold[min(1, len(gold) - 1)]),
        (x, y - 2, (255, 220, 140, 255)),
    ]


def hanging_cage(cx: int, top: int, stone: Sequence[Color], accent: Sequence[Color]) -> List[Pixel]:
    pixels: List[Pixel] = []
    # Chain
    for y in range(top, top + 8):
        if y % 2 == 0:
            pixels.append((cx, y, stone[2]))
    # Cage
    for dy in range(8):
        for dx in range(-4, 5):
            if abs(dx) == 4 or dy in (0, 7) or (dx == 0 and dy > 2):
                pixels.append((cx + dx, top + 8 + dy, stone[1]))
    # Blood drip
    pixels.append((cx, top + 16, accent[0]))
    pixels.append((cx, top + 17, accent[min(1, len(accent) - 1)]))
    return pixels


def gold_filigree_line(x0: int, y: int, w: int, gold: Sequence[Color]) -> List[Pixel]:
    pixels = []
    g0, g1 = gold[0], gold[min(1, len(gold) - 1)]
    for i in range(w):
        c = g1 if i % 4 in (1, 2) else g0
        pixels.append((x0 + i, y, c))
        if i % 6 == 0:
            pixels.append((x0 + i, y - 1, g1))
    return pixels


def blood_stain(cx: int, cy: int, accent: Sequence[Color], seed: int = 0) -> List[Pixel]:
    rng = random.Random(seed)
    pixels = []
    for _ in range(rng.randint(6, 12)):
        dx = rng.randint(-4, 4)
        dy = rng.randint(0, 8)
        pixels.append((cx + dx, cy + dy, accent[dx % len(accent)]))
    return pixels


def column(
    x: int, y0: int, y1: int, stone: Sequence[Color],
    gold: Optional[Sequence[Color]] = None, width: int = 6,
) -> List[Pixel]:
    pixels = []
    half = width // 2
    for y in range(y0, y1):
        for dx in range(-half, half + 1):
            if abs(dx) == half:
                c = stone[0]
            elif dx < 0:
                c = stone[1]
            else:
                c = stone[min(2, len(stone) - 1)]
            pixels.append((x + dx, y, c))
    # Capital
    for dx in range(-half - 1, half + 2):
        pixels.append((x + dx, y0, stone[min(2, len(stone) - 1)]))
        if gold and abs(dx) <= half:
            pixels.append((x + dx, y0 + 1, gold[0]))
    # Base
    for dx in range(-half - 1, half + 2):
        pixels.append((x + dx, y1 - 1, stone[1]))
    return pixels


def olive_tree(
    cx: int, base_y: int, height: int,
    wood: Sequence[Color], foliage: Sequence[Color],
    snow: Optional[Sequence[Color]] = None,
    seed: int = 0,
) -> List[Pixel]:
    """Twisted dead/olive trunk + sparse canopy (wither hills)."""
    rng = random.Random(seed)
    pixels: List[Pixel] = []
    lean = rng.choice([-2, -1, 1, 2])
    for y in range(base_y - height, base_y):
        t = (y - (base_y - height)) / max(1, height)
        half = 1 + int(t * 2)
        xoff = int(lean * (1 - t))
        for dx in range(-half, half + 1):
            c = wood[0] if abs(dx) == half else wood[min(1, len(wood) - 1)]
            pixels.append((cx + dx + xoff, y, c))
    # Sparse leaves / dead branches
    top = base_y - height + 4
    for i in range(8):
        ang = rng.uniform(0, math.tau)
        r = rng.randint(4, 12)
        lx = cx + int(math.cos(ang) * r)
        ly = top + int(math.sin(ang) * r * 0.55)
        pixels.append((lx, ly, foliage[i % len(foliage)]))
        if snow and rng.random() < 0.45:
            pixels.append((lx, ly - 1, snow[0]))
    return pixels


def snow_dither_band(y0: int, y1: int, width: int, snow: Sequence[Color], ground: Color) -> List[Pixel]:
    pixels = []
    h = max(1, y1 - y0)
    for y in range(y0, y1):
        t = (y - y0) / h
        for x in range(width):
            if t < 0.4 or ((x + y) & 1) and t < 0.75:
                pixels.append((x, y, snow[min(1, len(snow) - 1)] if t < 0.5 else snow[0]))
            elif t < 0.9 and (x % 3 == y % 2):
                pixels.append((x, y, snow[0]))
            else:
                pixels.append((x, y, ground))
    return pixels

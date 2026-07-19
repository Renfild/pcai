#!/usr/bin/env python3
"""The Hall of Vigil — enriched ambient great-hall loop.

224x128 · ~29 colors · 8-frame pingpong
Improvements: volumetric god-rays, more mirrors, banners, sconces,
chandelier, wall niches, side rugs, richer vault.
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / ".cursor" / "skills" / "aseprite-pixel-art"
sys.path.insert(0, str(SKILL / "scripts"))

from aseprite_io import Cel, Sprite
from fx_helpers import flicker, radial_glow, wave_curve

OUT = Path(__file__).resolve().parent
W, H = 224, 128
FRAMES = 8

STONE = [
    (22, 24, 30, 255),
    (38, 42, 52, 255),
    (56, 62, 74, 255),
    (80, 88, 102, 255),
    (112, 122, 138, 255),
    (162, 172, 188, 255),
]
CARPET = [
    (48, 12, 18, 255),
    (96, 22, 30, 255),
    (152, 42, 48, 255),
    (208, 78, 68, 255),
]
GOLD = [
    (74, 48, 18, 255),
    (128, 88, 28, 255),
    (190, 150, 52, 255),
    (240, 214, 118, 255),
]
RUBY = [(100, 18, 28, 255), (176, 42, 54, 255), (236, 86, 86, 255)]
SAPPH = [(18, 38, 100, 255), (46, 82, 176, 255), (100, 148, 236, 255)]
EMER = [(18, 78, 44, 255), (42, 148, 82, 255), (86, 210, 128, 255)]
AMBER = [(112, 64, 16, 255), (196, 132, 32, 255), (244, 196, 82, 255)]
BEAM = [(255, 230, 160, 255), (255, 196, 100, 255)]
DUST = (255, 244, 220, 255)

PALETTE = STONE + CARPET + GOLD + RUBY + SAPPH + EMER + AMBER + BEAM + [DUST]
assert 24 <= len(PALETTE) <= 30, len(PALETTE)

# Windows + tint for colored rays
WINDOWS = [
    {"cx": 56, "colors": RUBY, "tint": (255, 130, 120)},
    {"cx": 112, "colors": [EMER[0], SAPPH[1], EMER[2]], "tint": (140, 210, 255)},
    {"cx": 168, "colors": AMBER, "tint": (255, 210, 100)},
]
WIN_TOP, WIN_HALF, WIN_H = 30, 13, 44


def put(s, x, y, c, layer, frame=0):
    if 0 <= x < W and 0 <= y < H:
        s.put_pixel(x, y, c, layer=layer, frame=frame)


def hline(s, x0, x1, y, c, layer, frame=0):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        put(s, x, y, c, layer, frame)


def vline(s, x, y0, y1, c, layer, frame=0):
    for y in range(min(y0, y1), max(y0, y1) + 1):
        put(s, x, y, c, layer, frame)


def fill(s, x0, y0, x1, y1, c, layer, frame=0):
    s.fill_rect(x0, y0, x1, y1, c, layer=layer, frame=frame)


def mix_rgb(a, b, t):
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
        a[3] if len(a) > 3 else 255,
    )


def in_arch(cx, top, half, x, y) -> bool:
    sill = top + WIN_H
    if y < top or y > sill:
        return False
    if y >= top + half:
        return abs(x - cx) < half - 1
    dx = x - cx
    dy = (top + half) - y
    return dx * dx + dy * dy <= (half - 2) * (half - 2)


# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------

def draw_vaulted_wall(s: Sprite) -> None:
    fill(s, 0, 0, W - 1, 78, STONE[2], "wall")
    for y in range(0, 24):
        hline(s, 0, W - 1, y, STONE[0] if y < 12 else STONE[1], "wall")

    # Vault bays with boss stones
    bays = [(0, 48), (48, 96), (96, 144), (144, 192), (192, 224)]
    for x0, x1 in bays:
        cx = (x0 + x1) // 2
        span = (x1 - x0) // 2 - 2
        for t in range(span * 2 + 1):
            dx = t - span
            yy = int(4 + (1 - math.sqrt(max(0, 1 - (dx / max(1, span)) ** 2))) * 20)
            for thick in range(4):
                put(s, cx + dx, yy + thick, STONE[1], "wall")
            put(s, cx + dx, yy, STONE[3], "wall")
            put(s, cx + dx, yy + 3, STONE[0], "wall")
        # Keystone / boss
        put(s, cx, 5, STONE[4], "wall")
        put(s, cx, 6, GOLD[1], "wall")
        put(s, cx - 1, 6, GOLD[0], "wall")
        put(s, cx + 1, 6, GOLD[0], "wall")
        for y in range(20, 29):
            put(s, x0 + 2, y, STONE[1], "wall")
            put(s, x1 - 3, y, STONE[1], "wall")

    # Cornice with dentils
    hline(s, 0, W - 1, 26, STONE[4], "wall")
    hline(s, 0, W - 1, 27, STONE[1], "wall")
    hline(s, 0, W - 1, 28, STONE[5], "wall")
    hline(s, 0, W - 1, 29, STONE[3], "wall")
    for x in range(4, W, 6):
        put(s, x, 27, STONE[0], "wall")
        put(s, x, 28, STONE[4], "wall")

    # Ashlar
    for y in range(30, 78, 7):
        hline(s, 0, W - 1, y, STONE[1], "wall")
        off = 0 if (y // 7) % 2 == 0 else 9
        for x in range(off, W, 18):
            vline(s, x, y + 1, min(y + 6, 77), STONE[1], "wall")
            # Lived-in wear
            if (x + y) % 29 == 0:
                put(s, x + 3, y + 2, STONE[0], "wall")
                put(s, x + 4, y + 3, STONE[0], "wall")
            if (x * 3 + y) % 41 == 0:
                put(s, x + 8, y + 4, STONE[3], "wall")


def draw_side_doorway(s: Sprite, left: bool) -> None:
    """Arched side passage into adjoining corridors."""
    cx = 48 if left else 176
    top, bot, half = 70, 100, 8
    # Recess fill
    for y in range(top, bot + 1):
        for x in range(cx - half, cx + half + 1):
            if y < top + half:
                dx = x - cx
                dy = (top + half) - y
                if dx * dx + dy * dy > half * half:
                    continue
            put(s, x, y, STONE[0], "wall")
        put(s, cx - half, y, STONE[1], "wall")
        put(s, cx + half, y, STONE[3], "wall")
    # Arch highlight
    for t in range(-half, half + 1):
        dy = int(math.sqrt(max(0, half * half - t * t)))
        put(s, cx + t, top + half - dy, STONE[4], "wall")
    # Threshold
    hline(s, cx - half, cx + half, bot, STONE[3], "floor")
    # Tiny warm glow hint from corridor
    put(s, cx, bot - 8, AMBER[0], "fixtures")
    put(s, cx, bot - 10, AMBER[1], "fixtures")


def draw_back_door(s: Sprite) -> None:
    """Deprecated — side doorways used instead."""
    draw_side_doorway(s, True)
    draw_side_doorway(s, False)


def draw_arched_window(s: Sprite, cx: int, colors) -> None:
    top, half, height = WIN_TOP, WIN_HALF, WIN_H
    sill = top + height

    for y in range(top - 2, sill + 3):
        for x in range(cx - half - 3, cx + half + 4):
            inside = in_arch(cx, top, half, x, y)
            near = any(in_arch(cx, top, half, x + ox, y + oy) for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-2, 0), (2, 0)))
            if near and not inside:
                put(s, x, y, STONE[5] if y < top + 10 else STONE[4], "wall")

    for t in range(-half - 1, half + 2):
        dy = int(math.sqrt(max(0, (half + 1) ** 2 - t * t)))
        put(s, cx + t, top + half - dy - 1, STONE[5], "wall")
        put(s, cx + t, top + half - dy - 2, GOLD[1], "wall")  # gold trim on arch

    hline(s, cx - half - 1, cx + half + 1, sill + 1, STONE[5], "wall")
    hline(s, cx - half, cx + half, sill + 2, GOLD[1], "wall")
    hline(s, cx - half + 1, cx + half - 1, sill + 3, STONE[3], "wall")

    for y in range(top, sill + 1):
        for x in range(cx - half, cx + half + 1):
            if not in_arch(cx, top, half, x, y):
                continue
            rel = (y - top) / height
            band = 0 if rel < 0.33 else (1 if rel < 0.66 else 2)
            # Diamond lead came — slightly sparser so color reads
            if ((x + y) % 5 == 0) or ((x - y) % 5 == 0):
                put(s, x, y, STONE[0], "glass")
            else:
                c = colors[band]
                if (x * 5 + y * 3) % 9 == 0:
                    c = colors[min(2, band + 1)]
                put(s, x, y, c, "glass")

    for y in range(top + 2, sill + 1):
        if in_arch(cx, top, half, cx, y):
            put(s, cx, y, STONE[4], "wall")
            put(s, cx - 1, y, GOLD[0], "wall")
    hline(s, cx - half + 2, cx + half - 2, top + height // 2, STONE[4], "wall")
    # Gold corner bosses on sill
    put(s, cx - half, sill + 1, GOLD[2], "wall")
    put(s, cx + half, sill + 1, GOLD[2], "wall")


def draw_oval_mirror(s: Sprite, cx: int, cy: int, rw: int = 9, rh: int = 15, fancy: bool = True) -> None:
    for y in range(cy - rh - 4, cy + rh + 5):
        for x in range(cx - rw - 4, cx + rw + 5):
            nx = (x - cx) / (rw + 2.4)
            ny = (y - cy) / (rh + 2.4)
            d = nx * nx + ny * ny
            if 0.8 <= d <= 1.15:
                c = GOLD[1]
                if nx < -0.2 and ny < 0:
                    c = GOLD[2]
                if nx > 0.3 and ny > 0.15:
                    c = GOLD[0]
                put(s, x, y, c, "fixtures")
            if fancy and 1.08 <= d <= 1.22:
                put(s, x, y, GOLD[0], "fixtures")

    for y in range(cy - rh, cy + rh + 1):
        for x in range(cx - rw, cx + rw + 1):
            nx = (x - cx) / rw
            ny = (y - cy) / rh
            if nx * nx + ny * ny > 1.0:
                continue
            put(s, x, y, STONE[1], "fixtures")
            if nx < -0.05:
                put(s, x, y, STONE[3], "fixtures")
            if -0.55 < nx < -0.15 and -0.65 < ny < 0.2:
                put(s, x, y, STONE[5], "fixtures")
            if -0.35 < nx < -0.1 and -0.4 < ny < 0.0:
                put(s, x, y, (200, 210, 220, 255), "fixtures")
            # Warm bounce from windows
            if nx > 0.2 and abs(ny) < 0.5:
                put(s, x, y, (70, 60, 50, 255), "fixtures")

    put(s, cx, cy - rh - 4, GOLD[3], "fixtures")
    put(s, cx, cy - rh - 3, GOLD[2], "fixtures")
    put(s, cx - 1, cy - rh - 2, GOLD[1], "fixtures")
    put(s, cx + 1, cy - rh - 2, GOLD[1], "fixtures")
    if fancy:
        # Side scrolls
        put(s, cx - rw - 3, cy, GOLD[2], "fixtures")
        put(s, cx + rw + 3, cy, GOLD[2], "fixtures")
        put(s, cx - rw - 2, cy - 1, GOLD[1], "fixtures")
        put(s, cx + rw + 2, cy - 1, GOLD[1], "fixtures")
    put(s, cx, cy + rh + 2, GOLD[1], "fixtures")
    put(s, cx, cy + rh + 3, GOLD[2], "fixtures")


def draw_rect_mirror(s: Sprite, x0: int, y0: int, w: int, h: int) -> None:
    """Small rectangular looking-glass with gold frame (side walls)."""
    # Frame
    fill(s, x0, y0, x0 + w, y0 + h, GOLD[0], "fixtures")
    fill(s, x0 + 1, y0 + 1, x0 + w - 1, y0 + h - 1, GOLD[1], "fixtures")
    # Glass
    fill(s, x0 + 2, y0 + 2, x0 + w - 2, y0 + h - 2, STONE[1], "fixtures")
    for y in range(y0 + 2, y0 + h - 1):
        for x in range(x0 + 2, x0 + w - 1):
            nx = (x - x0) / w
            if nx < 0.4:
                put(s, x, y, STONE[3], "fixtures")
            if 0.15 < nx < 0.35 and (y - y0) < h * 0.45:
                put(s, x, y, STONE[5], "fixtures")
    # Corner ornaments
    put(s, x0, y0, GOLD[2], "fixtures")
    put(s, x0 + w, y0, GOLD[2], "fixtures")
    put(s, x0, y0 + h, GOLD[1], "fixtures")
    put(s, x0 + w, y0 + h, GOLD[1], "fixtures")
    put(s, x0 + w // 2, y0 - 1, GOLD[3], "fixtures")


def draw_banner(s: Sprite, cx: int, top: int, color_ramp, width: int = 10, length: int = 28) -> None:
    """Hanging heraldic banner with gold rod."""
    half = width // 2
    # Rod
    hline(s, cx - half - 2, cx + half + 2, top, GOLD[2], "fixtures")
    put(s, cx - half - 2, top, GOLD[3], "fixtures")
    put(s, cx + half + 2, top, GOLD[3], "fixtures")
    # Cloth
    for y in range(top + 1, top + length):
        t = (y - top) / length
        # Slight wave in silhouette
        sway = int(math.sin(t * math.pi * 2) * 1)
        # V-cut tip near bottom
        tip_in = 0
        if t > 0.75:
            tip_in = int((t - 0.75) / 0.25 * half)
        for dx in range(-half + tip_in, half - tip_in + 1):
            u = abs(dx) / max(1, half)
            c = color_ramp[0] if u > 0.7 else (color_ramp[1] if u > 0.25 else color_ramp[2])
            # Fold shadow
            if dx == -1:
                c = color_ramp[0]
            put(s, cx + dx + sway, y, c, "fixtures")
        # Gold fringe dots
        if y % 4 == 0 and tip_in == 0:
            put(s, cx - half + sway, y, GOLD[1], "fixtures")
            put(s, cx + half + sway, y, GOLD[1], "fixtures")
    # Emblem
    ey = top + length // 3
    put(s, cx, ey, GOLD[3], "fixtures")
    put(s, cx - 1, ey, GOLD[2], "fixtures")
    put(s, cx + 1, ey, GOLD[2], "fixtures")
    put(s, cx, ey - 1, GOLD[2], "fixtures")
    put(s, cx, ey + 1, GOLD[1], "fixtures")


def draw_sconce(s: Sprite, cx: int, cy: int) -> None:
    """Wall torch sconce with visible flame stub on fixtures."""
    put(s, cx - 2, cy, GOLD[0], "fixtures")
    put(s, cx - 1, cy, GOLD[1], "fixtures")
    put(s, cx, cy, GOLD[1], "fixtures")
    put(s, cx, cy - 1, GOLD[2], "fixtures")
    hline(s, cx - 1, cx + 2, cy + 1, GOLD[1], "fixtures")
    put(s, cx, cy + 2, GOLD[0], "fixtures")
    put(s, cx + 1, cy + 2, GOLD[0], "fixtures")
    vline(s, cx + 1, cy + 3, cy + 6, STONE[1], "fixtures")
    # Flame body (static base; glow layer animates around it)
    put(s, cx + 1, cy - 1, AMBER[2], "fixtures")
    put(s, cx + 1, cy - 2, AMBER[1], "fixtures")
    put(s, cx + 1, cy - 3, (255, 230, 140, 255), "fixtures")
    put(s, cx, cy - 2, AMBER[2], "fixtures")
    put(s, cx + 2, cy - 2, AMBER[1], "fixtures")


def draw_niche(s: Sprite, cx: int, top: int) -> None:
    """Wall niche with pedestal urn."""
    # Recess
    for y in range(top, top + 22):
        for x in range(cx - 6, cx + 7):
            put(s, x, y, STONE[1], "wall")
        put(s, cx - 6, y, STONE[0], "wall")
        put(s, cx + 6, y, STONE[3], "wall")
    # Arch top
    for t in range(-6, 7):
        dy = int(math.sqrt(max(0, 36 - t * t)))
        put(s, cx + t, top + 6 - dy, STONE[0], "wall")
        put(s, cx + t, top + 7 - dy, STONE[3], "wall")
    # Pedestal
    fill(s, cx - 3, top + 16, cx + 3, top + 21, STONE[3], "fixtures")
    hline(s, cx - 4, cx + 4, top + 16, STONE[4], "fixtures")
    # Urn
    fill(s, cx - 2, top + 10, cx + 2, top + 15, STONE[4], "fixtures")
    hline(s, cx - 3, cx + 3, top + 10, GOLD[1], "fixtures")
    hline(s, cx - 1, cx + 1, top + 8, GOLD[2], "fixtures")
    put(s, cx, top + 7, GOLD[3], "fixtures")
    put(s, cx, top + 12, GOLD[1], "fixtures")


def draw_chandelier(s: Sprite) -> None:
    """Ceiling chandelier over aisle."""
    cx, cy = W // 2, 18
    # Chain
    for y in range(8, cy):
        put(s, cx, y, STONE[3] if y % 2 == 0 else GOLD[0], "fixtures")
    # Ring
    for t in range(16):
        ang = t / 16 * math.tau
        x = int(cx + math.cos(ang) * 10)
        y = int(cy + math.sin(ang) * 3)
        put(s, x, y, GOLD[1], "fixtures")
        put(s, x, y + 1, GOLD[0], "fixtures")
    # Arms + candles
    for i, ang in enumerate([0.2, 1.2, 2.2, 3.4, 4.4, 5.4]):
        ax = int(cx + math.cos(ang) * 9)
        ay = int(cy + math.sin(ang) * 2)
        put(s, ax, ay, GOLD[2], "fixtures")
        put(s, ax, ay + 1, GOLD[1], "fixtures")
        # Candle
        put(s, ax, ay - 1, STONE[5], "fixtures")
        put(s, ax, ay - 2, STONE[5], "fixtures")
    # Center drop
    put(s, cx, cy + 2, GOLD[3], "fixtures")
    put(s, cx, cy + 3, GOLD[2], "fixtures")
    put(s, cx, cy + 4, GOLD[1], "fixtures")


def draw_side_bench(s: Sprite, x0: int, facing_right: bool) -> None:
    """Stone bench along side wall."""
    y0 = 100
    for y in range(y0, y0 + 10):
        for x in range(x0, x0 + 18):
            put(s, x, y, STONE[2], "fixtures")
    hline(s, x0, x0 + 17, y0, STONE[4], "fixtures")
    hline(s, x0, x0 + 17, y0 + 9, STONE[1], "fixtures")
    # Legs
    for lx in (x0 + 1, x0 + 14):
        vline(s, lx, y0 + 10, y0 + 14, STONE[1], "fixtures")
    # Cushion strip
    for x in range(x0 + 2, x0 + 16):
        put(s, x, y0 + 1, CARPET[1], "fixtures")
        put(s, x, y0 + 2, CARPET[2], "fixtures")


def draw_floor(s: Sprite) -> None:
    fill(s, 0, 79, W - 1, H - 1, STONE[2], "floor")
    hline(s, 0, W - 1, 78, STONE[1], "wall")
    hline(s, 0, W - 1, 79, STONE[3], "floor")

    rows = [80, 86, 93, 101, 110, 120]
    for ri, y0 in enumerate(rows):
        y1 = (rows[ri + 1] - 1) if ri + 1 < len(rows) else H - 1
        t = ri / max(1, len(rows) - 1)
        tile_w = int(10 + t * 14)
        x = 0
        col = 0
        while x < W:
            c_hi = STONE[3] if (col + ri) % 2 == 0 else STONE[2]
            c_lo = STONE[2] if (col + ri) % 2 == 0 else STONE[1]
            for yy in range(y0, y1 + 1):
                for xx in range(x, min(x + tile_w, W)):
                    put(s, xx, yy, c_hi if yy < y0 + 2 else c_lo, "floor")
            hline(s, x, min(x + tile_w - 1, W - 1), y1, STONE[1], "floor")
            vline(s, x, y0, y1, STONE[1], "floor")
            x += tile_w
            col += 1

    vx = W // 2
    for k in (-4, -2, 2, 4):
        for step in range(42):
            t = step / 41
            xx = int(vx + k * (5 + t * 24))
            yy = int(80 + t * (H - 80))
            put(s, xx, yy, STONE[1], "floor")


def draw_carpet(s: Sprite) -> None:
    for y in range(80, H):
        t = (y - 80) / (H - 80)
        half = int(9 + t * 30)
        cx = W // 2
        hline(s, cx - half - 2, cx + half + 2, y, CARPET[0], "carpet")
        for x in range(cx - half, cx + half + 1):
            u = abs(x - cx) / max(1, half)
            worn = ((x * 7 + y * 5) % 19 == 0) or ((x * 3 + y) % 29 == 0)
            if worn:
                c = CARPET[1]
            elif u < 0.22:
                c = CARPET[3]
            elif u < 0.55:
                c = CARPET[2]
            else:
                c = CARPET[1]
            put(s, x, y, c, "carpet")
        put(s, cx - half, y, GOLD[1], "carpet")
        put(s, cx + half, y, GOLD[1], "carpet")
        put(s, cx - half + 1, y, GOLD[0], "carpet")
        put(s, cx + half - 1, y, GOLD[0], "carpet")
        if y % 5 == 0:
            put(s, cx - half, y, GOLD[2], "carpet")
            put(s, cx + half, y, GOLD[2], "carpet")

    for my in (94, 110, 124):
        t = (my - 80) / (H - 80)
        half = int(9 + t * 30)
        cx = W // 2
        for dy in range(-2, 3):
            for dx in range(-4, 5):
                if dx * dx / 16 + dy * dy / 4 <= 1:
                    put(s, cx + dx, my + dy, CARPET[3] if abs(dx) < 2 else CARPET[2], "carpet")
        put(s, cx, my, GOLD[2], "carpet")


def draw_side_rugs(s: Sprite) -> None:
    """Small side runners near outer walls."""
    for x0 in (26, 182):
        for y in range(110, 126):
            for x in range(x0, x0 + 14):
                u = (x - x0) / 14
                c = CARPET[2] if 0.25 < u < 0.75 else CARPET[1]
                if (x + y * 3) % 13 == 0:
                    c = CARPET[0]
                put(s, x, y, c, "carpet")
            put(s, x0, y, GOLD[0], "carpet")
            put(s, x0 + 13, y, GOLD[0], "carpet")
        # End tassels
        for x in range(x0 + 2, x0 + 12, 2):
            put(s, x, 126, GOLD[1], "carpet")


def draw_pillar(s: Sprite, cx: int) -> None:
    top, bot = 3, 127
    for y in range(top, top + 12):
        half = 13 - (y - top) // 2
        for dx in range(-half, half + 1):
            c = STONE[4] if abs(dx) < half // 2 else STONE[3]
            if dx > half // 3:
                c = STONE[5]
            put(s, cx + dx, y, c, "pillars")
        put(s, cx - half, y, STONE[1], "pillars")
        put(s, cx + half, y, STONE[5], "pillars")
    hline(s, cx - 14, cx + 14, top + 3, STONE[5], "pillars")
    # Gold inlay ring on capital
    hline(s, cx - 10, cx + 10, top + 8, GOLD[1], "pillars")

    for y in range(top + 12, bot - 9):
        t = (y - top) / (bot - top)
        half = int(9 + t * 3)
        for dx in range(-half, half + 1):
            flute = abs(dx) % 3 == 2
            if dx < -half // 2:
                c = STONE[1]
            elif dx < 0:
                c = STONE[2]
            elif dx < half // 2:
                c = STONE[3]
            else:
                c = STONE[4]
            if flute and abs(dx) < half - 1:
                idx = STONE.index(c) if c in STONE else 2
                c = STONE[max(0, idx - 1)]
            put(s, cx + dx, y, c, "pillars")
        put(s, cx - half, y, STONE[0], "pillars")
        put(s, cx + half, y, STONE[5], "pillars")

    for y in range(bot - 9, bot + 1):
        half = 15 if y > bot - 5 else 13
        for dx in range(-half, half + 1):
            put(s, cx + dx, y, STONE[2] if dx < 0 else STONE[3], "pillars")
        put(s, cx - half, y, STONE[0], "pillars")
        put(s, cx + half, y, STONE[4], "pillars")
    hline(s, cx - 16, cx + 16, bot - 9, STONE[5], "pillars")
    hline(s, cx - 12, cx + 12, bot - 5, GOLD[0], "pillars")


def draw_shade(s: Sprite) -> None:
    for y in range(H):
        for x in range(W):
            vx = abs(x - W / 2) / (W / 2)
            ceiling = max(0.0, 1.0 - y / 48.0)
            corner = max(0.0, vx - 0.5) / 0.5
            amount = 0.74 + 0.2 * ceiling + 0.12 * corner
            if 80 <= y and abs(x - W / 2) < 22 + (y - 80) * 0.35:
                amount = min(1.0, amount + 0.1)
            g = int(255 * min(1.0, amount))
            if g < 248:
                put(s, x, y, (g, g, int(min(255, g * 1.03)), 255), "shade")


# ---------------------------------------------------------------------------
# Animated FX — volumetric rays
# ---------------------------------------------------------------------------

def beam_foot(cx: int) -> tuple[int, int]:
    fx = int(cx + (W // 2 - cx) * 0.48)
    fy = 118
    return fx, fy


def draw_wall_crest(s: Sprite, cx: int, cy: int, accent) -> None:
    """Small heraldic shield above a mirror — avoids banner overlap."""
    # Shield outline
    for dy in range(-6, 8):
        half = 5 if dy < 4 else max(1, 5 - (dy - 3))
        for dx in range(-half, half + 1):
            put(s, cx + dx, cy + dy, accent[1] if abs(dx) < half else GOLD[0], "fixtures")
        put(s, cx - half, cy + dy, GOLD[1], "fixtures")
        put(s, cx + half, cy + dy, GOLD[1], "fixtures")
    put(s, cx, cy - 7, GOLD[3], "fixtures")
    put(s, cx, cy, accent[2], "fixtures")
    put(s, cx - 1, cy, GOLD[2], "fixtures")
    put(s, cx + 1, cy, GOLD[2], "fixtures")


def draw_god_ray(s: Sprite, frame: int, cx: int, tint: tuple, inten: float, wobble: float) -> None:
    """Soft volumetric cone — continuous alpha falloff, no speckled trapezoid look."""
    foot_x, foot_y = beam_foot(cx)
    foot_x += int(wobble)
    sill_y = WIN_TOP + WIN_H + 1
    top_half, bot_half = 5.0, 17.0

    # Window bloom
    for y in range(WIN_TOP, WIN_TOP + WIN_H + 1):
        for x in range(cx - WIN_HALF, cx + WIN_HALF + 1):
            if not in_arch(cx, WIN_TOP, WIN_HALF, x, y):
                continue
            dist = abs(x - cx) / WIN_HALF
            a = int((110 + 60 * (1 - dist)) * inten)
            put(s, x, y, (tint[0], tint[1], tint[2], a), "glow", frame)

    for y in range(sill_y, foot_y + 1):
        t = (y - sill_y) / max(1, foot_y - sill_y)
        # Smoothstep widen
        tw = t * t * (3 - 2 * t)
        bx = cx + (foot_x - cx) * t
        half = top_half + (bot_half - top_half) * tw
        # Cover full soft radius
        span = int(math.ceil(half * 1.35))
        for di in range(-span, span + 1):
            edge = abs(di) / max(0.5, half)
            if edge >= 1.35:
                continue
            # Cosine falloff → soft continuous beam, not hard trapezoid
            if edge <= 1.0:
                core = 0.5 + 0.5 * math.cos(edge * math.pi)
            else:
                # Soft penumbra beyond geometric edge
                core = 0.5 * max(0.0, 1.0 - (edge - 1.0) / 0.35)
            core = core * core  # concentrate energy in spine

            r = int(BEAM[1][0] * 0.55 + tint[0] * 0.45)
            g = int(BEAM[1][1] * 0.55 + tint[1] * 0.45)
            b = int(BEAM[1][2] * 0.55 + tint[2] * 0.45)
            # Screen wash — higher alpha, smoother
            a_s = int((70 + 55 * core) * inten * (1.0 - 0.3 * t))
            put(s, int(round(bx + di)), y, (r, g, b, a_s), "beams", frame)

            # Addition hot core
            if edge < 0.85:
                rr = int(BEAM[0][0] * 0.7 + tint[0] * 0.3)
                gg = int(BEAM[0][1] * 0.7 + tint[1] * 0.3)
                bb = int(BEAM[0][2] * 0.7 + tint[2] * 0.3)
                a_a = int((50 + 75 * core) * inten * (0.9 - 0.25 * t))
                put(s, int(round(bx + di)), y, (rr, gg, bb, a_a), "glow", frame)

            # Bright filament
            if abs(di) <= 0.6:
                put(s, int(round(bx + di)), y,
                    (BEAM[0][0], BEAM[0][1], BEAM[0][2], int(100 * inten * (1.0 - 0.35 * t))),
                    "glow", frame)

    # Soft floor pool
    prx, pry = 18.0, 5.5
    for dy in range(-8, 9):
        for dx in range(-22, 23):
            e = (dx / prx) ** 2 + (dy / pry) ** 2
            if e > 1.2:
                continue
            fall = max(0.0, 1.0 - math.sqrt(min(1.0, e)))
            fall = fall * fall * (3 - 2 * fall)
            put(s, foot_x + dx, foot_y + dy,
                (tint[0], tint[1], tint[2], int(45 * fall * inten)), "beams", frame)
            put(s, foot_x + dx, foot_y + dy,
                (BEAM[0][0], BEAM[0][1], BEAM[0][2], int(110 * fall * inten)), "glow", frame)


def draw_light_beams(s: Sprite, frame: int) -> None:
    shimmer = flicker(frame, base=1.0, amount=0.16, seed=5)
    for i, win in enumerate(WINDOWS):
        inten = shimmer * (0.93 + 0.07 * math.sin(frame * 0.9 + i * 1.3))
        wobble = wave_curve(frame, FRAMES, amplitude=1.8, phase=i * 0.2) * (0.9 if i != 1 else 0.35)
        if i == 2:
            wobble = -wobble
        draw_god_ray(s, frame, win["cx"], win["tint"], inten, wobble)

    # Chandelier candle glows (animated)
    cx = W // 2
    cy = 18
    for j, ang in enumerate([0.2, 1.2, 2.2, 3.4, 4.4, 5.4]):
        ax = int(cx + math.cos(ang) * 9)
        ay = int(cy + math.sin(ang) * 2) - 2
        fi = flicker(frame, base=1.0, amount=0.25, seed=20 + j)
        for px, py, col in radial_glow(ax, ay, 3, (255, 200, 100, int(160 * fi)), falloff=1.4):
            put(s, px, py, col, "glow", frame)
        put(s, ax, ay, (255, 240, 180, int(220 * fi)), "glow", frame)

    # Sconce flames
    for sx, sy in ((34, 58), (190, 58), (34, 88), (190, 88)):
        fi = flicker(frame, base=1.0, amount=0.3, seed=sx + sy)
        for px, py, col in radial_glow(sx + 1, sy - 1, 4, (255, 160, 60, int(140 * fi)), falloff=1.8):
            put(s, px, py, col, "glow", frame)
        put(s, sx + 1, sy - 1, (255, 220, 120, int(200 * fi)), "glow", frame)
        put(s, sx + 1, sy - 2, (255, 180, 80, int(160 * fi)), "glow", frame)


def draw_dust(s: Sprite, frame: int) -> None:
    rng = random.Random(11)
    motes = []
    for i, win in enumerate(WINDOWS):
        foot_x, foot_y = beam_foot(win["cx"])
        for _ in range(20):
            motes.append({
                "cx": win["cx"], "foot_x": foot_x, "foot_y": foot_y,
                "along": rng.random(), "lat": rng.uniform(-0.8, 0.8),
                "speed": rng.uniform(0.2, 0.9), "phase": rng.random(),
                "bright": rng.random() > 0.65, "seed": rng.randint(0, 999),
                "tint": win["tint"],
            })
    # Extra motes under chandelier
    for _ in range(8):
        motes.append({
            "cx": W // 2, "foot_x": W // 2, "foot_y": 70,
            "along": rng.random(), "lat": rng.uniform(-0.9, 0.9),
            "speed": rng.uniform(0.15, 0.5), "phase": rng.random(),
            "bright": True, "seed": rng.randint(0, 999),
            "tint": (255, 220, 160),
            "chand": True,
        })

    sill_y = WIN_TOP + WIN_H + 1
    for m in motes:
        along = (m["along"] + frame * 0.03 * m["speed"]) % 1.0
        sway = math.sin((frame / FRAMES + m["phase"]) * math.tau) * 0.2
        if m.get("chand"):
            x = int(m["cx"] + m["lat"] * 12 + sway * 3)
            y = int(22 + along * 40 + wave_curve(frame, FRAMES, 0.6, m["phase"]))
        else:
            t = along
            bx = m["cx"] + (m["foot_x"] - m["cx"]) * t
            by = sill_y + (m["foot_y"] - sill_y) * t
            half = 4 + (18 - 4) * (t * t)
            x = int(bx + (m["lat"] + sway) * half)
            y = int(by + wave_curve(frame, FRAMES, 0.7, m["phase"]) * 0.5)
        fade = 0.4 if along < 0.06 or along > 0.94 else 1.0
        inten = flicker(frame, base=0.9, amount=0.2, seed=m["seed"])
        a = int((220 if m["bright"] else 120) * fade * inten)
        tint = m["tint"]
        put(s, x, y, (min(255, tint[0] + 40), min(255, tint[1] + 30), min(255, tint[2] + 20), a), "dust", frame)
        if m["bright"]:
            put(s, x, y - 1, (DUST[0], DUST[1], DUST[2], a // 3), "dust", frame)


def copy_static(s: Sprite) -> None:
    names = ["wall", "glass", "fixtures", "floor", "carpet", "pillars", "shade"]
    for fi in range(1, FRAMES):
        for name in names:
            layer = s._resolve_layer(name)
            src = layer.cels[0]
            if src is None:
                continue
            layer.cels[fi] = Cel(x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels))


def build() -> Sprite:
    s = Sprite(W, H)
    s.add_layer("wall")
    s.add_layer("glass")
    s.add_layer("fixtures")
    s.add_layer("floor")
    s.add_layer("carpet")
    s.add_layer("pillars")
    s.add_layer("shade", blend_mode="multiply", opacity=95)
    s.add_layer("beams", blend_mode="screen")
    s.add_layer("glow", blend_mode="addition")
    s.add_layer("dust", blend_mode="addition")

    for _ in range(1, FRAMES):
        s.add_frame(150)

    draw_vaulted_wall(s)

    for win in WINDOWS:
        draw_arched_window(s, win["cx"], win["colors"])

    # Large oval mirrors between windows
    draw_oval_mirror(s, 84, 54, rw=9, rh=14)
    draw_oval_mirror(s, 140, 54, rw=9, rh=14)
    # Crests above those mirrors
    draw_wall_crest(s, 84, 34, RUBY)
    draw_wall_crest(s, 140, 34, SAPPH)

    # Side oval mirrors (outer walls, high)
    draw_oval_mirror(s, 30, 46, rw=7, rh=11, fancy=True)
    draw_oval_mirror(s, 194, 46, rw=7, rh=11, fancy=True)
    # Extra small oval pair higher near cornice between window and side
    draw_oval_mirror(s, 68, 40, rw=5, rh=8, fancy=False)
    draw_oval_mirror(s, 156, 40, rw=5, rh=8, fancy=False)

    # Outer banners only
    draw_banner(s, 42, 28, AMBER, width=8, length=16)
    draw_banner(s, 182, 28, EMER, width=8, length=16)

    draw_sconce(s, 36, 56)
    draw_sconce(s, 188, 56)
    draw_sconce(s, 36, 86)
    draw_sconce(s, 188, 86)

    draw_chandelier(s)
    draw_back_door(s)  # side arched passages
    draw_floor(s)
    draw_carpet(s)
    draw_side_rugs(s)
    draw_pillar(s, 16)
    draw_pillar(s, 207)
    draw_shade(s)
    copy_static(s)

    for f in range(FRAMES):
        draw_light_beams(s, f)
        draw_dust(s, f)
        s.set_frame_duration(f, 150)

    s.add_tag("ambient", 0, FRAMES - 1, direction="pingpong")
    s.palette = PALETTE
    return s


def main() -> None:
    s = build()
    ase = s.save(OUT / "hall_of_vigil.aseprite")
    png = s.preview(OUT / "hall_of_vigil.png", scale=3, frame=0, background=(8, 8, 12, 255))
    order = list(range(FRAMES)) + list(range(FRAMES - 2, 0, -1))
    gif = s.preview_gif(OUT / "hall_of_vigil.gif", scale=3, background=(8, 8, 12, 255), frames=order)

    img = s.composite_frame(0)
    samples = []
    for win in WINDOWS:
        fx, fy = beam_foot(win["cx"])
        samples.append((win["cx"], img.getpixel((fx, fy))))
    print(f"saved {ase}")
    print(f"saved {png}")
    print(f"saved {gif}")
    print(f"beam samples {samples}")
    print(f"palette={len(PALETTE)}")


if __name__ == "__main__":
    main()

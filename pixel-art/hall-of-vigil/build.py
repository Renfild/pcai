#!/usr/bin/env python3
"""The Hall of Vigil — castle great-hall interior ambient loop (pass 2).

224x128 · ~28 colors · 8-frame pingpong
Layers: wall, glass, fixtures, floor, carpet, pillars, shade(multiply),
        beams(screen), glow(addition), dust(addition)
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / ".cursor" / "skills" / "aseprite-pixel-art"
sys.path.insert(0, str(SKILL / "scripts"))

from aseprite_io import Cel, Sprite
from fx_helpers import flicker, wave_curve

OUT = Path(__file__).resolve().parent
W, H = 224, 128
FRAMES = 8

# ---------------------------------------------------------------------------
# Palette (~28)
# ---------------------------------------------------------------------------
STONE = [
    (24, 26, 32, 255),    # 0 deepest
    (40, 44, 54, 255),    # 1 dark
    (58, 64, 76, 255),    # 2 mid-dark
    (82, 90, 104, 255),   # 3 mid
    (110, 120, 136, 255), # 4 lit
    (158, 168, 184, 255), # 5 light+highlight combined
]
CARPET = [
    (52, 14, 20, 255),
    (98, 24, 32, 255),
    (148, 40, 46, 255),
    (200, 72, 62, 255),
]
GOLD = [
    (78, 52, 20, 255),
    (132, 92, 32, 255),
    (188, 148, 52, 255),
    (236, 208, 110, 255),
]
RUBY = [(96, 20, 30, 255), (168, 40, 52, 255), (228, 78, 78, 255)]
SAPPH = [(20, 40, 96, 255), (44, 78, 168, 255), (96, 140, 228, 255)]
EMER = [(20, 76, 44, 255), (40, 140, 78, 255), (78, 200, 120, 255)]
AMBER = [(108, 64, 18, 255), (188, 128, 34, 255), (236, 188, 78, 255)]
BEAM = [(255, 220, 140, 255), (255, 188, 90, 255)]  # core + mid
DUST = (255, 240, 210, 255)

PALETTE = STONE + CARPET + GOLD + RUBY + SAPPH + EMER + AMBER + BEAM + [DUST]
assert 24 <= len(PALETTE) <= 30, len(PALETTE)

WINDOW_CENTERS = [56, 112, 168]
WIN_TOP, WIN_HALF, WIN_H = 32, 13, 42


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


def in_arch(cx, top, half, x, y) -> bool:
    """True if (x,y) is inside the arched window opening."""
    sill = top + WIN_H
    if y < top or y > sill:
        return False
    if y >= top + half:
        return abs(x - cx) < half - 1
    # semicircle
    dx = x - cx
    dy = (top + half) - y
    return dx * dx + dy * dy <= (half - 2) * (half - 2)


# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------

def draw_vaulted_wall(s: Sprite) -> None:
    # Solid wall
    fill(s, 0, 0, W - 1, 78, STONE[2], "wall")

    # Ceiling gloom
    for y in range(0, 26):
        t = y / 26
        c = STONE[0] if t < 0.45 else STONE[1]
        hline(s, 0, W - 1, y, c, "wall")

    # Vault ribs as thick stone arches (not beads)
    bays = [(0, 48), (48, 96), (96, 144), (144, 192), (192, 224)]
    for x0, x1 in bays:
        cx = (x0 + x1) // 2
        span = (x1 - x0) // 2 - 2
        for t in range(span * 2 + 1):
            dx = t - span
            # Upper arch curve — more visible rib
            yy = int(5 + (1 - math.sqrt(max(0, 1 - (dx / span) ** 2))) * 20)
            for thick in range(4):
                put(s, cx + dx, yy + thick, STONE[1], "wall")
            put(s, cx + dx, yy, STONE[3], "wall")          # lit underside edge
            put(s, cx + dx, yy + 1, STONE[2], "wall")
            put(s, cx + dx, yy + 3, STONE[0], "wall")       # deep shadow on top of rib
        # Vertical springers into cornice
        for y in range(22, 30):
            put(s, x0 + 2, y, STONE[1], "wall")
            put(s, x0 + 3, y, STONE[2], "wall")
            put(s, x1 - 3, y, STONE[1], "wall")
            put(s, x1 - 4, y, STONE[2], "wall")

    # Cornice band
    hline(s, 0, W - 1, 27, STONE[4], "wall")
    hline(s, 0, W - 1, 28, STONE[1], "wall")
    hline(s, 0, W - 1, 29, STONE[5], "wall")
    hline(s, 0, W - 1, 30, STONE[3], "wall")

    # Ashlar blocks on back wall
    for y in range(31, 78, 7):
        hline(s, 0, W - 1, y, STONE[1], "wall")
        off = 0 if (y // 7) % 2 == 0 else 9
        for x in range(off, W, 18):
            vline(s, x, y + 1, min(y + 6, 77), STONE[1], "wall")
            # subtle block face variation
            for yy in range(y + 1, min(y + 6, 77)):
                for xx in range(x + 1, min(x + 17, W)):
                    if (xx + yy) % 13 == 0:
                        put(s, xx, yy, STONE[3], "wall")


def draw_arched_window(s: Sprite, cx: int, colors) -> None:
    top, half, height = WIN_TOP, WIN_HALF, WIN_H
    sill = top + height

    # Stone frame (outer)
    for y in range(top - 2, sill + 3):
        for x in range(cx - half - 2, cx + half + 3):
            inside = in_arch(cx, top, half, x, y)
            near = False
            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if in_arch(cx, top, half, x + ox, y + oy):
                    near = True
                    break
            if near and not inside:
                # Frame thickness
                put(s, x, y, STONE[5] if y < top + 8 or x <= cx - half else STONE[4], "wall")
            if abs(x - (cx - half - 2)) < 1 or abs(x - (cx + half + 2)) < 1:
                if top <= y <= sill + 1:
                    put(s, x, y, STONE[3], "wall")

    # Arch highlight on outer stone
    for t in range(-half - 1, half + 2):
        dy = int(math.sqrt(max(0, (half + 1) ** 2 - t * t)))
        put(s, cx + t, top + half - dy - 1, STONE[5], "wall")

    # Sill ledge
    hline(s, cx - half - 1, cx + half + 1, sill + 1, STONE[5], "wall")
    hline(s, cx - half, cx + half, sill + 2, STONE[3], "wall")

    # Glass + leading
    for y in range(top, sill + 1):
        for x in range(cx - half, cx + half + 1):
            if not in_arch(cx, top, half, x, y):
                continue
            # Band by height — 3 color stops
            rel = (y - top) / height
            if rel < 0.33:
                band = 0
            elif rel < 0.66:
                band = 1
            else:
                band = 2
            # Diamond lead came
            if ((x + y) % 4 == 0) or ((x - y) % 4 == 0):
                put(s, x, y, STONE[0], "glass")
            else:
                c = colors[band]
                # Occasional brighter pane
                if (x * 5 + y * 3) % 11 == 0:
                    c = colors[min(2, band + 1)]
                put(s, x, y, c, "glass")

    # Mullion + transom
    for y in range(top + 2, sill + 1):
        if in_arch(cx, top, half, cx, y):
            put(s, cx, y, STONE[4], "wall")
            put(s, cx - 1, y, STONE[3], "wall")
    hline(s, cx - half + 2, cx + half - 2, top + height // 2, STONE[4], "wall")


def draw_mirror(s: Sprite, cx: int, cy: int, rw: int = 9, rh: int = 15) -> None:
    # Ornate gold oval frame
    for y in range(cy - rh - 3, cy + rh + 4):
        for x in range(cx - rw - 3, cx + rw + 4):
            nx = (x - cx) / (rw + 2.2)
            ny = (y - cy) / (rh + 2.2)
            d = nx * nx + ny * ny
            if 0.82 <= d <= 1.12:
                # Frame body
                c = GOLD[1]
                if nx < -0.25 and ny < 0:
                    c = GOLD[2]
                if nx > 0.35 and ny > 0.2:
                    c = GOLD[0]
                put(s, x, y, c, "fixtures")
            if 1.05 <= d <= 1.2:
                put(s, x, y, GOLD[0], "fixtures")

    # Glass
    for y in range(cy - rh, cy + rh + 1):
        for x in range(cx - rw, cx + rw + 1):
            nx = (x - cx) / rw
            ny = (y - cy) / rh
            if nx * nx + ny * ny > 1.0:
                continue
            # Dark reflective surface with cool stone echo
            put(s, x, y, STONE[1], "fixtures")
            # Soft vertical reflection gradient
            if nx < -0.1:
                put(s, x, y, STONE[3], "fixtures")
            if -0.55 < nx < -0.2 and -0.7 < ny < 0.15:
                put(s, x, y, STONE[5], "fixtures")
            if -0.4 < nx < -0.15 and -0.45 < ny < -0.05:
                put(s, x, y, STONE[5], "fixtures")
            # Tiny warm bounce from nearby windows
            if nx > 0.25 and abs(ny) < 0.4:
                put(s, x, y, (STONE[2][0] + 8, STONE[2][1] + 4, STONE[2][2], 255), "fixtures")

    # Crest
    put(s, cx, cy - rh - 4, GOLD[3], "fixtures")
    put(s, cx, cy - rh - 3, GOLD[2], "fixtures")
    put(s, cx - 1, cy - rh - 2, GOLD[1], "fixtures")
    put(s, cx + 1, cy - rh - 2, GOLD[1], "fixtures")
    # Bottom finial
    put(s, cx, cy + rh + 2, GOLD[1], "fixtures")
    put(s, cx, cy + rh + 3, GOLD[2], "fixtures")


def draw_floor(s: Sprite) -> None:
    fill(s, 0, 79, W - 1, H - 1, STONE[2], "floor")
    hline(s, 0, W - 1, 78, STONE[1], "wall")  # skirting
    hline(s, 0, W - 1, 79, STONE[3], "floor")

    # Large perspective flagstones
    # Row depths (y starts)
    rows = [80, 86, 93, 101, 110, 120]
    for ri, y0 in enumerate(rows):
        y1 = (rows[ri + 1] - 1) if ri + 1 < len(rows) else H - 1
        t = ri / max(1, len(rows) - 1)
        # Tile width grows toward camera
        tile_w = int(10 + t * 14)
        # Perspective offset so seams converge toward center
        # Number of tiles across
        # Draw checker
        x = 0
        col = 0
        # Shift each row toward center vanishing
        while x < W:
            w = tile_w
            # nudge columns outward with depth
            c_hi = STONE[3] if (col + ri) % 2 == 0 else STONE[2]
            c_lo = STONE[2] if (col + ri) % 2 == 0 else STONE[1]
            for yy in range(y0, y1 + 1):
                for xx in range(x, min(x + w, W)):
                    # top of tile slightly lighter
                    put(s, xx, yy, c_hi if yy < y0 + 2 else c_lo, "floor")
            # grout
            hline(s, x, min(x + w - 1, W - 1), y1, STONE[1], "floor")
            vline(s, x, y0, y1, STONE[1], "floor")
            x += w
            col += 1

    # Converging aisle cracks toward vanish
    vx = W // 2
    for k in (-3, -1, 1, 3):
        for step in range(40):
            t = step / 39
            xx = int(vx + k * (4 + t * 22))
            yy = int(80 + t * (H - 80))
            put(s, xx, yy, STONE[1], "floor")


def draw_carpet(s: Sprite) -> None:
    for y in range(80, H):
        t = (y - 80) / (H - 80)
        half = int(9 + t * 30)
        cx = W // 2
        # Shadow under rug
        hline(s, cx - half - 2, cx + half + 2, y, CARPET[0], "carpet")
        for x in range(cx - half, cx + half + 1):
            # Center stripe slightly richer
            u = abs(x - cx) / max(1, half)
            worn = ((x * 7 + y * 5) % 19 == 0) or ((x * 3 + y) % 29 == 0)
            faded = ((x + y * 4) % 37 == 0)
            if worn:
                c = CARPET[1]
            elif faded:
                c = CARPET[2]
            elif u < 0.2:
                c = CARPET[3]
            elif u < 0.55:
                c = CARPET[2]
            else:
                c = CARPET[1]
            put(s, x, y, c, "carpet")
        # Gold border
        put(s, cx - half, y, GOLD[1], "carpet")
        put(s, cx + half, y, GOLD[1], "carpet")
        put(s, cx - half + 1, y, GOLD[0], "carpet")
        put(s, cx + half - 1, y, GOLD[0], "carpet")
        if y % 5 == 0:
            put(s, cx - half, y, GOLD[2], "carpet")
            put(s, cx + half, y, GOLD[2], "carpet")

    # Medallions
    for my in (94, 110, 124):
        t = (my - 80) / (H - 80)
        half = int(9 + t * 30)
        cx = W // 2
        for dy in range(-2, 3):
            for dx in range(-4, 5):
                if dx * dx / 16 + dy * dy / 4 <= 1:
                    put(s, cx + dx, my + dy, CARPET[3] if abs(dx) < 2 else CARPET[2], "carpet")
        put(s, cx, my, GOLD[2], "carpet")
        put(s, cx - 1, my, GOLD[1], "carpet")
        put(s, cx + 1, my, GOLD[1], "carpet")


def draw_pillar(s: Sprite, cx: int) -> None:
    top, bot = 4, 127
    # Capital
    for y in range(top, top + 12):
        half = 13 - (y - top) // 2
        for dx in range(-half, half + 1):
            c = STONE[5] if dx > half // 3 else (STONE[3] if dx < -half // 3 else STONE[4])
            put(s, cx + dx, y, c, "pillars")
        put(s, cx - half, y, STONE[1], "pillars")
        put(s, cx + half, y, STONE[5], "pillars")
    hline(s, cx - 14, cx + 14, top + 3, STONE[5], "pillars")
    hline(s, cx - 13, cx + 13, top + 11, STONE[1], "pillars")

    # Shaft with fluting
    for y in range(top + 12, bot - 9):
        t = (y - top) / (bot - top)
        half = int(9 + t * 3)
        for dx in range(-half, half + 1):
            # Flute grooves
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
                c = STONE[max(0, STONE.index(c) - 1)] if c in STONE else c
            put(s, cx + dx, y, c, "pillars")
        put(s, cx - half, y, STONE[0], "pillars")
        put(s, cx + half, y, STONE[5], "pillars")

    # Base
    for y in range(bot - 9, bot + 1):
        half = 15 if y > bot - 5 else 13
        for dx in range(-half, half + 1):
            c = STONE[2] if dx < 0 else STONE[3]
            put(s, cx + dx, y, c, "pillars")
        put(s, cx - half, y, STONE[0], "pillars")
        put(s, cx + half, y, STONE[4], "pillars")
    hline(s, cx - 16, cx + 16, bot - 9, STONE[5], "pillars")
    hline(s, cx - 15, cx + 15, bot, STONE[1], "pillars")


def draw_shade(s: Sprite) -> None:
    """Subtle multiply vignette — keep center readable."""
    for y in range(H):
        for x in range(W):
            vx = abs(x - W / 2) / (W / 2)
            # Darker up high and in corners; leave aisle / beams more open
            ceiling = max(0.0, 1.0 - y / 50.0)
            corner = max(0.0, vx - 0.55) / 0.45
            amount = 0.72 + 0.22 * ceiling + 0.12 * corner
            # Protect carpet aisle a bit
            if 80 <= y and abs(x - W / 2) < 20 + (y - 80) * 0.35:
                amount = min(1.0, amount + 0.08)
            g = int(255 * min(1.0, amount))
            if g < 250:
                put(s, x, y, (g, g, int(min(255, g * 1.03)), 255), "shade")


# ---------------------------------------------------------------------------
# Animated FX
# ---------------------------------------------------------------------------

def beam_foot(cx: int) -> tuple[int, int]:
    # Angle toward center aisle, land mid-floor
    fx = int(cx + (W // 2 - cx) * 0.42)
    fy = 116
    return fx, fy


def draw_light_beams(s: Sprite, frame: int) -> None:
    shimmer = flicker(frame, base=1.0, amount=0.14, seed=5)
    wobble = wave_curve(frame, FRAMES, amplitude=1.5, cycles=1)

    for i, cx in enumerate(WINDOW_CENTERS):
        inten = shimmer * (0.94 + 0.06 * math.sin(frame * 0.85 + i * 1.1))
        foot_x, foot_y = beam_foot(cx)
        foot_x += int(wobble * (0.8 if i != 1 else 0.25) * (1 if i != 2 else -1))

        # Window pane bloom (addition)
        for y in range(WIN_TOP, WIN_TOP + WIN_H + 1):
            for x in range(cx - WIN_HALF, cx + WIN_HALF + 1):
                if not in_arch(cx, WIN_TOP, WIN_HALF, x, y):
                    continue
                dist = abs(x - cx) / WIN_HALF
                a = int((70 + 55 * (1 - dist)) * inten)
                put(s, x, y, (BEAM[0][0], BEAM[0][1], BEAM[0][2], a), "glow", frame)

        # Shaft body
        sill_y = WIN_TOP + WIN_H + 2
        top_half, bot_half = 5, 15
        for y in range(sill_y, foot_y + 1):
            t = (y - sill_y) / max(1, foot_y - sill_y)
            bx = int(cx + (foot_x - cx) * t)
            half = int(top_half + (bot_half - top_half) * t * t)  # widen faster near floor
            for dx in range(-half - 1, half + 2):
                edge = abs(dx) / max(1, half)
                if edge > 1.15:
                    continue
                core = max(0.0, 1.0 - edge ** 1.35)
                # Screen wash (soft)
                a_s = int((48 + 38 * core) * inten * (0.9 - 0.15 * t))
                put(s, bx + dx, y, (BEAM[1][0], BEAM[1][1], BEAM[1][2], a_s), "beams", frame)
                # Addition core (true brightening)
                if edge < 0.65:
                    a_a = int((28 + 50 * core) * inten * (0.75 + 0.15 * (1 - t)))
                    put(s, bx + dx, y, (BEAM[0][0], BEAM[0][1], BEAM[0][2], a_a), "glow", frame)

        # Floor light pool
        prx, pry = 17, 5
        for dy in range(-pry, pry + 1):
            for dx in range(-prx, prx + 1):
                e = (dx / prx) ** 2 + (dy / pry) ** 2
                if e > 1:
                    continue
                fall = 1.0 - math.sqrt(e)
                put(s, foot_x + dx, foot_y + dy,
                    (BEAM[0][0], BEAM[0][1], BEAM[0][2], int(85 * fall * inten)), "glow", frame)
                put(s, foot_x + dx, foot_y + dy,
                    (BEAM[1][0], BEAM[1][1], BEAM[1][2], int(55 * fall * inten)), "beams", frame)


def draw_dust(s: Sprite, frame: int) -> None:
    rng = random.Random(7)
    motes = []
    for i, cx in enumerate(WINDOW_CENTERS):
        foot_x, foot_y = beam_foot(cx)
        for _ in range(16):
            motes.append({
                "cx": cx, "foot_x": foot_x, "foot_y": foot_y,
                "along": rng.random(),
                "lat": rng.uniform(-0.75, 0.75),
                "speed": rng.uniform(0.25, 0.85),
                "phase": rng.random(),
                "bright": rng.random() > 0.72,
                "seed": rng.randint(0, 999),
            })

    sill_y = WIN_TOP + WIN_H + 2
    for m in motes:
        along = (m["along"] + frame * 0.028 * m["speed"]) % 1.0
        sway = math.sin((frame / FRAMES + m["phase"]) * math.tau) * 0.18
        t = along
        bx = m["cx"] + (m["foot_x"] - m["cx"]) * t
        by = sill_y + (m["foot_y"] - sill_y) * t
        half = 5 + (15 - 5) * (t * t)
        x = int(bx + (m["lat"] + sway) * half)
        y = int(by + wave_curve(frame, FRAMES, amplitude=0.8, phase=m["phase"]) * 0.5)
        fade = 0.45 if along < 0.07 or along > 0.93 else 1.0
        inten = flicker(frame, base=0.9, amount=0.18, seed=m["seed"])
        a = int((210 if m["bright"] else 130) * fade * inten)
        put(s, x, y, (DUST[0], DUST[1], DUST[2], a), "dust", frame)
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
    s.add_layer("shade", blend_mode="multiply", opacity=100)
    s.add_layer("beams", blend_mode="screen")
    s.add_layer("glow", blend_mode="addition")
    s.add_layer("dust", blend_mode="addition")

    for _ in range(1, FRAMES):
        s.add_frame(150)

    draw_vaulted_wall(s)
    draw_arched_window(s, 56, RUBY)
    draw_arched_window(s, 112, [SAPPH[0], EMER[1], SAPPH[2]])
    draw_arched_window(s, 168, AMBER)
    draw_mirror(s, 84, 52)
    draw_mirror(s, 140, 52)
    draw_floor(s)
    draw_carpet(s)
    draw_pillar(s, 17)
    draw_pillar(s, 206)
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
    png = s.preview(OUT / "hall_of_vigil.png", scale=3, frame=0, background=(10, 10, 14, 255))
    order = list(range(FRAMES)) + list(range(FRAMES - 2, 0, -1))
    gif = s.preview_gif(OUT / "hall_of_vigil.gif", scale=3, background=(10, 10, 14, 255), frames=order)

    img = s.composite_frame(0)
    fx, fy = beam_foot(112)
    print(f"saved {ase}")
    print(f"saved {png}")
    print(f"saved {gif}")
    print(f"center beam-foot {fx},{fy} -> {img.getpixel((fx, fy))}")
    print(f"carpet in beam -> {img.getpixel((W//2, 112))}")
    print(f"palette={len(PALETTE)} layers={[l.name+':'+l.blend_mode for l in s.layers]}")


if __name__ == "__main__":
    main()

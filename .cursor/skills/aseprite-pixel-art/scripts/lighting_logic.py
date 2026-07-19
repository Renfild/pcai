"""Lighting logic for pixel scenes — structured lights, washes, shafts.

Use with Sprite layers:
  shade  → multiply (ambient / AO / time-of-day)
  beams  → screen   (soft volume)
  glow   → addition (hot cores, lamps, magic)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

Color = Tuple[int, int, int, int]
Pixel = Tuple[int, int, Color]


def _clamp(v: float, lo: int = 0, hi: int = 255) -> int:
    return max(lo, min(hi, int(round(v))))


@dataclass
class LightSource:
    """A logical light in scene space."""

    x: float
    y: float
    color: Tuple[int, int, int] = (255, 210, 140)
    intensity: float = 1.0
    radius: float = 40.0
    kind: str = "point"  # point | shaft | shaft | ambient
    # shaft / spot extras
    aim_deg: float = 90.0      # 0=right, 90=down (screen y+)
    cone_deg: float = 35.0
    length: float = 60.0
    flicker_seed: int = 0
    cast_on: str = "glow"      # default FX layer name


@dataclass
class LightingSetup:
    """Scene lighting plan — apply to Sprite FX layers."""

    ambient: Tuple[int, int, int] = (180, 185, 200)  # multiply wash base
    ambient_strength: float = 0.35  # 0=no wash, 1=full darken toward ambient grey
    time_of_day: str = "day"  # dawn | day | dusk | night | magic
    lights: List[LightSource] = field(default_factory=list)

    def add_point(self, x, y, color=(255, 210, 140), intensity=1.0, radius=36, **kw) -> LightSource:
        lit = LightSource(x, y, color, intensity, radius, kind="point", **kw)
        self.lights.append(lit)
        return lit

    def add_shaft(self, x, y, aim_deg=90, length=70, cone_deg=30, color=(255, 220, 150), intensity=1.0, **kw) -> LightSource:
        lit = LightSource(
            x, y, color, intensity, radius=length, kind="shaft",
            aim_deg=aim_deg, cone_deg=cone_deg, length=length, **kw,
        )
        self.lights.append(lit)
        return lit

    def add_spot(self, x, y, aim_deg=90, cone_deg=40, radius=50, color=(255, 200, 120), intensity=1.0, **kw) -> LightSource:
        lit = LightSource(x, y, color, intensity, radius, kind="spot", aim_deg=aim_deg, cone_deg=cone_deg, **kw)
        self.lights.append(lit)
        return lit


# Time-of-day presets → ambient multiply color + strength
TIME_PRESETS = {
    "dawn":  ((200, 170, 160), 0.28),
    "day":   ((210, 215, 220), 0.18),
    "dusk":  ((180, 140, 130), 0.40),
    "night": ((90, 100, 140), 0.55),
    "magic": ((130, 100, 170), 0.42),
}


def apply_time_of_day(setup: LightingSetup, time: Optional[str] = None) -> LightingSetup:
    tod = time or setup.time_of_day
    if tod in TIME_PRESETS:
        setup.ambient, setup.ambient_strength = TIME_PRESETS[tod]
        setup.time_of_day = tod
    return setup


def flicker_intensity(frame: int, base: float = 1.0, amount: float = 0.15, seed: int = 0) -> float:
    t = frame * 0.37 + seed * 0.11
    wave = (
        math.sin(t) + 0.5 * math.sin(t * 2.3) + 0.25 * math.sin(t * 4.1)
    ) / 1.75
    jitter = ((math.sin((frame + seed) * 12.9898) * 43758.5453) % 1.0) - 0.5
    return max(0.0, base + amount * wave + amount * 0.2 * jitter)


def shade_wash_pixels(
    width: int,
    height: int,
    ambient: Tuple[int, int, int],
    strength: float,
    vignette: float = 0.25,
) -> List[Pixel]:
    """Full-frame multiply wash. strength 0..1; vignette darkens edges/ceiling."""
    pixels: List[Pixel] = []
    ar, ag, ab = ambient
    # Multiply layer color: lerp white→ambient by strength
    for y in range(height):
        for x in range(width):
            vx = abs(x - width / 2) / (width / 2)
            ceiling = max(0.0, 1.0 - y / max(1, height * 0.45))
            edge = max(0.0, vx - 0.55) / 0.45
            local = strength + vignette * (0.6 * ceiling + 0.4 * edge)
            local = min(1.0, local)
            # On multiply layers, grey closer to 255 = less effect
            gscale = 1.0 - local
            r = _clamp(255 * gscale + ar * local)
            g = _clamp(255 * gscale + ag * local)
            b = _clamp(255 * gscale + ab * local)
            if local > 0.02:
                pixels.append((x, y, (r, g, b, 255)))
    return pixels


def point_light_pixels(
    light: LightSource,
    frame: int = 0,
    falloff: float = 2.0,
) -> List[Pixel]:
    """Radial addition/screen glow for a point light."""
    inten = light.intensity * flicker_intensity(frame, seed=light.flicker_seed)
    cr, cg, cb = light.color
    rad = max(1.0, light.radius)
    pixels: List[Pixel] = []
    r_i = int(math.ceil(rad))
    cx, cy = int(round(light.x)), int(round(light.y))
    for y in range(cy - r_i, cy + r_i + 1):
        for x in range(cx - r_i, cx + r_i + 1):
            d = math.hypot(x - light.x, y - light.y) / rad
            if d > 1.0:
                continue
            t = (1.0 - d) ** falloff
            a = _clamp(220 * t * inten)
            if a > 0:
                pixels.append((x, y, (cr, cg, cb, a)))
    return pixels


def shaft_light_pixels(
    light: LightSource,
    frame: int = 0,
) -> Tuple[List[Pixel], List[Pixel]]:
    """God-ray cone. Returns (screen_pixels, addition_pixels)."""
    inten = light.intensity * flicker_intensity(frame, amount=0.12, seed=light.flicker_seed)
    cr, cg, cb = light.color
    aim = math.radians(light.aim_deg)
    half = math.radians(light.cone_deg) / 2.0
    length = max(1.0, light.length)
    screen: List[Pixel] = []
    add: List[Pixel] = []

    # March along aim
    steps = int(length) + 1
    for i in range(steps):
        t = i / max(1, steps - 1)
        dist = t * length
        # Cone widens with distance
        width = 1.5 + t * length * math.tan(half)
        bx = light.x + math.cos(aim) * dist
        by = light.y + math.sin(aim) * dist
        # Soft cross-section
        span = int(math.ceil(width * 1.3))
        for k in range(-span, span + 1):
            # Perpendicular offset
            px = bx + math.cos(aim + math.pi / 2) * k
            py = by + math.sin(aim + math.pi / 2) * k
            edge = abs(k) / max(0.5, width)
            if edge > 1.3:
                continue
            if edge <= 1.0:
                core = 0.5 + 0.5 * math.cos(edge * math.pi)
            else:
                core = 0.45 * max(0.0, 1.0 - (edge - 1.0) / 0.3)
            core *= core
            fade = 1.0 - 0.35 * t
            a_s = _clamp((65 + 50 * core) * inten * fade)
            a_a = _clamp((40 + 70 * core) * inten * fade) if edge < 0.85 else 0
            ix, iy = int(round(px)), int(round(py))
            if a_s > 0:
                screen.append((ix, iy, (cr, cg, cb, a_s)))
            if a_a > 0:
                add.append((ix, iy, (
                    min(255, cr + 20), min(255, cg + 15), min(255, cb + 10), a_a
                )))
    return screen, add


def spot_light_pixels(light: LightSource, frame: int = 0) -> List[Pixel]:
    """Cone-limited point light (lantern / flashlight)."""
    inten = light.intensity * flicker_intensity(frame, seed=light.flicker_seed)
    cr, cg, cb = light.color
    aim = math.radians(light.aim_deg)
    half = math.radians(light.cone_deg) / 2.0
    rad = max(1.0, light.radius)
    pixels: List[Pixel] = []
    r_i = int(math.ceil(rad))
    for y in range(int(light.y) - r_i, int(light.y) + r_i + 1):
        for x in range(int(light.x) - r_i, int(light.x) + r_i + 1):
            dx, dy = x - light.x, y - light.y
            d = math.hypot(dx, dy) / rad
            if d > 1.0 or d < 1e-6:
                continue
            ang = math.atan2(dy, dx)
            # Shortest angle delta
            delta = (ang - aim + math.pi) % math.tau - math.pi
            if abs(delta) > half * (1.0 + 0.3 * d):
                continue
            t = (1.0 - d) ** 1.8
            cone = 1.0 - abs(delta) / half
            a = _clamp(200 * t * cone * inten)
            if a > 0:
                pixels.append((x, y, (cr, cg, cb, a)))
    return pixels


def bake_lights(
    setup: LightingSetup,
    width: int,
    height: int,
    frame: int = 0,
) -> dict:
    """Compute all lighting pixels for one frame.

    Returns {
      'shade': [...],      # multiply wash
      'beams': [...],      # screen
      'glow':  [...],      # addition
    }
    """
    apply_time_of_day(setup)
    shade = shade_wash_pixels(width, height, setup.ambient, setup.ambient_strength)
    beams: List[Pixel] = []
    glow: List[Pixel] = []

    for lit in setup.lights:
        if lit.kind == "point":
            glow.extend(point_light_pixels(lit, frame))
        elif lit.kind == "shaft":
            sc, ad = shaft_light_pixels(lit, frame)
            beams.extend(sc)
            glow.extend(ad)
        elif lit.kind == "spot":
            glow.extend(spot_light_pixels(lit, frame))
        elif lit.kind == "ambient":
            pass
    return {"shade": shade, "beams": beams, "glow": glow}


def stamp_lighting(sprite, setup: LightingSetup, frame: int = 0,
                   shade_layer: str = "shade",
                   beams_layer: str = "beams",
                   glow_layer: str = "glow",
                   stamp_shade: bool = True) -> None:
    """Bake + stamp onto a Sprite for one frame."""
    layers = bake_lights(setup, sprite.width, sprite.height, frame)
    if stamp_shade and layers["shade"]:
        sprite.stamp(layers["shade"], layer=shade_layer, frame=frame)
    sprite.stamp(layers["beams"], layer=beams_layer, frame=frame)
    sprite.stamp(layers["glow"], layer=glow_layer, frame=frame)


def platformer_default_lights(
    width: int,
    height: int,
    ground_y: int,
    time: str = "dusk",
    windows: Optional[Sequence[Tuple[int, int]]] = None,
    lamps: Optional[Sequence[Tuple[int, int]]] = None,
) -> LightingSetup:
    """Opinionated lighting kit for a side-view platformer stage."""
    setup = LightingSetup(time_of_day=time)
    apply_time_of_day(setup)
    if windows:
        for i, (wx, wy) in enumerate(windows):
            setup.add_shaft(
                wx, wy, aim_deg=95 + (i - 1) * 8, length=height - wy - 8,
                cone_deg=28, color=(255, 220, 150), intensity=0.95,
                flicker_seed=10 + i,
            )
    if lamps:
        for i, (lx, ly) in enumerate(lamps):
            setup.add_point(lx, ly, color=(255, 170, 80), intensity=1.0, radius=28, flicker_seed=50 + i)
    # Subtle ground bounce fill
    setup.add_point(width // 2, ground_y - 4, color=(180, 160, 140), intensity=0.25, radius=width * 0.4, flicker_seed=0)
    return setup

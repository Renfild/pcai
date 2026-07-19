"""Reusable FX helpers for Aseprite pixel-art skills.

Animation curves, soft glows, flicker, and a tiny particle system so glow /
ember / spark layers don't need to be hand-derived every time.

All drawing helpers return iterables of (x, y, rgba) suitable for Sprite.stamp()
or write directly onto a Sprite when a sprite/layer/frame is provided.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple, Union

Color = Tuple[int, int, int, int]
Pixel = Tuple[int, int, Color]


def _clamp(v: float, lo: float = 0.0, hi: float = 255.0) -> int:
    return max(int(lo), min(int(hi), int(round(v))))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _color_scale(color: Color, alpha_scale: float) -> Color:
    r, g, b, a = color
    return (r, g, b, _clamp(a * alpha_scale))


# ---------------------------------------------------------------------------
# Animation curves
# ---------------------------------------------------------------------------

def wave_curve(
    frame: int,
    frames: int,
    amplitude: float = 1.0,
    phase: float = 0.0,
    cycles: float = 1.0,
) -> float:
    """Sine wave in [-amplitude, +amplitude] over an animation loop.

    phase is in turns (0..1). cycles is how many full waves per loop.
    """
    if frames <= 0:
        return 0.0
    t = (frame / frames) * cycles + phase
    return math.sin(t * math.tau) * amplitude


def walk_cycle(
    frame: int,
    frames: int = 8,
    stride: float = 2.0,
    bob: float = 1.0,
) -> dict:
    """Parametric 2-leg walk cycle offsets.

    Returns dict with:
      - contact / down / passing / up phase name
      - body_y: vertical bob (peaks at passing frames)
      - left_leg_x / right_leg_x / left_leg_y / right_leg_y
      - left_arm_x / right_arm_x
    """
    if frames <= 0:
        frames = 8
    # Normalize into one cycle
    phase = (frame % frames) / frames  # 0..1
    # Classic 4-beat walk: contact(0) → down(0.25) → passing(0.5) → up(0.75)
    if phase < 0.125 or phase >= 0.875:
        name = "contact"
    elif phase < 0.375:
        name = "down"
    elif phase < 0.625:
        name = "passing"
    else:
        name = "up"

    # Body bob peaks at passing (phase 0.5): positive body_y = upward.
    # Callers should subtract body_y from sprite y (y grows downward).
    body_y = -math.cos(phase * math.tau) * bob

    # Legs: opposite sin swings
    leg_swing = math.sin(phase * math.tau) * stride
    left_leg_x = leg_swing
    right_leg_x = -leg_swing
    # Planted foot lower (positive y down) at contact extremes
    left_leg_y = max(0.0, math.cos(phase * math.tau)) * (bob * 0.5)
    right_leg_y = max(0.0, -math.cos(phase * math.tau)) * (bob * 0.5)

    # Arms opposite legs
    left_arm_x = -leg_swing * 0.7
    right_arm_x = leg_swing * 0.7

    return {
        "phase": name,
        "t": phase,
        "body_y": body_y,
        "left_leg_x": left_leg_x,
        "right_leg_x": right_leg_x,
        "left_leg_y": left_leg_y,
        "right_leg_y": right_leg_y,
        "left_arm_x": left_arm_x,
        "right_arm_x": right_arm_x,
    }


# ---------------------------------------------------------------------------
# Glow / flicker
# ---------------------------------------------------------------------------

def radial_glow(
    cx: int,
    cy: int,
    radius: int,
    color: Color,
    falloff: float = 2.0,
    hollow: float = 0.0,
) -> List[Pixel]:
    """Soft circular light. falloff >1 = tighter core; hollow>0 leaves a clear center.

    Returns pixels with alpha faded by distance. Stamp onto an 'addition' layer.
    """
    pixels: List[Pixel] = []
    r, g, b, a = color
    rad = max(1, radius)
    for y in range(cy - rad, cy + rad + 1):
        for x in range(cx - rad, cx + rad + 1):
            dist = math.hypot(x - cx, y - cy) / rad
            if dist > 1.0:
                continue
            if hollow > 0 and dist < hollow:
                continue
            # Smooth falloff
            t = 1.0 - dist
            t = t ** falloff
            aa = _clamp(a * t)
            if aa > 0:
                pixels.append((x, y, (r, g, b, aa)))
    return pixels


def flicker(
    frame: int,
    base: float = 1.0,
    amount: float = 0.15,
    seed: int = 0,
    speeds: Sequence[float] = (1.0, 2.3, 4.1),
) -> float:
    """Organic torch/candle intensity multiplier around `base`.

    Combines a few incommensurate sines plus a tiny hash jitter so the flame
    doesn't look like a pure sine.
    """
    t = frame * 0.37 + seed * 0.11
    wave = 0.0
    weight = 0.0
    for i, spd in enumerate(speeds):
        w = 1.0 / (i + 1)
        wave += w * math.sin(t * spd + i * 1.7)
        weight += w
    wave /= max(weight, 1e-6)
    # Deterministic micro-jitter
    jitter = ((math.sin((frame + seed) * 12.9898) * 43758.5453) % 1.0) - 0.5
    return max(0.0, base + amount * wave + amount * 0.25 * jitter)


# ---------------------------------------------------------------------------
# Particle system
# ---------------------------------------------------------------------------

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: Color
    size: int = 1
    gravity: float = 0.0
    drag: float = 0.0


@dataclass
class ParticleSystem:
    particles: List[Particle] = field(default_factory=list)

    def alive(self) -> List[Particle]:
        return [p for p in self.particles if p.life > 0]


def spawn_burst(
    cx: float,
    cy: float,
    count: int = 12,
    color: Color = (255, 180, 60, 220),
    speed: float = 1.2,
    life: float = 8.0,
    life_jitter: float = 3.0,
    cone_deg: float = 360.0,
    aim_deg: float = -90.0,
    gravity: float = 0.05,
    drag: float = 0.02,
    size: int = 1,
    seed: Optional[int] = None,
) -> ParticleSystem:
    """Spawn a burst of particles. aim_deg: 0=right, -90=up (screen y-down)."""
    rng = random.Random(seed)
    half = math.radians(cone_deg) / 2.0
    aim = math.radians(aim_deg)
    system = ParticleSystem()
    for _ in range(count):
        angle = aim + rng.uniform(-half, half)
        spd = speed * rng.uniform(0.4, 1.0)
        vx = math.cos(angle) * spd
        vy = math.sin(angle) * spd
        max_life = max(1.0, life + rng.uniform(-life_jitter, life_jitter))
        # Slight color jitter
        r, g, b, a = color
        jittered = (
            _clamp(r + rng.randint(-12, 12)),
            _clamp(g + rng.randint(-12, 12)),
            _clamp(b + rng.randint(-12, 12)),
            a,
        )
        system.particles.append(
            Particle(
                x=cx + rng.uniform(-0.3, 0.3),
                y=cy + rng.uniform(-0.3, 0.3),
                vx=vx,
                vy=vy,
                life=max_life,
                max_life=max_life,
                color=jittered,
                size=size,
                gravity=gravity,
                drag=drag,
            )
        )
    return system


def simulate_particles(system: ParticleSystem, steps: int = 1) -> ParticleSystem:
    """Advance particles by `steps` frames (mutates and returns system)."""
    for _ in range(max(1, steps)):
        for p in system.particles:
            if p.life <= 0:
                continue
            p.vy += p.gravity
            p.vx *= 1.0 - p.drag
            p.vy *= 1.0 - p.drag
            p.x += p.vx
            p.y += p.vy
            p.life -= 1.0
    return system


def stamp_particles(
    system: ParticleSystem,
    fade: bool = True,
) -> List[Pixel]:
    """Convert living particles to pixels. Alpha fades with remaining life."""
    pixels: List[Pixel] = []
    for p in system.alive():
        t = p.life / p.max_life if p.max_life > 0 else 0.0
        color = _color_scale(p.color, t if fade else 1.0)
        ix, iy = int(round(p.x)), int(round(p.y))
        if p.size <= 1:
            pixels.append((ix, iy, color))
        else:
            r = p.size // 2
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r:
                        pixels.append((ix + dx, iy + dy, color))
    return pixels


def ember_trail(
    cx: int,
    cy: int,
    frames: int,
    color: Color = (255, 140, 40, 200),
    count: int = 6,
    rise: float = 0.9,
    seed: int = 0,
) -> List[List[Pixel]]:
    """Convenience: rising ember particles across `frames` for a torch/campfire.

    Returns a list of per-frame pixel lists. Continuously respawns so the trail
    stays dense.
    """
    rng = random.Random(seed)
    system = ParticleSystem()
    out: List[List[Pixel]] = []
    for fi in range(frames):
        # Respawn a few each frame
        for _ in range(max(1, count // 3)):
            if len(system.alive()) >= count:
                break
            burst = spawn_burst(
                cx + rng.uniform(-1.0, 1.0),
                cy,
                count=1,
                color=color,
                speed=rise,
                life=6.0,
                life_jitter=2.0,
                cone_deg=50.0,
                aim_deg=-90.0,
                gravity=-0.02,  # slight extra rise
                drag=0.04,
                seed=seed + fi * 17 + _,
            )
            system.particles.extend(burst.particles)
        simulate_particles(system, 1)
        out.append(stamp_particles(system))
    return out


# ---------------------------------------------------------------------------
# Optional Sprite integration (duck-typed to avoid hard import cycles)
# ---------------------------------------------------------------------------

def apply_glow(sprite, layer: Union[str, int], frame: int, pixels: Iterable[Pixel]) -> None:
    """Stamp glow/particle pixels onto sprite via stamp() if available."""
    stamp = getattr(sprite, "stamp", None)
    if stamp is None:
        raise TypeError("sprite does not support stamp()")
    stamp(pixels, layer=layer, frame=frame)

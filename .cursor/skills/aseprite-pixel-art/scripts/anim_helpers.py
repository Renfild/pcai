"""Platformer animation curves — idle / run / jump / fall / land / attack.

Returns per-frame offset dicts so character build scripts stay parametric.
Positive body_y = upward (subtract from sprite y; y grows downward).
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence


def _clamp01(t: float) -> float:
    return max(0.0, min(1.0, t))


def ease_out_quad(t: float) -> float:
    t = _clamp01(t)
    return 1.0 - (1.0 - t) * (1.0 - t)


def ease_in_quad(t: float) -> float:
    t = _clamp01(t)
    return t * t


def ease_in_out(t: float) -> float:
    t = _clamp01(t)
    return 3 * t * t - 2 * t * t * t


def idle_breath(
    frame: int,
    frames: int = 6,
    chest: float = 0.6,
    head: float = 0.4,
) -> Dict[str, float]:
    """Subtle breathing idle. Peaks mid-loop."""
    if frames <= 0:
        frames = 6
    t = (frame % frames) / frames
    s = math.sin(t * math.tau)
    return {
        "phase": "idle",
        "t": t,
        "body_y": s * chest * 0.35,
        "chest_y": -s * chest,   # expand up
        "head_y": -s * head,
        "arm_y": s * 0.25,
    }


def run_cycle(
    frame: int,
    frames: int = 8,
    stride: float = 3.0,
    bob: float = 1.2,
    lean: float = 1.0,
) -> Dict[str, float]:
    """Platformer run — stronger stride/lean than walk_cycle."""
    if frames <= 0:
        frames = 8
    phase = (frame % frames) / frames
    if phase < 0.125 or phase >= 0.875:
        name = "contact"
    elif phase < 0.375:
        name = "down"
    elif phase < 0.625:
        name = "passing"
    else:
        name = "up"

    body_y = -math.cos(phase * math.tau) * bob
    swing = math.sin(phase * math.tau) * stride
    return {
        "phase": name,
        "t": phase,
        "body_y": body_y,
        "body_lean_x": lean * 0.6,  # forward lean (facing right)
        "left_leg_x": swing,
        "right_leg_x": -swing,
        "left_leg_y": max(0.0, math.cos(phase * math.tau)) * (bob * 0.55),
        "right_leg_y": max(0.0, -math.cos(phase * math.tau)) * (bob * 0.55),
        "left_arm_x": -swing * 0.85,
        "right_arm_x": swing * 0.85,
    }


def jump_arc(
    frame: int,
    frames: int = 6,
    height: float = 8.0,
    stretch: float = 1.0,
) -> Dict[str, float]:
    """Jump pose timeline: crouch → launch → hang → fall-start.

    frames typically 4–8 covering the whole airborne beat.
    """
    if frames <= 0:
        frames = 6
    t = _clamp01(frame / max(1, frames - 1))
    # Parabola peak at t=0.45
    y = height * (4.0 * t * (1.0 - t))
    if t < 0.18:
        name = "crouch"
        squash = 1.0 + (0.18 - t) / 0.18 * 0.35
        stretch_y = 1.0 - (0.18 - t) / 0.18 * 0.25
    elif t < 0.45:
        name = "rise"
        squash = 0.9
        stretch_y = 1.0 + stretch * 0.2
    elif t < 0.6:
        name = "hang"
        squash = 1.0
        stretch_y = 1.0
    else:
        name = "fall"
        squash = 0.95
        stretch_y = 1.0 + stretch * 0.15
    return {
        "phase": name,
        "t": t,
        "body_y": y,
        "squash_x": squash,
        "stretch_y": stretch_y,
        "arm_up": 1.0 if name in ("rise", "hang") else 0.3,
        "legs_tuck": 1.0 if name in ("rise", "hang") else 0.2,
    }


def land_squash(
    frame: int,
    frames: int = 3,
    amount: float = 0.4,
) -> Dict[str, float]:
    """Landing recovery: squash then settle."""
    if frames <= 0:
        frames = 3
    t = _clamp01(frame / max(1, frames - 1))
    # Peak squash at start, ease out
    squash = amount * (1.0 - ease_out_quad(t))
    return {
        "phase": "land",
        "t": t,
        "body_y": -squash * 2.0,  # sink into ground
        "squash_x": 1.0 + squash,
        "stretch_y": 1.0 - squash * 0.7,
        "dust": 1.0 - t,
    }


def attack_swing(
    frame: int,
    frames: int = 5,
    reach: float = 6.0,
) -> Dict[str, float]:
    """Melee swing: windup → strike → recovery."""
    if frames <= 0:
        frames = 5
    t = _clamp01(frame / max(1, frames - 1))
    if t < 0.3:
        name = "windup"
        u = t / 0.3
        arm = -reach * 0.4 * ease_out_quad(u)
        body = -0.5 * u
    elif t < 0.55:
        name = "strike"
        u = (t - 0.3) / 0.25
        arm = _lerp(-reach * 0.4, reach, ease_in_quad(u))
        body = _lerp(-0.5, 1.0, u)
    else:
        name = "recover"
        u = (t - 0.55) / 0.45
        arm = _lerp(reach, 0.0, ease_out_quad(u))
        body = _lerp(1.0, 0.0, u)
    return {
        "phase": name,
        "t": t,
        "arm_x": arm,
        "body_x": body,
        "body_y": 0.3 if name == "strike" else 0.0,
        "slash": 1.0 if name == "strike" else 0.0,
    }


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def anim_tag_plan(
    actions: Sequence[str] = ("idle", "run", "jump", "fall", "land"),
    frame_counts: Dict[str, int] | None = None,
) -> List[Dict]:
    """Allocate frame ranges + suggested durations for a character sheet.

    Returns list of {name, from, to, duration_ms, direction}.
    """
    counts = {
        "idle": 6,
        "run": 8,
        "jump": 4,
        "fall": 2,
        "land": 3,
        "attack": 5,
        "hurt": 2,
        "death": 4,
    }
    if frame_counts:
        counts.update(frame_counts)
    durations = {
        "idle": 120,
        "run": 70,
        "jump": 80,
        "fall": 90,
        "land": 70,
        "attack": 60,
        "hurt": 100,
        "death": 110,
    }
    plan = []
    cursor = 0
    for name in actions:
        n = counts.get(name, 4)
        plan.append({
            "name": name,
            "from": cursor,
            "to": cursor + n - 1,
            "frames": n,
            "duration_ms": durations.get(name, 100),
            "direction": "forward",
        })
        cursor += n
    return plan


def pose_for(action: str, frame: int, **kwargs) -> Dict[str, float]:
    """Dispatch helper — pick the right curve by action name."""
    action = action.lower()
    if action == "idle":
        return idle_breath(frame, **{k: kwargs[k] for k in ("frames", "chest", "head") if k in kwargs})
    if action in ("run", "walk"):
        return run_cycle(frame, **{k: kwargs[k] for k in ("frames", "stride", "bob", "lean") if k in kwargs})
    if action == "jump":
        return jump_arc(frame, **{k: kwargs[k] for k in ("frames", "height", "stretch") if k in kwargs})
    if action == "land":
        return land_squash(frame, **{k: kwargs[k] for k in ("frames", "amount") if k in kwargs})
    if action == "attack":
        return attack_swing(frame, **{k: kwargs[k] for k in ("frames", "reach") if k in kwargs})
    if action == "fall":
        # Reuse late jump_arc
        frames = kwargs.get("frames", 2)
        return jump_arc(frames, frames=frames + 2, height=kwargs.get("height", 2.0))
    return {"phase": action, "t": 0.0, "body_y": 0.0}

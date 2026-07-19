"""Platformer animation curves — idle / run / jump / fall / land / attack.

Lessons baked in (Slynyrd Pixelblog 8 — Intro to Animation):
  - Strong keyframes first (contact / pass / stride); in-betweens are optional
  - Energy > smoothness — fewer frames often read stronger
  - 6-frame run is a sweet default; 3-frame Mega Man style still works
  - Playback duration must scale when frames are removed (8@80ms → 4@160ms)
  - Hold extremes on idle for a less robotic feel (Pixelblog 55)

Positive body_y = upward (subtract from sprite y; y grows downward).
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple


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


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# ---------------------------------------------------------------------------
# Playback timing (energy preservation when economizing frames)
# ---------------------------------------------------------------------------

# Baseline: 8-frame run @ 80ms/frame. Halve frames → double duration.
RUN_BASE_FRAMES = 8
RUN_BASE_MS = 80


def frame_duration_ms(frames: int, base_frames: int = RUN_BASE_FRAMES, base_ms: int = RUN_BASE_MS) -> int:
    """Scale frame duration so total cycle energy stays similar when cutting frames."""
    frames = max(1, frames)
    return max(40, int(round(base_ms * base_frames / frames)))


def run_frame_durations(frames: int = 6) -> List[int]:
    """Per-frame ms list for a run cycle (uniform; use hold_pattern for idle)."""
    d = frame_duration_ms(frames)
    return [d] * frames


def hold_pattern(frames: int, hold_ends: int = 2, mid_ms: int = 90, hold_ms: int = 140) -> List[int]:
    """Offset timing: hold first/last frames longer (life-like idle / breathe).

    Pixelblog 55: uniform playback feels robotic; hold extremities longer.
    """
    if frames <= 2:
        return [hold_ms] * frames
    out = []
    for i in range(frames):
        if i < hold_ends or i >= frames - hold_ends:
            out.append(hold_ms)
        else:
            out.append(mid_ms)
    return out


# ---------------------------------------------------------------------------
# Idle
# ---------------------------------------------------------------------------

def idle_breath(
    frame: int,
    frames: int = 6,
    chest: float = 0.6,
    head: float = 0.4,
    hold_extremes: bool = True,
) -> Dict[str, float]:
    """Subtle breathing idle.

    When hold_extremes=True, phase spends more time at inhale/exhale peaks
    (ease the sine) so the loop feels less mechanical.
    """
    if frames <= 0:
        frames = 6
    t = (frame % frames) / frames
    if hold_extremes:
        # flatten near peaks: slower at extremes
        s = math.sin(t * math.tau)
        s = math.copysign(abs(s) ** 0.75, s)
    else:
        s = math.sin(t * math.tau)
    return {
        "phase": "idle",
        "t": t,
        "body_y": s * chest * 0.35,
        "chest_y": -s * chest,   # expand up
        "head_y": -s * head,
        "arm_y": s * 0.25,
        "durations_ms": hold_pattern(frames) if hold_extremes else [120] * frames,
    }


# ---------------------------------------------------------------------------
# Run — keyframe-first (Pixelblog 8)
# ---------------------------------------------------------------------------

# Canonical keyframe names in one stride + opposite stride
# 3-frame: stride_a, pass, stride_b  (pass reused conceptually)
# 4-frame: contact, pass, contact_opp, high (or contact, down, pass, up)
# 6-frame: drop recoil (recommended default)
# 8-frame: full including recoil + high

def _run_phase_name(phase: float, frames: int) -> str:
    """Map normalized phase to keyframe role."""
    if frames <= 3:
        # Mega Man style: stride / pass / stride
        if phase < 1 / 3:
            return "stride"
        if phase < 2 / 3:
            return "pass"
        return "stride"
    if frames <= 4:
        if phase < 0.25:
            return "contact"
        if phase < 0.5:
            return "pass"
        if phase < 0.75:
            return "contact"
        return "up"
    # 6–8: classic contact → down → passing → up
    if phase < 0.125 or phase >= 0.875:
        return "contact"
    if phase < 0.375:
        return "down" if frames >= 6 else "pass"
    if phase < 0.625:
        return "passing"
    return "up"


def _variable_bob(phase: float, bob: float, frames: int) -> float:
    """Non-sine bob: down, down, up-fast (Pixelblog 55).

    One stride relative deltas ≈ -1, -1, +2 (scaled by bob).
    Positive return = upward.
    """
    # Build piecewise over half-cycle then mirror
    # Map phase 0..1 across two strides
    local = (phase * 2.0) % 1.0  # one stride 0..1
    # 0..0.33 sink, 0.33..0.66 sink more, 0.66..1.0 snap up through pass
    if local < 1 / 3:
        y = -bob * (0.35 + 0.35 * (local * 3))
    elif local < 2 / 3:
        y = -bob * (0.7 + 0.3 * ((local - 1 / 3) * 3))
    else:
        # Fast up through pass (legs together)
        u = (local - 2 / 3) * 3
        y = _lerp(-bob, bob * 0.85, ease_out_quad(u))
    return y


def run_cycle(
    frame: int,
    frames: int = 6,
    stride: float = 3.0,
    bob: float = 1.2,
    lean: float = 1.0,
    variable_bob: bool = True,
) -> Dict[str, float]:
    """Platformer run — keyframe-aware, energy-first.

    Default 6 frames (Slynyrd): contact+pass preserved, recoil dropped.
    Set frames=3 for Mega Man economical style; frames=8 for full smooth.
    """
    if frames <= 0:
        frames = 6
    frames = int(frames)
    phase = (frame % frames) / frames
    name = _run_phase_name(phase, frames)

    if variable_bob:
        body_y = _variable_bob(phase, bob, frames)
    else:
        body_y = -math.cos(phase * math.tau) * bob

    # Powerful stride: limbs extended at contact/stride; tucked at pass
    swing = math.sin(phase * math.tau) * stride
    if name == "pass" or name == "passing":
        swing *= 0.35  # limbs close to body (Pixelblog 8 pass frame)
    if name == "stride":
        swing = math.copysign(stride, math.sin(phase * math.tau) or 1.0)

    return {
        "phase": name,
        "t": phase,
        "body_y": body_y,
        "body_lean_x": lean * (0.85 if name in ("stride", "contact", "down") else 0.45),
        "left_leg_x": swing,
        "right_leg_x": -swing,
        "left_leg_y": max(0.0, math.cos(phase * math.tau)) * (bob * 0.55),
        "right_leg_y": max(0.0, -math.cos(phase * math.tau)) * (bob * 0.55),
        "left_arm_x": -swing * 0.85,
        "right_arm_x": swing * 0.85,
        "duration_ms": frame_duration_ms(frames),
        "keyframes": run_keyframe_guide(frames),
    }


def run_keyframe_guide(frames: int = 6) -> List[str]:
    """Which keyframe roles exist for this frame count (for authors / tags)."""
    if frames <= 3:
        return ["stride", "pass", "stride"]
    if frames <= 4:
        return ["contact", "pass", "contact", "up"]
    if frames <= 6:
        # recoil removed from 8
        return ["contact", "down", "passing", "up", "contact", "passing"]
    return ["contact", "down", "passing", "up", "contact", "down", "passing", "up"]


def economize_run_frames(full_frames: int = 8, target: int = 6) -> List[int]:
    """Indices to KEEP when reducing an 8-frame run (Pixelblog 8 recipe).

    8→6: drop recoil frames
    8→4: drop recoil + high point
    """
    # Canonical 8 indices: 0 contact, 1 recoil/down, 2 passing, 3 up/high,
    #                      4 contact, 5 recoil, 6 passing, 7 up
    if full_frames != 8:
        step = full_frames / target
        return [min(full_frames - 1, int(i * step)) for i in range(target)]
    if target >= 8:
        return list(range(8))
    if target == 6:
        return [0, 2, 3, 4, 6, 7]  # drop recoil 1,5
    if target == 4:
        return [0, 2, 4, 6]  # contact + pass only (drop recoil + high)
    if target == 3:
        return [0, 2, 4]
    # generic subsample
    return [int(i * 8 / target) for i in range(target)]


# ---------------------------------------------------------------------------
# Jump / land / attack
# ---------------------------------------------------------------------------

def jump_arc(
    frame: int,
    frames: int = 6,
    height: float = 8.0,
    stretch: float = 1.0,
) -> Dict[str, float]:
    """Jump pose timeline: crouch → launch → hang → fall-start.

    Keyframes: crouch + hang are the dramatic poses — keep them readable alone.
    """
    if frames <= 0:
        frames = 6
    t = _clamp01(frame / max(1, frames - 1))
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
    squash = amount * (1.0 - ease_out_quad(t))
    return {
        "phase": "land",
        "t": t,
        "body_y": -squash * 2.0,
        "squash_x": 1.0 + squash,
        "stretch_y": 1.0 - squash * 0.7,
        "dust": 1.0 - t,
    }


def attack_swing(
    frame: int,
    frames: int = 5,
    reach: float = 6.0,
) -> Dict[str, float]:
    """Melee swing: windup → strike → recovery (keyframes: windup + strike)."""
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


def anim_tag_plan(
    actions: Sequence[str] = ("idle", "run", "jump", "fall", "land"),
    frame_counts: Optional[Dict[str, int]] = None,
) -> List[Dict]:
    """Allocate frame ranges + suggested durations for a character sheet.

    Run defaults to 6 frames @ scaled ms (energy-preserving).
    Idle uses hold_pattern durations (stored as duration_ms average + list).
    """
    counts = {
        "idle": 6,
        "run": 6,
        "jump": 4,
        "fall": 2,
        "land": 3,
        "attack": 5,
        "hurt": 2,
        "death": 4,
    }
    if frame_counts:
        counts.update(frame_counts)
    plan = []
    cursor = 0
    for name in actions:
        n = counts.get(name, 4)
        if name == "run":
            durs = run_frame_durations(n)
            dur = durs[0]
        elif name == "idle":
            durs = hold_pattern(n)
            dur = sum(durs) // len(durs)
        else:
            defaults = {
                "jump": 80, "fall": 90, "land": 70, "attack": 60,
                "hurt": 100, "death": 110,
            }
            dur = defaults.get(name, 100)
            durs = [dur] * n
        plan.append({
            "name": name,
            "from": cursor,
            "to": cursor + n - 1,
            "frames": n,
            "duration_ms": dur,
            "durations_ms": durs,
            "direction": "forward",
        })
        cursor += n
    return plan


def pose_for(action: str, frame: int, **kwargs) -> Dict[str, float]:
    """Dispatch helper — pick the right curve by action name."""
    action = action.lower()
    if action == "idle":
        keys = ("frames", "chest", "head", "hold_extremes")
        return idle_breath(frame, **{k: kwargs[k] for k in keys if k in kwargs})
    if action in ("run", "walk"):
        keys = ("frames", "stride", "bob", "lean", "variable_bob")
        return run_cycle(frame, **{k: kwargs[k] for k in keys if k in kwargs})
    if action == "jump":
        keys = ("frames", "height", "stretch")
        return jump_arc(frame, **{k: kwargs[k] for k in keys if k in kwargs})
    if action == "land":
        keys = ("frames", "amount")
        return land_squash(frame, **{k: kwargs[k] for k in keys if k in kwargs})
    if action == "attack":
        keys = ("frames", "reach")
        return attack_swing(frame, **{k: kwargs[k] for k in keys if k in kwargs})
    if action == "fall":
        frames = kwargs.get("frames", 2)
        return jump_arc(frames, frames=frames + 2, height=kwargs.get("height", 2.0))
    return {"phase": action, "t": 0.0, "body_y": 0.0}

"""Top-down (3/4) character animation helpers.

Lessons from Slynyrd Pixelblog 55 — Top Down Character Animation:
  - Conform character size to tile grid (e.g. 26×32 ≈ 1×2 of 16×16 tiles)
  - 4-dir facing can still support 8-dir movement (Zelda LttP style)
  - Full 8-dir: design 5 unique orientations, flip for the rest when symmetric
  - 6-frame run is the economy/smoothness sweet spot for small sprites
  - Variable bob (down 1, down 1, up 2) — not a pure sine
  - Hold idle extremes longer than in-betweens
  - Design for motion clarity: simplify noisy details before animating
  - Layer gear (cape/weapon) separately for equipment swaps

Directions use screen space: N=up, E=right, S=down, W=left.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from anim_helpers import frame_duration_ms, hold_pattern, run_cycle, idle_breath

# 8-way + 4-way sets
DIR8 = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
DIR4 = ("N", "E", "S", "W")

# Unique orientations to author when figure is left/right symmetric
# Flip map: authored → mirrored
FLIP_FROM = {
    "W": "E",
    "NW": "NE",
    "SW": "SE",
}


@dataclass
class TopDownProfile:
    """Sizing + anim defaults for a top-down hero."""

    tile: int = 16
    width: int = 26
    height: int = 32  # ≈ 2 tiles tall
    directions: int = 8  # 4 or 8
    run_frames: int = 6
    idle_frames: int = 4
    # Bob amplitudes (px)
    run_bob: float = 1.5
    idle_bob: float = 0.5
    stride: float = 2.5

    def footprint(self) -> Tuple[int, int]:
        """Tile footprint (cols, rows) rounded up."""
        return (
            max(1, (self.width + self.tile - 1) // self.tile),
            max(1, (self.height + self.tile - 1) // self.tile),
        )


def directions_for(n: int = 8) -> Tuple[str, ...]:
    return DIR8 if n >= 8 else DIR4


def authoring_directions(n: int = 8, symmetric: bool = True) -> List[str]:
    """Directions you must draw; others come from flips when symmetric."""
    if n <= 4:
        return list(DIR4)
    if not symmetric:
        return list(DIR8)
    # 5 unique: N, NE, E, SE, S
    return ["N", "NE", "E", "SE", "S"]


def resolve_orientation(direction: str, symmetric: bool = True) -> Tuple[str, bool]:
    """Return (source_direction, flip_x) for drawing."""
    d = direction.upper()
    if not symmetric:
        return d, False
    if d in FLIP_FROM:
        return FLIP_FROM[d], True
    return d, False


def dir_vector(direction: str) -> Tuple[float, float]:
    """Unit-ish movement vector for direction (x right, y down)."""
    d = direction.upper()
    table = {
        "N": (0, -1), "NE": (1, -1), "E": (1, 0), "SE": (1, 1),
        "S": (0, 1), "SW": (-1, 1), "W": (-1, 0), "NW": (-1, -1),
    }
    vx, vy = table.get(d, (0, 1))
    mag = math.hypot(vx, vy) or 1.0
    return vx / mag, vy / mag


def facing_from_velocity(vx: float, vy: float, directions: int = 8) -> str:
    """Snap velocity to nearest facing. Prefer 4-dir if |vx|≈|vy| and dirs==4."""
    if abs(vx) < 1e-6 and abs(vy) < 1e-6:
        return "S"
    ang = math.degrees(math.atan2(vx, -vy)) % 360  # 0 = N, 90 = E
    if directions <= 4:
        sector = int((ang + 45) // 90) % 4
        return DIR4[sector]
    sector = int((ang + 22.5) // 45) % 8
    return DIR8[sector]


# ---------------------------------------------------------------------------
# Pose curves
# ---------------------------------------------------------------------------

def topdown_idle(
    frame: int,
    frames: int = 4,
    bob: float = 0.5,
    direction: str = "S",
) -> Dict:
    """Idle with held extremes + small bob. Hair/cape secondary motion hooks."""
    base = idle_breath(frame, frames=frames, chest=bob, head=bob * 0.7, hold_extremes=True)
    src, flip = resolve_orientation(direction)
    return {
        **base,
        "direction": direction.upper(),
        "source_direction": src,
        "flip_x": flip,
        "hair_shift": 1 if (frame % frames) in (1, frames - 1) else 0,  # PB55 hair tip
        "durations_ms": hold_pattern(frames, hold_ends=1, mid_ms=100, hold_ms=160),
    }


def topdown_run(
    frame: int,
    frames: int = 6,
    bob: float = 1.5,
    stride: float = 2.5,
    direction: str = "S",
) -> Dict:
    """6-frame top-down run with variable bob (down, down, up-fast)."""
    base = run_cycle(
        frame, frames=frames, stride=stride, bob=bob,
        lean=0.35, variable_bob=True,
    )
    src, flip = resolve_orientation(direction)
    vx, vy = dir_vector(direction)
    # Shoulder/leg swing projected onto facing
    swing = base["left_leg_x"]
    return {
        **base,
        "direction": direction.upper(),
        "source_direction": src,
        "flip_x": flip,
        "move_x": vx,
        "move_y": vy,
        "leg_fwd": swing * (1.0 if abs(vx) >= abs(vy) else 0.55),
        "duration_ms": frame_duration_ms(frames),
        # Head bob is the core expression (PB55)
        "head_y": base["body_y"],
        "shoulder_y": base["body_y"] * 0.6,
    }


def topdown_sheet_plan(
    profile: Optional[TopDownProfile] = None,
    include_run: bool = True,
    include_idle: bool = True,
) -> Dict:
    """Plan a spritesheet layout: directions × actions × frames.

    Returns metadata an exporter / build script can use to place cels.
    """
    profile = profile or TopDownProfile()
    dirs = authoring_directions(profile.directions, symmetric=True)
    actions = []
    cursor = 0
    if include_idle:
        n = profile.idle_frames
        durs = hold_pattern(n)
        actions.append({
            "name": "idle",
            "frames": n,
            "from": cursor,
            "to": cursor + n - 1,
            "durations_ms": durs,
            "directions": dirs,
        })
        cursor += n
    if include_run:
        n = profile.run_frames
        d = frame_duration_ms(n)
        actions.append({
            "name": "run",
            "frames": n,
            "from": cursor,
            "to": cursor + n - 1,
            "durations_ms": [d] * n,
            "directions": dirs,
        })
        cursor += n
    return {
        "profile": {
            "w": profile.width, "h": profile.height, "tile": profile.tile,
            "footprint": list(profile.footprint()),
            "directions": profile.directions,
        },
        "authoring_directions": dirs,
        "flip_map": dict(FLIP_FROM),
        "actions": actions,
        "total_frames_per_dir": cursor,
        "notes": [
            "Author only authoring_directions; flip for W/NW/SW when symmetric",
            "Sync all directions in a circle after roughing — compare head bob & stride",
            "Simplify design until motion stays clear at 1x",
        ],
    }


def sync_check_bobs(
    poses_by_dir: Dict[str, Sequence[Dict]],
    key: str = "body_y",
    tol: float = 0.75,
) -> List[str]:
    """Warn if body/head bob magnitudes diverge across directions (PB55 sync tip)."""
    warnings = []
    if not poses_by_dir:
        return warnings
    # Compare peak bob per direction
    peaks = {d: max(abs(p.get(key, 0.0)) for p in poses) for d, poses in poses_by_dir.items()}
    avg = sum(peaks.values()) / len(peaks)
    for d, peak in peaks.items():
        if abs(peak - avg) > tol:
            warnings.append(f"{d} {key} peak={peak:.2f} diverges from avg={avg:.2f}")
    return warnings

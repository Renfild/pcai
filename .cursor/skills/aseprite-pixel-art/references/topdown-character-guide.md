# Top-Down Character Animation Guide

Principles adapted from [Slynyrd Pixelblog 55 — Top Down Character Animation](https://www.slynyrd.com/blog/2025/3/24/pixelblog-55-top-down-character-animation).

## Projection & size

- Use **3/4 top-down** (front + top visible) — Chrono Trigger / classic RPG feel
- Size assets to the **tile grid**. Example: 26×32px ≈ 1×2 of 16×16 tiles (`TopDownProfile`)
- Even without real tiles, grid-coherent sizing keeps levels and characters cohesive

## 4 directions vs 8

| Approach | Facing | Movement | Notes |
|---|---|---|---|
| Zelda LttP style | 4 (N/E/S/W) | can be 8-way | Wide attacks / strafe compensate angles |
| Full 8-dir | 8 facings | 8-way | Demands more from levels & enemies |

Bang-for-buck: 4-dir facing + 8-dir move is still valid. Full 8-dir is for modern feel.

## Authoring economy

If the figure is left/right **symmetric**, author **5 orientations** (N, NE, E, SE, S) and flip for W/NW/SW.

```python
from topdown_anim import authoring_directions, resolve_orientation, topdown_sheet_plan

dirs = authoring_directions(8, symmetric=True)  # 5 dirs
src, flip_x = resolve_orientation("NW")         # ("NE", True)
plan = topdown_sheet_plan()                     # sheet metadata
```

Asymmetric hair/gear → draw all 8 uniquely (or accept hand-swap on flip).

## Workflow that catches errors

1. Rough all orientations in one scene (comparative measurements)
2. Sequence into a **rotation loop** — jank you miss side-by-side shows up here
3. Lock thickness/length of limbs (1px matters at this size)
4. Idle next (front → sides → angles)
5. Run: finish **front 6-frame** first, then side, up, angles last
6. Arrange directions in a **circle** and sync motion (head bob, shoulder, stride)

`sync_check_bobs(poses_by_dir)` flags divergent peaks across directions.

## Variable bob (not pure sine)

One stride relative to previous frames ≈ **down 1px, down 1px, up 2px**. Up is faster (pass frame, legs under torso). Pure sine looks robotic.

```python
from topdown_anim import topdown_run, topdown_idle

run = topdown_run(f, frames=6, direction="SE")  # variable bob built-in
idle = topdown_idle(f, frames=4, direction="S") # held extremes
```

## Idle timing

Uniform frame duration feels robotic. **Hold extremities** longer than in-betweens (`hold_pattern`).

## Design for animation

- Static-hero detail often becomes noise in motion — **simplify for clarity**
- Layer cape / weapon / boots on separate layers for equipment swaps
- Hair bounce: shift on only 1–2 frames of the loop; keep highlight rhythm consistent across facings

## Delivery

- Spritesheet or `.aseprite` with tags per action; directions as rows or layers
- Document whether W/NW/SW are flips or unique
- Keep foot/shadow pivot stable across frames

See also: [animation-guide.md](animation-guide.md) (side-view fundamentals)

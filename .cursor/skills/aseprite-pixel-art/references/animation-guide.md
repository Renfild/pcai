# Animation Guide (side-view)

Principles adapted from [Slynyrd Pixelblog 8 — Intro to Animation](https://www.slynyrd.com/blog/2018/8/19/pixelblog-8-intro-to-animation).

## Start simple

- Animate a **clear silhouette** with few colors first; detail after motion works
- Tiny sprites limit readable motion; huge sprites are slow to iterate — pick a comfortable size (16–32px tall is common for platformers)

## Keyframes first

Keyframes are the dramatic poses that carry the motion. In-betweens only fill gaps.

| Run role | What it shows |
|---|---|
| **contact / stride** | Limb extended, forward lean, max action |
| **pass** | Limbs close to body, connects both strides |
| **down / recoil** | Optional — often dropped for energy |
| **up / high** | Optional apex — drop when economizing to 4 frames |

**Rule:** if you delete all in-betweens, the remaining keyframes should still read as a run.

### Frame economy (Slynyrd recipe)

| Frames | Keep | Drop | Suggested ms/frame |
|---|---|---|---|
| 8 | full | — | 80 |
| 6 | contact, pass, up | recoil | ~107 |
| 4 | contact + pass | recoil + high | 160 |
| 3 | stride, pass, stride | everything else | ~213 |

`anim_helpers.frame_duration_ms(n)` and `economize_run_frames()` encode this. **Default to 6-frame runs.**

More frames ≠ better. Excessive in-betweens leach energy and look sluggish.

## Idle

Any movement beats a statue. Prefer a **breathing bob**. Hold inhale/exhale frames longer than mid frames (`hold_pattern`, `idle_breath(hold_extremes=True)`).

## Playback speed

Duration per frame changes the feel as much as the drawings. When you cut frames, **lengthen** each remaining frame so cycle energy stays similar.

## Cluster hygiene

Looping animations expose every orphan pixel. Respect clusters on every frame — one stray pixel becomes an eyesore on repeat.

## API

```python
from anim_helpers import (
    run_cycle, idle_breath, anim_tag_plan,
    frame_duration_ms, economize_run_frames, run_keyframe_guide,
)

pose = run_cycle(f, frames=6, variable_bob=True)  # energy-first default
idle = idle_breath(f, frames=6, hold_extremes=True)
plan = anim_tag_plan(["idle", "run", "jump", "land"])  # run=6, scaled ms
keep = economize_run_frames(8, target=6)  # [0,2,3,4,6,7]
```

See also: [topdown-character-guide.md](topdown-character-guide.md), [platformer-guide.md](platformer-guide.md)

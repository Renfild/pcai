# Lighting & Particles Guide

How to use **blend modes** + `fx_helpers.py` so glow/ember/spark layers look correct in previews **and** in Aseprite.

## Blend modes that matter for FX

| Mode | Use for | Notes |
|---|---|---|
| `addition` | Fire glow, magic, neon, laser | Brightens past palette; best default for light |
| `screen` | Soft light, haze, moonlight | Gentler than addition |
| `multiply` | Shadows, time-of-day wash, AO | Darkens; great for whole-scene mood |
| `normal` | Opaque props, most particles with their own alpha | Safe default |

Create FX layers explicitly:

```python
s.add_layer("body")
s.add_layer("glow", blend_mode="addition")
s.add_layer("embers", blend_mode="addition")
s.add_layer("shade", blend_mode="multiply", opacity=140)
```

`composite_frame()` simulates these modes, so PNG/GIF previews match Aseprite.

## Soft glow (torches, eyes, crystals)

```python
from fx_helpers import radial_glow, flicker, apply_glow

intensity = flicker(frame, base=1.0, amount=0.2, seed=3)
core = radial_glow(cx, cy, radius=3, color=(255, 220, 120, int(220 * intensity)), falloff=1.2)
halo = radial_glow(cx, cy, radius=8, color=(255, 140, 40, int(100 * intensity)), falloff=2.5)
apply_glow(s, "glow", frame, core + halo)
```

Tips:
- Two rings (tight core + wide halo) read better than one huge glow
- Keep glow colors warm-on-warm or cool-on-cool; mixed hues turn muddy under addition
- Never put glow on the same layer as solid lineart

## Particles (embers, sparks, dust, wisps)

```python
from fx_helpers import spawn_burst, simulate_particles, stamp_particles, ember_trail

# One-shot burst (hit spark, poof)
sys = spawn_burst(cx, cy, count=14, color=(255, 200, 80, 230),
                  speed=1.4, life=7, cone_deg=80, aim_deg=-90, seed=1)
for f in range(nframes):
    s.stamp(stamp_particles(sys), layer="embers", frame=f)
    simulate_particles(sys)

# Continuous rising embers (torch)
for f, pixels in enumerate(ember_trail(cx, cy - 1, frames=nframes, seed=2)):
    s.stamp(pixels, layer="embers", frame=f)
```

Tips:
- Prefer **few** bright particles over many dim ones
- Fade alpha with life (`stamp_particles` does this by default)
- Aim bursts opposite gravity for fire; with gravity for debris
- Dust: low alpha, `normal` or soft `screen`, near-zero speed

## Animation curves

```python
from fx_helpers import walk_cycle, wave_curve

wc = walk_cycle(frame, frames=8, stride=2, bob=1)
body_y = int(round(wc["body_y"]))   # positive = upward → subtract from y

bob = wave_curve(frame, frames=12, amplitude=1.5, cycles=1)
```

`walk_cycle` body bob **peaks at the passing frames** (mid-stride). Subtract `body_y` from sprite y when drawing.

## Checklist before shipping FX

- [ ] Glow / particles live on their own layers with `addition` or `screen`
- [ ] Preview via `composite_frame` / `preview_gif` shows brightening past base colors
- [ ] Solid art still readable with FX layers hidden
- [ ] Flicker + particles share a stable seed for reproducible builds
- [ ] File saved as `.aseprite` so blend modes survive into the editor

See also: [environments-and-scenes-guide.md](environments-and-scenes-guide.md)

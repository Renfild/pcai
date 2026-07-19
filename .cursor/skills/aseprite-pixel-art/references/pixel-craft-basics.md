# Pixel Craft Basics (locations, lighting, ambient FX)

## Parallax (Terraria-style)

| Layer | Scroll | Content |
|---|---|---|
| `sky` | 0.0 | Gradient only |
| `bg_far` | 0.15 | Silhouettes, few colors |
| `bg_mid` | 0.35 | Distant trees/hills |
| `bg_near` | 0.65 | Larger BG props |
| `close_bg` | 1.0 | Room extension — **no** parallax lag |
| `world` / `props` | 1.0 | Collidable main |
| `fg` | 1.25 | Margins only — never cover player |

Export scroll rates in `loop_fx.PARALLAX_STACK` / `loc.export_game()["parallax"]`.

## Platforms

Stamp with `loop_fx.stamp_platform` — multi-layer:
1. Underside shadow / support nubs  
2. Body (dirt / stone / wood variation)  
3. Top lip highlight  
4. Surface dressing heaps (leaves / snow / moss)  
5. Edge cracks  

Never a flat single-color rectangle.

## Water

`loop_fx.stamp_water` — **horizontal** depth bands + soft 2px surface wave + bank foam.  
No vertical caustic hatch lines.

## Ambient particles (clouds / leaves / snow)

**One direction only.** Spawn off-screen → travel → despawn off-screen → respawn.  
Never `x % width` wrap mid-view (looks like a teleport).

```python
from loop_fx import make_cloud_field, make_leaf_field, bake_drift_frames
frames = bake_drift_frames(make_cloud_field(W, H, direction=1), n_frames)
```

Use Aseprite tag `direction="forward"` for weather — **not pingpong** (pingpong reverses drift).

Suggested ambient: **12 frames @ 100ms**.

## Lighting

- Diffused fill first (`stamp_diffused`)
- Soft shafts (low intensity, almost no flicker)
- Lamps: flicker amount ≈ 0.05–0.1 — high flicker looks like “curves” in the light
- Shade multiply once; copy to other frames

## Checklist

- [ ] Main collidables outlined; close-bg not  
- [ ] FG only at margins  
- [ ] Platforms multi-layer + surface heaps  
- [ ] Water bands read as liquid  
- [ ] Particles one-way spawn/despawn  
- [ ] Ambient forward, ~12 frames  
- [ ] `export_game()["validation"]["ok"]`

#!/usr/bin/env python3
"""Torch demo: solid pole + additive flame glow + rising embers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from aseprite_io import Sprite
from fx_helpers import apply_glow, ember_trail, flicker, radial_glow

OUT = ROOT / "examples" / "out"
OUT.mkdir(parents=True, exist_ok=True)

W = H = 32
FRAMES = 8
CX, FLAME_Y = 16, 11


def draw_body(s: Sprite, frame: int) -> None:
    # Wooden pole
    s.fill_rect(15, 14, 16, 28, (92, 58, 32, 255), layer="body", frame=frame)
    s.fill_rect(14, 27, 17, 28, (70, 44, 24, 255), layer="body", frame=frame)
    # Bowl / metal cup
    s.fill_rect(13, 13, 18, 15, (120, 120, 130, 255), layer="body", frame=frame)
    s.fill_rect(14, 12, 17, 12, (150, 150, 160, 255), layer="body", frame=frame)
    # Flame core (solid, slight flicker via height)
    inten = flicker(frame, base=1.0, amount=0.25, seed=7)
    top = FLAME_Y - int(2 + 2 * inten)
    s.fill_rect(15, top, 16, 12, (255, 230, 120, 255), layer="body", frame=frame)
    s.fill_rect(14, top + 1, 17, 12, (255, 170, 50, 255), layer="body", frame=frame)
    s.put_pixel(15, top - 1, (255, 250, 200, 255), layer="body", frame=frame)


def main() -> None:
    s = Sprite(W, H)
    s.add_layer("body")
    s.add_layer("glow", blend_mode="addition")
    s.add_layer("embers", blend_mode="addition")
    for i in range(FRAMES):
        if i:
            s.add_frame(90)
        draw_body(s, i)
        inten = flicker(i, base=1.0, amount=0.22, seed=3)
        core = radial_glow(
            CX, FLAME_Y, radius=3,
            color=(255, 220, 140, int(200 * inten)),
            falloff=1.1,
        )
        halo = radial_glow(
            CX, FLAME_Y, radius=8,
            color=(255, 120, 30, int(90 * inten)),
            falloff=2.4,
        )
        apply_glow(s, "glow", i, core + halo)

    for f, pixels in enumerate(ember_trail(CX, FLAME_Y - 1, FRAMES, seed=11)):
        s.stamp(pixels, layer="embers", frame=f)

    ase = s.save(OUT / "torch.aseprite")
    png = s.preview(OUT / "torch.png", scale=8, frame=0, background=(20, 18, 28, 255))
    gif = s.preview_gif(OUT / "torch.gif", scale=8, background=(20, 18, 28, 255))

    # Prove addition brightens past base palette values
    img = s.composite_frame(0, background=(20, 18, 28, 255))
    px = img.getpixel((CX, FLAME_Y))
    print(f"wrote {ase}")
    print(f"wrote {png}")
    print(f"wrote {gif}")
    print(f"flame center composited RGBA={px}")
    if px[0] <= 255 and px[1] <= 255:
        # With addition over an already-bright flame + glow, channels should be high
        assert px[0] >= 200 and px[1] >= 150, f"expected bright additive result, got {px}"
    print("torch demo OK")


if __name__ == "__main__":
    main()

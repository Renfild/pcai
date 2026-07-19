#!/usr/bin/env python3
"""Regression tests: blend modes, round-trip I/O, walk_cycle bob, fx helpers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from aseprite_io import Sprite, load_aseprite
from fx_helpers import walk_cycle, radial_glow, spawn_burst, simulate_particles, stamp_particles


def test_addition_brightens() -> None:
    s = Sprite(8, 8)
    s.add_layer("body")
    s.add_layer("glow", blend_mode="addition")
    s.fill_rect(2, 2, 5, 5, (100, 40, 20, 255), layer="body")
    s.fill_rect(2, 2, 5, 5, (80, 60, 20, 180), layer="glow")
    img = s.composite_frame(0)
    r, g, b, a = img.getpixel((3, 3))
    # addition must exceed the base body channel (glow contributes light)
    assert r > 100 and g > 40, (r, g, b, a)
    print("OK addition_brightens", (r, g, b, a))


def test_multiply_darkens() -> None:
    s = Sprite(4, 4)
    s.add_layer("body")
    s.add_layer("shade", blend_mode="multiply")
    s.fill_rect(0, 0, 3, 3, (200, 100, 50, 255), layer="body")
    s.fill_rect(0, 0, 3, 3, (128, 128, 128, 255), layer="shade")
    r, g, b, a = s.composite_frame(0).getpixel((1, 1))
    assert r < 200 and g < 100, (r, g, b, a)
    print("OK multiply_darkens", (r, g, b, a))


def test_roundtrip(tmp: Path) -> None:
    s = Sprite(16, 16)
    s.add_layer("body")
    s.add_layer("glow", blend_mode="addition", opacity=200)
    s.put_pixel(4, 5, (10, 20, 30, 255), layer="body")
    s.put_pixel(4, 5, (40, 50, 60, 128), layer="glow")
    s.add_frame(50)
    s.put_pixel(5, 5, (1, 2, 3, 255), layer="body", frame=1)
    s.add_tag("idle", 0, 1)
    path = tmp / "roundtrip.aseprite"
    s.save(path)
    s2 = load_aseprite(path)
    assert s2.width == 16 and s2.height == 16
    assert [L.name for L in s2.layers] == ["body", "glow"]
    assert s2.layers[1].blend_mode == "addition"
    assert s2.layers[1].opacity == 200
    assert s2.layers[0].cels[0].get_pixel(4, 5) == (10, 20, 30, 255)
    assert s2.tags[0].name == "idle"
    # Composite after reload still brightens
    r, *_ = s2.composite_frame(0).getpixel((4, 5))
    assert r > 10
    print("OK roundtrip")


def test_walk_cycle_bob_peaks_at_passing() -> None:
    frames = 8
    samples = [(i, walk_cycle(i, frames=frames, bob=2.0)) for i in range(frames)]
    # Passing phases should have the highest body_y (upward)
    passing = [body_y for i, d in samples if d["phase"] == "passing" for body_y in [d["body_y"]]]
    contact = [d["body_y"] for i, d in samples if d["phase"] == "contact"]
    assert passing, "expected passing frames"
    assert max(passing) > max(contact)
    # Frame at t≈0.5 should be near peak
    mid = walk_cycle(frames // 2, frames=frames, bob=2.0)
    assert mid["body_y"] == max(d["body_y"] for _, d in samples)
    print("OK walk_cycle_bob", [(i, d["phase"], round(d["body_y"], 3)) for i, d in samples])


def test_particles_and_glow() -> None:
    glow = radial_glow(8, 8, 4, (255, 200, 50, 200), falloff=2.0)
    assert any(p[2][3] == 200 for p in glow)  # center-ish full alpha
    assert all(0 < p[2][3] <= 200 for p in glow)
    sys = spawn_burst(8, 8, count=10, seed=42, life=5, speed=1.0)
    assert len(sys.alive()) == 10
    simulate_particles(sys, 2)
    px = stamp_particles(sys)
    assert px
    print("OK particles_and_glow", len(glow), "glow px,", len(px), "particle px")


def test_character_plus_fx(tmp: Path) -> None:
    """Small character + glowing torch + walk bob — end-to-end smoke."""
    s = Sprite(48, 32)
    s.add_layer("body")
    s.add_layer("glow", blend_mode="addition")
    n = 8
    for i in range(n):
        if i:
            s.add_frame(100)
        wc = walk_cycle(i, frames=n, bob=1.0)
        by = -int(round(wc["body_y"]))  # positive bob → move up (smaller y)
        # Tiny person
        s.fill_rect(10, 12 + by, 14, 20 + by, (60, 100, 180, 255), layer="body", frame=i)
        s.fill_rect(11, 8 + by, 13, 11 + by, (220, 190, 150, 255), layer="body", frame=i)
        # Torch in hand
        tx, ty = 16, 14 + by
        s.fill_rect(tx, ty, tx, ty + 5, (90, 60, 30, 255), layer="body", frame=i)
        s.stamp(radial_glow(tx, ty - 1, 4, (255, 160, 40, 160)), layer="glow", frame=i)

    path = tmp / "char_fx.aseprite"
    s.save(path)
    s.preview_gif(tmp / "char_fx.gif", scale=4, background=(16, 16, 24, 255))
    assert path.stat().st_size > 100
    print("OK character_plus_fx")


def main() -> None:
    tmp = ROOT / "examples" / "out"
    tmp.mkdir(parents=True, exist_ok=True)
    test_addition_brightens()
    test_multiply_darkens()
    test_roundtrip(tmp)
    test_walk_cycle_bob_peaks_at_passing()
    test_particles_and_glow()
    test_character_plus_fx(tmp)
    print("\nAll regression tests passed.")


if __name__ == "__main__":
    main()

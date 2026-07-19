#!/usr/bin/env python3
"""Generate all physics-ready preset stages into pixel-art/<name>/."""

from __future__ import annotations

import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / ".cursor" / "skills" / "aseprite-pixel-art"
sys.path.insert(0, str(SKILL / "scripts"))

from stage_builder import preset_stages, render_stage

ROOT = Path(__file__).resolve().parent


def main() -> None:
    for brief in preset_stages():
        out = ROOT / brief.name.replace("_", "-")
        # keep folder names kebab-case matching name
        folder = {
            "saltspire_coast": "saltspire-coast",
            "gloomroot_cavern": "gloomroot-cavern",
            "ashen_ramparts": "ashen-ramparts",
            "moonfen_marsh": "moonfen-marsh",
        }[brief.name]
        out = ROOT / folder
        print(f"=== {brief.title} ===")
        _, loc, game = render_stage(brief, out)
        v = game["validation"]
        print(f"  ok={v['ok']} platforms={v['platform_count']} hard_gaps={len(v['hard_gaps'])}")
        print(f"  physics jump={game['physics']['jump_height']} gap={game['physics']['jump_gap']}")
        print(f"  spawn={game['spawn']} → {out}")
        if not v["ok"]:
            print("  WARNINGS:", v["warnings"])


if __name__ == "__main__":
    main()

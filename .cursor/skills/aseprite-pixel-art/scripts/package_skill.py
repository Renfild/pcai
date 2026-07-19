#!/usr/bin/env python3
"""Package aseprite-pixel-art into a distributable .skill zip."""

from __future__ import annotations

import fnmatch
import zipfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {"__pycache__", "node_modules", ".git", ".cursor", "dist"}
EXCLUDE_GLOBS = {"*.pyc", ".DS_Store", "*.skill"}


def main() -> None:
    # Nested under .cursor/skills/<name> → zip beside it.
    # Repo-root skill (aseprskill) → zip into ./dist/aseprite-pixel-art.skill
    if SKILL_DIR.parent.name == "skills":
        out_dir = SKILL_DIR.parent
        arc_name = SKILL_DIR.name
    else:
        out_dir = SKILL_DIR / "dist"
        out_dir.mkdir(parents=True, exist_ok=True)
        arc_name = "aseprite-pixel-art"
    out = out_dir / f"{arc_name}.skill"

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in SKILL_DIR.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(SKILL_DIR)
            if any(part in EXCLUDE_DIRS for part in rel.parts):
                continue
            if any(fnmatch.fnmatch(path.name, pat) for pat in EXCLUDE_GLOBS):
                continue
            zf.write(path, f"{arc_name}/{rel.as_posix()}")
            print("Added", f"{arc_name}/{rel.as_posix()}")
    print(f"\nPackaged → {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

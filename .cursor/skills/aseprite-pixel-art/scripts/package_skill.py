#!/usr/bin/env python3
"""Package aseprite-pixel-art into a distributable .skill zip."""

from __future__ import annotations

import fnmatch
import zipfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = SKILL_DIR.parent  # .cursor/skills/
EXCLUDE_DIRS = {"__pycache__", "node_modules"}
EXCLUDE_GLOBS = {"*.pyc", ".DS_Store"}
# Skip generated junk under examples/out except kept demo assets (handled by not deleting them)


def main() -> None:
    out = OUT_DIR / f"{SKILL_DIR.name}.skill"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in SKILL_DIR.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(SKILL_DIR.parent)
            if any(part in EXCLUDE_DIRS for part in rel.parts):
                continue
            if any(fnmatch.fnmatch(path.name, pat) for pat in EXCLUDE_GLOBS):
                continue
            zf.write(path, rel.as_posix())
            print("Added", rel.as_posix())
    print(f"\nPackaged → {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

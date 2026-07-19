# Publish to https://github.com/Renfild/aseprskill

This skill is ready to live in **aseprskill**. The cloud agent could not push
(403 — token only has write access to `Renfild/pcai`).

## Option A — git bundle (keeps history)

```bash
git clone https://github.com/Renfild/aseprskill.git
cd aseprskill
git fetch /path/to/aseprskill-skill-from-guides.bundle cursor/skill-from-guides-c0fa:cursor/skill-from-guides-c0fa
git checkout cursor/skill-from-guides-c0fa
git push -u origin cursor/skill-from-guides-c0fa
gh pr create --base main --head cursor/skill-from-guides-c0fa \
  --title "Add aseprite-pixel-art skill (guides-informed)" \
  --body "See SKILL.md — Pixelblog 8, Maglione level design, Pixelblog 55."
```

Artifact: `aseprskill-skill-from-guides.bundle`

## Option B — tarball onto main

```bash
git clone https://github.com/Renfild/aseprskill.git
cd aseprskill
tar xzf /path/to/aseprskill-branch.tar.gz --strip-components=1
git checkout -b cursor/skill-from-guides-c0fa
git add -A && git commit -m "Add aseprite-pixel-art skill"
git push -u origin cursor/skill-from-guides-c0fa
```

## Option C — grant agent access

Add the Cursor cloud agent / `cursor[bot]` as a collaborator on
`Renfild/aseprskill` with write access, then re-run the move task.

"""Platformer location generation — rooms, platforms, tiles, game export.

Produces a LocationSpec you draw into a Sprite. Includes collision AABB hints,
tilemap export, spawn validation, and jump-reachability checks for game-ready
stages (not just art demos).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

Color = Tuple[int, int, int, int]


# Layer roles (Sandro Maglione — Platformer Level Design Full Guide)
# Foreground: depth props that never hide the player (margins / pass-behind grass)
# Main: collidable + interactive — solid outline, high contrast, less saturation
# Close background: non-interactive, no outline, moves 1:1 with camera (not parallax)
# Parallax: far layers — more saturation, fewer colors, slower scroll
LAYER_ROLES = {
    "foreground": {"scroll": 1.15, "outline": False, "interactive": False, "z": 5},
    "main":       {"scroll": 1.0,  "outline": True,  "interactive": True,  "z": 3},
    "close_bg":   {"scroll": 1.0,  "outline": False, "interactive": False, "z": 2},
    "parallax_near": {"scroll": 0.55, "outline": False, "interactive": False, "z": 1},
    "parallax_far":  {"scroll": 0.2,  "outline": False, "interactive": False, "z": 0},
    "sky":           {"scroll": 0.0,  "outline": False, "interactive": False, "z": -1},
}


def platformer_layer_stack() -> List[Dict]:
    """Recommended Aseprite layer order (bottom → top) for a game-ready stage."""
    return [
        {"name": "sky", "role": "sky", **LAYER_ROLES["sky"]},
        {"name": "far", "role": "parallax_far", **LAYER_ROLES["parallax_far"]},
        {"name": "close_bg", "role": "close_bg", **LAYER_ROLES["close_bg"]},
        {"name": "world", "role": "main", **LAYER_ROLES["main"]},
        {"name": "props", "role": "main", **LAYER_ROLES["main"]},
        {"name": "near", "role": "foreground", **LAYER_ROLES["foreground"]},
        {"name": "shade", "role": "fx", "blend": "multiply"},
        {"name": "beams", "role": "fx", "blend": "screen"},
        {"name": "glow", "role": "fx", "blend": "addition"},
        {"name": "fg_fx", "role": "foreground", **LAYER_ROLES["foreground"]},
    ]


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        return self.x + self.w - 1

    @property
    def y2(self) -> int:
        return self.y + self.h - 1

    def as_aabb(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}

    def snap(self, tile: int) -> "Rect":
        """Snap origin and size to tile grid (size at least 1 tile when possible)."""
        x = (self.x // tile) * tile
        y = (self.y // tile) * tile
        w = max(tile, ((self.w + tile - 1) // tile) * tile) if self.w >= tile // 2 else self.w
        h = self.h if self.h < tile else max(tile, ((self.h + tile - 1) // tile) * tile)
        return Rect(x, y, w, h)


@dataclass
class Prop:
    kind: str  # torch | banner | door | chest | spike | ladder | decor | checkpoint
    x: int
    y: int
    meta: Dict = field(default_factory=dict)


@dataclass
class PlatformerPhysics:
    """Assumptions used to validate / generate reachable layouts."""

    tile: int = 16
    player_w: int = 12
    player_h: int = 16
    # Max jump peak (pixels up from standing feet)
    jump_height: int = 48
    # Max horizontal gap clearable at run+jump
    jump_gap: int = 64
    # Coyote / feel padding when checking gaps
    gap_slack: int = 8


@dataclass
class LocationSpec:
    """Logical layout for a platformer stage / room."""

    name: str
    width: int
    height: int
    tile: int = 16
    theme: str = "castle"  # castle | cave | forest | autumn_forest | dungeon | rooftop
    # Geometry
    solids: List[Rect] = field(default_factory=list)       # collision platforms
    one_way: List[Rect] = field(default_factory=list)      # jump-through
    hazards: List[Rect] = field(default_factory=list)
    climbables: List[Rect] = field(default_factory=list)
    kill_zones: List[Rect] = field(default_factory=list)   # instant death (void/lava)
    checkpoints: List[Tuple[int, int]] = field(default_factory=list)
    # Spawns
    player_spawn: Tuple[int, int] = (32, 64)  # feet position (bottom-center)
    exits: List[Dict] = field(default_factory=list)        # {name,x,y,w,h,target}
    # Decor
    props: List[Prop] = field(default_factory=list)
    windows: List[Tuple[int, int]] = field(default_factory=list)  # light anchors
    lamps: List[Tuple[int, int]] = field(default_factory=list)
    # Parallax hints: list of {name, scroll, color}
    parallax: List[Dict] = field(default_factory=list)
    ground_y: int = 0
    seed: int = 0
    camera: Dict = field(default_factory=dict)  # {x,y,w,h} bounds
    physics: Optional[PlatformerPhysics] = None

    def collision_map(self) -> List[Dict]:
        out = []
        for r in self.solids:
            out.append({"type": "solid", **r.as_aabb()})
        for r in self.one_way:
            out.append({"type": "one_way", **r.as_aabb()})
        for r in self.hazards:
            out.append({"type": "hazard", **r.as_aabb()})
        for r in self.climbables:
            out.append({"type": "climb", **r.as_aabb()})
        for r in self.kill_zones:
            out.append({"type": "kill", **r.as_aabb()})
        return out

    def snap_all(self) -> None:
        """Snap gameplay geometry to tile grid (keeps thin one-ways as-is if short)."""
        t = self.tile
        self.solids = [r.snap(t) if r.h >= t // 2 else Rect((r.x // t) * t, r.y, max(t, (r.w // t) * t), r.h) for r in self.solids]
        self.one_way = [Rect((r.x // t) * t, r.y, max(t, ((r.w + t - 1) // t) * t), r.h) for r in self.one_way]
        self.hazards = [r.snap(t) for r in self.hazards]
        self.climbables = [r.snap(t) for r in self.climbables]
        self.kill_zones = [r.snap(t) for r in self.kill_zones]
        sx, sy = self.player_spawn
        # Feet on tile; keep sub-tile x for feel but prefer tile center
        self.player_spawn = (sx, (sy // t) * t)

    def dedupe_solids(self) -> None:
        seen = set()
        uniq = []
        for r in self.solids:
            key = (r.x, r.y, r.w, r.h)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(r)
        self.solids = uniq

    def export_game(self) -> Dict:
        """Engine-ready JSON: collision, spawn, camera, tile size, tags."""
        phys = self.physics or PlatformerPhysics(tile=self.tile)
        cam = self.camera or {
            "x": 0, "y": 0, "w": self.width, "h": self.height,
        }
        return {
            "name": self.name,
            "theme": self.theme,
            "width": self.width,
            "height": self.height,
            "tile": self.tile,
            "ground_y": self.ground_y,
            "spawn": {
                "x": self.player_spawn[0],
                "y": self.player_spawn[1],
                "feet": True,
                "player_w": phys.player_w,
                "player_h": phys.player_h,
            },
            "checkpoints": [{"x": x, "y": y} for x, y in self.checkpoints],
            "exits": list(self.exits),
            "camera": cam,
            "physics": {
                "jump_height": phys.jump_height,
                "jump_gap": phys.jump_gap,
                "tile": phys.tile,
            },
            "parallax": list(self.parallax),
            "lamps": [{"x": x, "y": y} for x, y in self.lamps],
            "windows": [{"x": x, "y": y} for x, y in self.windows],
            "props": [
                {"kind": p.kind, "x": p.x, "y": p.y, **p.meta} for p in self.props
            ],
            "collision": self.collision_map(),
            "tilemap": build_tilemap(self),
            "validation": validate_layout(self, phys),
        }


# Theme palettes (compact)
THEMES: Dict[str, Dict[str, List[Color]]] = {
    "castle": {
        "stone": [(40, 44, 54, 255), (70, 78, 92, 255), (110, 120, 136, 255), (160, 170, 186, 255)],
        "accent": [(140, 40, 48, 255), (200, 70, 60, 255)],
        "gold": [(120, 88, 32, 255), (210, 170, 70, 255)],
        "bg": [(24, 26, 34, 255), (48, 52, 64, 255)],
    },
    "cave": {
        "stone": [(36, 32, 40, 255), (60, 54, 64, 255), (92, 82, 96, 255), (130, 118, 132, 255)],
        "accent": [(80, 160, 120, 255), (40, 200, 160, 255)],
        "gold": [(180, 140, 60, 255), (220, 190, 90, 255)],
        "bg": [(16, 14, 20, 255), (32, 28, 38, 255)],
    },
    "forest": {
        "stone": [(48, 60, 40, 255), (70, 92, 52, 255), (110, 140, 70, 255), (160, 190, 100, 255)],
        "accent": [(160, 60, 40, 255), (220, 120, 60, 255)],
        "gold": [(200, 170, 70, 255), (240, 210, 100, 255)],
        "bg": [(30, 40, 50, 255), (50, 70, 60, 255)],
        "leaf": [(60, 100, 50, 255), (90, 140, 60, 255), (130, 170, 80, 255)],
        "water": [(20, 40, 50, 255), (30, 70, 80, 255), (50, 110, 120, 255)],
    },
    "autumn_forest": {
        # Dark fantasy autumn — plum bark, rust foliage, violet mist
        "stone": [(42, 28, 36, 255), (72, 44, 48, 255), (110, 70, 52, 255), (150, 100, 70, 255)],
        "accent": [(160, 48, 36, 255), (210, 90, 40, 255), (230, 150, 60, 255)],
        "gold": [(180, 120, 40, 255), (240, 180, 70, 255)],
        "bg": [(18, 14, 28, 255), (36, 28, 48, 255), (48, 40, 58, 255)],
        "leaf": [(140, 40, 36, 255), (190, 70, 40, 255), (220, 130, 50, 255), (180, 90, 30, 255)],
        "moss": [(40, 70, 48, 255), (70, 110, 60, 255)],
        "water": [(20, 28, 48, 255), (36, 50, 80, 255), (60, 90, 120, 255)],
        "cloud_bg": [(140, 120, 170, 60)],
        "cloud_fg": [(30, 22, 40, 75)],
        "haze": [(70, 50, 90, 255)],
    },
    "dungeon": {
        "stone": [(34, 34, 40, 255), (56, 56, 64, 255), (88, 88, 98, 255), (130, 130, 142, 255)],
        "accent": [(120, 30, 140, 255), (180, 60, 200, 255)],
        "gold": [(160, 120, 40, 255), (210, 170, 60, 255)],
        "bg": [(14, 12, 18, 255), (28, 24, 34, 255)],
    },
    "rooftop": {
        "stone": [(50, 48, 58, 255), (80, 76, 90, 255), (120, 114, 130, 255), (170, 164, 180, 255)],
        "accent": [(200, 80, 60, 255), (240, 140, 80, 255)],
        "gold": [(220, 180, 80, 255), (250, 220, 120, 255)],
        "bg": [(40, 50, 80, 255), (70, 90, 130, 255)],
        "cloud_bg": [(160, 170, 200, 55)],
        "cloud_fg": [(50, 55, 70, 70)],
    },
    # Blasphemous / Cvstodia — ash stone, faded gold, penitent crimson (purist pixel)
    "penitent": {
        "stone": [(28, 24, 30, 255), (48, 42, 50, 255), (78, 68, 74, 255), (118, 104, 108, 255), (158, 140, 138, 255)],
        "accent": [(90, 18, 22, 255), (140, 28, 32, 255), (190, 48, 42, 255)],  # blood
        "gold": [(90, 70, 36, 255), (150, 118, 52, 255), (210, 170, 80, 255)],
        "bg": [(12, 10, 14, 255), (28, 22, 28, 255), (42, 34, 40, 255)],
        "wood": [(52, 34, 28, 255), (78, 50, 36, 255)],
        "ash": [(60, 58, 62, 255), (90, 86, 90, 255)],
        "candle": [(255, 210, 120, 255), (255, 150, 60, 255)],
        "glass": [(40, 50, 70, 255), (70, 30, 40, 255), (50, 70, 50, 255), (90, 70, 30, 255)],
        "thorn": [(40, 32, 28, 255), (70, 50, 40, 255)],
        "haze": [(50, 35, 40, 255)],
    },
    "olive_wither": {
        # Where Olive Trees Wither — cold ash, snow, dead olive, muted crimson
        "stone": [(36, 36, 42, 255), (58, 58, 66, 255), (90, 90, 100, 255), (140, 140, 150, 255)],
        "accent": [(100, 30, 35, 255), (150, 50, 45, 255)],
        "gold": [(100, 85, 50, 255), (170, 145, 70, 255)],
        "bg": [(40, 44, 52, 255), (70, 76, 88, 255), (110, 118, 130, 255)],
        "snow": [(200, 205, 215, 255), (230, 232, 238, 255), (255, 255, 255, 255)],
        "olive": [(40, 44, 36, 255), (60, 68, 48, 255), (90, 88, 60, 255)],
        "wood": [(50, 40, 34, 255), (78, 60, 48, 255)],
        "haze": [(120, 130, 145, 255)],
        "cloud_bg": [(180, 185, 200, 70)],
        "cloud_fg": [(60, 65, 75, 60)],
    },
    "cistern": {
        # Desecrated Cistern — wet stone, bilge green, sick gold, black water
        "stone": [(24, 28, 30, 255), (40, 48, 50, 255), (62, 74, 72, 255), (95, 110, 105, 255)],
        "accent": [(70, 90, 50, 255), (110, 140, 70, 255)],  # bilge moss
        "gold": [(80, 70, 30, 255), (140, 120, 50, 255)],
        "bg": [(8, 12, 14, 255), (18, 26, 28, 255), (28, 40, 42, 255)],
        "water": [(8, 16, 18, 255), (16, 32, 36, 255), (30, 55, 58, 255), (50, 80, 78, 255)],
        "rust": [(90, 45, 30, 255), (130, 70, 40, 255)],
        "candle": [(220, 180, 90, 255), (255, 140, 50, 255)],
        "haze": [(30, 45, 48, 255)],
    },
}


def theme_colors(theme: str) -> Dict[str, List[Color]]:
    return THEMES.get(theme, THEMES["castle"])


# ---------------------------------------------------------------------------
# Game-ready helpers
# ---------------------------------------------------------------------------

def build_tilemap(loc: LocationSpec) -> Dict:
    """Coarse tile grid for engines: 0 empty, 1 solid, 2 one_way, 3 hazard, 4 climb, 5 kill."""
    t = loc.tile
    cols = loc.width // t
    rows = loc.height // t
    grid = [[0 for _ in range(cols)] for _ in range(rows)]

    def paint(rects: Sequence[Rect], code: int, full: bool = True) -> None:
        for r in rects:
            c0 = max(0, r.x // t)
            r0 = max(0, r.y // t)
            c1 = min(cols, (r.x + r.w + t - 1) // t)
            r1 = min(rows, (r.y + r.h + t - 1) // t) if full else min(rows, r0 + 1)
            for ry in range(r0, r1):
                for cx in range(c0, c1):
                    if grid[ry][cx] == 0 or code in (3, 5):
                        grid[ry][cx] = code

    paint(loc.solids, 1, full=True)
    paint(loc.one_way, 2, full=False)  # one-way = top row only
    paint(loc.hazards, 3, full=True)
    paint(loc.climbables, 4, full=True)
    paint(loc.kill_zones, 5, full=True)
    return {
        "tile": t,
        "cols": cols,
        "rows": rows,
        "codes": {"empty": 0, "solid": 1, "one_way": 2, "hazard": 3, "climb": 4, "kill": 5},
        "grid": grid,
    }


def _platform_tops(loc: LocationSpec) -> List[Tuple[int, int, int]]:
    """List of (x, y, w) standable tops from solids + one_ways (not walls/ceiling)."""
    tops = []
    for r in loc.solids + loc.one_way:
        if r.h >= loc.height - loc.tile:  # full-height wall
            continue
        if r.y <= loc.tile and r.h <= loc.tile and r.w >= loc.width - loc.tile * 2:
            continue  # ceiling
        if r.w < loc.tile // 2:
            continue
        tops.append((r.x, r.y, r.w))
    return tops


def validate_layout(loc: LocationSpec, phys: Optional[PlatformerPhysics] = None) -> Dict:
    """Check spawn clearance and rough jump reachability. Returns {ok, warnings, gaps}."""
    phys = phys or loc.physics or PlatformerPhysics(tile=loc.tile)
    warnings: List[str] = []
    sx, sy = loc.player_spawn
    # Spawn must sit on or just above a platform
    tops = _platform_tops(loc)
    on_ground = False
    for px, py, pw in tops:
        if px <= sx <= px + pw and abs(sy - py) <= 2:
            on_ground = True
            break
        if px <= sx <= px + pw and py - phys.player_h <= sy <= py:
            on_ground = True
            break
    if not on_ground:
        warnings.append(f"spawn ({sx},{sy}) may not rest on a platform top")

    # Body clearance above spawn
    for r in loc.solids:
        if r.x <= sx <= r.x2 and r.y < sy and r.y2 > sy - phys.player_h:
            if r.y > loc.tile:  # ignore ceiling band
                warnings.append("spawn body overlaps a solid")
                break

    # Gap analysis between sorted tops by x
    sorted_tops = sorted(tops, key=lambda t: (t[0], t[1]))
    hard_gaps = []
    for i in range(len(sorted_tops) - 1):
        ax, ay, aw = sorted_tops[i]
        bx, by, bw = sorted_tops[i + 1]
        gap = bx - (ax + aw)
        rise = ay - by  # positive = next is higher
        if gap <= 0:
            continue
        max_gap = phys.jump_gap + phys.gap_slack
        max_rise = phys.jump_height
        if gap > max_gap or rise > max_rise:
            hard_gaps.append({"from": [ax, ay], "to": [bx, by], "gap": gap, "rise": rise})
            warnings.append(f"hard jump gap={gap}px rise={rise}px near x={ax}")

    return {
        "ok": len(warnings) == 0,
        "warnings": warnings,
        "hard_gaps": hard_gaps,
        "platform_count": len(tops),
    }


def ensure_game_ready(loc: LocationSpec, phys: Optional[PlatformerPhysics] = None) -> LocationSpec:
    """Snap, dedupe, set camera/physics, place default checkpoint, validate spawn."""
    phys = phys or PlatformerPhysics(tile=loc.tile)
    loc.physics = phys
    loc.snap_all()
    loc.dedupe_solids()
    loc.camera = loc.camera or {"x": 0, "y": 0, "w": loc.width, "h": loc.height}
    if not loc.checkpoints:
        loc.checkpoints.append(tuple(loc.player_spawn))  # type: ignore
    # Ensure kill zone under hazards that are pits
    for h in loc.hazards:
        if h.y >= loc.ground_y - loc.tile and h.h >= loc.tile:
            # pit floor kill already covered by hazard; add void below if open
            pass
    # Nudge spawn onto nearest platform top if floating
    tops = _platform_tops(loc)
    sx, sy = loc.player_spawn
    best = None
    best_d = 1e9
    for px, py, pw in tops:
        if px - 4 <= sx <= px + pw + 4:
            d = abs(sy - py)
            if d < best_d:
                best_d = d
                best = (max(px + loc.tile // 2, min(sx, px + pw - loc.tile // 2)), py)
    if best and best_d > 2:
        loc.player_spawn = best  # type: ignore
    if not loc.parallax:
        loc.parallax = [
            {"name": "sky", "role": "sky", "scroll": 0.0, "z": -1},
            {"name": "far", "role": "parallax_far", "scroll": 0.2, "z": 0},
            {"name": "close_bg", "role": "close_bg", "scroll": 1.0, "z": 2},
            {"name": "world", "role": "main", "scroll": 1.0, "z": 3},
            {"name": "near", "role": "foreground", "scroll": 1.15, "z": 5},
        ]
    return loc


def make_platformer_room(
    name: str = "stage",
    width: int = 320,
    height: int = 176,
    tile: int = 16,
    theme: str = "castle",
    seed: int = 1,
    platforms: int = 5,
    style: str = "linear",  # linear | ascent | arena | pit
    game_ready: bool = True,
    physics: Optional[PlatformerPhysics] = None,
) -> LocationSpec:
    """Generate a playable side-view room layout."""
    rng = random.Random(seed)
    phys = physics or PlatformerPhysics(tile=tile)
    ground_y = height - tile * 2
    loc = LocationSpec(
        name=name, width=width, height=height, tile=tile,
        theme=theme, ground_y=ground_y, seed=seed,
        player_spawn=(tile * 2 + tile // 2, ground_y),
        physics=phys,
    )

    # Floor + ceiling bounds
    loc.solids.append(Rect(0, ground_y, width, height - ground_y))
    loc.solids.append(Rect(0, 0, width, tile))  # ceiling strip
    loc.solids.append(Rect(0, 0, tile, height))  # left wall
    loc.solids.append(Rect(width - tile, 0, tile, height))  # right wall

    loc.parallax = [
        {"name": "sky", "role": "sky", "scroll": 0.0, "z": -1},
        {"name": "far", "role": "parallax_far", "scroll": 0.2, "z": 0},
        {"name": "close_bg", "role": "close_bg", "scroll": 1.0, "z": 2},
        {"name": "world", "role": "main", "scroll": 1.0, "z": 3},
        {"name": "near", "role": "foreground", "scroll": 1.15, "z": 5},
    ]

    if style == "linear":
        _gen_linear(loc, rng, platforms, phys)
    elif style == "ascent":
        _gen_ascent(loc, rng, platforms, phys)
    elif style == "arena":
        _gen_arena(loc, rng)
    elif style == "pit":
        _gen_pit(loc, rng, platforms, phys)
    else:
        _gen_linear(loc, rng, platforms, phys)

    _scatter_props(loc, rng)
    if game_ready:
        ensure_game_ready(loc, phys)
    return loc


def _gen_linear(loc: LocationSpec, rng: random.Random, n: int, phys: PlatformerPhysics) -> None:
    t = loc.tile
    gy = loc.ground_y
    x = t * 3
    max_gap = max(t * 2, min(phys.jump_gap - phys.gap_slack, t * 3))
    max_rise = min(phys.jump_height - t, t * 3)
    loc.windows.extend([(loc.width // 3, t * 3), (2 * loc.width // 3, t * 3)])
    prev_y = gy
    for i in range(n):
        w = rng.randint(3, 6) * t
        gap = rng.randint(t * 2, max_gap)
        rise = rng.randint(t, max_rise)
        y = prev_y - rise
        y = max(t * 3, min(gy - t, y))
        # Snap
        x = (x // t) * t
        y = (y // t) * t
        rect = Rect(x, y, w, t)
        if i % 2 == 0:
            loc.solids.append(rect)
        else:
            loc.one_way.append(Rect(x, y, w, max(4, t // 2)))
        if rng.random() < 0.55:
            loc.lamps.append((x + w // 2, y - t // 2))
        prev_y = y
        x += w + gap
        if x > loc.width - t * 4:
            break
    loc.exits.append({
        "name": "right", "x": loc.width - t * 2, "y": gy - t * 2,
        "w": t, "h": t * 2, "target": "next",
    })


def _gen_ascent(loc: LocationSpec, rng: random.Random, n: int, phys: PlatformerPhysics) -> None:
    t = loc.tile
    gy = loc.ground_y
    x = t * 2
    y = gy - t * 2
    max_step_x = max(t * 2, min(phys.jump_gap - t, t * 3))
    max_step_y = min(phys.jump_height - t, t * 2)
    for i in range(n):
        w = rng.randint(2, 4) * t
        loc.solids.append(Rect(x, y, w, t))
        if rng.random() < 0.5:
            loc.lamps.append((x + w // 2, y - 6))
        x += rng.randint(t * 2, max_step_x)
        y -= rng.randint(t, max_step_y)
        if x > loc.width - t * 3:
            x = t * 2 + (i % 3) * t
        if y < t * 3:
            break
    loc.exits.append({
        "name": "top", "x": loc.width // 2, "y": t, "w": t * 2, "h": t, "target": "above",
    })


def _gen_arena(loc: LocationSpec, rng: random.Random) -> None:
    t = loc.tile
    gy = loc.ground_y
    loc.one_way.append(Rect(t * 3, gy - t * 3, t * 3, t // 2))
    loc.one_way.append(Rect(loc.width - t * 6, gy - t * 3, t * 3, t // 2))
    loc.solids.append(Rect(loc.width // 2 - t * 2, gy - t * 5, t * 4, t))
    loc.lamps.append((loc.width // 2, gy - t * 6))
    loc.windows.append((loc.width // 2, t * 3))


def _gen_pit(loc: LocationSpec, rng: random.Random, n: int, phys: PlatformerPhysics) -> None:
    t = loc.tile
    gy = loc.ground_y
    pit_x = loc.width // 2 - t * 2
    pit_w = t * 4
    # Remove full floor; rebuild sides
    loc.solids = [r for r in loc.solids if not (r.y >= gy and r.x == 0 and r.w == loc.width)]
    loc.solids.append(Rect(t, gy, pit_x - t, loc.height - gy))
    loc.solids.append(Rect(pit_x + pit_w, gy, loc.width - (pit_x + pit_w) - t, loc.height - gy))
    loc.hazards.append(Rect(pit_x, gy, pit_w, loc.height - gy))
    loc.kill_zones.append(Rect(pit_x, loc.height - t, pit_w, t))
    # Stepping stones — gaps within jump range
    step_w = t * 2
    gap = min(phys.jump_gap - phys.gap_slack, t * 2)
    x = pit_x - t
    for i in range(max(2, n // 2)):
        y = gy - t * (2 + i)
        loc.one_way.append(Rect(x, y, step_w, max(4, t // 2)))
        x += step_w + gap
        if x > pit_x + pit_w:
            break


def _scatter_props(loc: LocationSpec, rng: random.Random) -> None:
    t = loc.tile
    gy = loc.ground_y
    for x in range(t * 2, loc.width - t * 2, t * 5):
        if rng.random() < 0.55:
            loc.props.append(Prop("torch", x, gy - t * 3))
            loc.lamps.append((x, gy - t * 3 - 4))
    if loc.theme in ("castle", "dungeon"):
        for x in (t * 4, loc.width // 2, loc.width - t * 5):
            loc.props.append(Prop("banner", x, t * 2, {"color": "accent"}))
    for ex in loc.exits:
        loc.props.append(Prop("door", ex["x"], ex["y"], {"exit": ex["name"]}))
    if loc.solids:
        candidates = [r for r in loc.solids if r.y < gy and r.w >= t * 2 and r.h <= t * 2]
        if candidates:
            plat = rng.choice(candidates)
            loc.props.append(Prop("chest", plat.x + plat.w // 2, plat.y, {}))


# ---------------------------------------------------------------------------
# Drawing helpers (stamp LocationSpec into Sprite)
# ---------------------------------------------------------------------------

def draw_location_base(sprite, loc: LocationSpec, layer: str = "world") -> None:
    """Paint solids / one-way / bg from a LocationSpec onto sprite."""
    pal = theme_colors(loc.theme)
    stone = pal["stone"]
    bg = pal["bg"]
    gold = pal["gold"]

    # Sky gradient
    for y in range(loc.height):
        t = y / max(1, loc.height - 1)
        c = (
            int(bg[0][0] + (bg[min(1, len(bg) - 1)][0] - bg[0][0]) * t),
            int(bg[0][1] + (bg[min(1, len(bg) - 1)][1] - bg[0][1]) * t),
            int(bg[0][2] + (bg[min(1, len(bg) - 1)][2] - bg[0][2]) * t),
            255,
        )
        for x in range(loc.width):
            sprite.put_pixel(x, y, c, layer=layer, frame=0)

    # Back wall brick field (between ceiling and ground)
    wall_top = loc.tile
    wall_bot = loc.ground_y
    for y in range(wall_top, wall_bot):
        for x in range(loc.tile, loc.width - loc.tile):
            row = (y - wall_top) // 4
            col = (x + (row % 2) * 4) // 8
            base = stone[1] if (row + col) % 2 == 0 else stone[0]
            sprite.put_pixel(x, y, base, layer=layer, frame=0)
        if (y - wall_top) % 4 == 0:
            for x in range(loc.tile, loc.width - loc.tile):
                sprite.put_pixel(x, y, stone[0], layer=layer, frame=0)

    # Windows as lit insets
    for wx, wy in loc.windows:
        for dy in range(-10, 12):
            for dx in range(-6, 7):
                if dy < -4:
                    if dx * dx + (dy + 4) * (dy + 4) > 36:
                        continue
                sprite.put_pixel(wx + dx, wy + dy, stone[0], layer=layer, frame=0)
                if abs(dx) < 5 and -3 <= dy <= 10:
                    sprite.put_pixel(wx + dx, wy + dy, (60, 90, 130, 255), layer=layer, frame=0)
        sprite.put_pixel(wx, wy, gold[1], layer=layer, frame=0)

    def draw_rect(r: Rect, fill: Color, edge: Color, outline: bool = True) -> None:
        """Main-layer solids get a hard top edge (Maglione: clear collidable read)."""
        for y in range(r.y, r.y + r.h):
            for x in range(r.x, r.x + r.w):
                # Inner fill darker / less detailed deeper in the block
                depth = (y - r.y) / max(1, r.h)
                c = fill if depth < 0.35 else (
                    fill[0] - 12, fill[1] - 12, fill[2] - 12, fill[3]
                )
                c = (max(0, c[0]), max(0, c[1]), max(0, c[2]), c[3])
                sprite.put_pixel(x, y, c, layer=layer, frame=0)
        if outline:
            for x in range(r.x, r.x + r.w):
                sprite.put_pixel(x, r.y, edge, layer=layer, frame=0)
                if r.h > 2:
                    sprite.put_pixel(x, r.y + 1, stone[2], layer=layer, frame=0)
            for y in range(r.y, r.y + r.h):
                sprite.put_pixel(r.x, y, stone[0], layer=layer, frame=0)
                sprite.put_pixel(r.x2, y, stone[0], layer=layer, frame=0)

    for r in loc.solids:
        draw_rect(r, stone[1], stone[3], outline=True)
        for x in range(r.x, r.x + r.w, loc.tile):
            for y in range(r.y, r.y + r.h):
                sprite.put_pixel(x, y, stone[0], layer=layer, frame=0)
            if r.h >= loc.tile:
                for xx in range(x, min(x + loc.tile, r.x + r.w)):
                    sprite.put_pixel(xx, r.y + loc.tile - 1, stone[0], layer=layer, frame=0)

    for r in loc.one_way:
        draw_rect(r, stone[2], stone[3], outline=True)
        for x in range(r.x, r.x + r.w, 3):
            sprite.put_pixel(x, r.y - 1, stone[3], layer=layer, frame=0)

    for r in loc.hazards:
        for y in range(r.y, min(r.y + r.h, loc.height)):
            for x in range(r.x, r.x + r.w):
                if (x + y) % 2 == 0:
                    sprite.put_pixel(x, y, (20, 16, 24, 255), layer=layer, frame=0)


def draw_location_props(sprite, loc: LocationSpec, layer: str = "props") -> None:
    pal = theme_colors(loc.theme)
    accent = pal["accent"]
    gold = pal["gold"]
    for p in loc.props:
        if p.kind == "torch":
            sprite.fill_rect(p.x, p.y, p.x + 1, p.y + 4, (60, 40, 28, 255), layer=layer)
            sprite.put_pixel(p.x, p.y - 1, gold[1], layer=layer)
            sprite.put_pixel(p.x, p.y - 2, (255, 200, 100, 255), layer=layer)
        elif p.kind == "banner":
            sprite.fill_rect(p.x - 3, p.y, p.x + 3, p.y + 12, accent[0], layer=layer)
            sprite.fill_rect(p.x - 2, p.y + 1, p.x + 2, p.y + 8, accent[1], layer=layer)
            sprite.fill_rect(p.x - 4, p.y, p.x + 4, p.y, gold[1], layer=layer)
        elif p.kind == "door":
            sprite.fill_rect(p.x, p.y, p.x + loc.tile - 1, p.y + loc.tile * 2 - 1, (70, 48, 32, 255), layer=layer)
            sprite.put_pixel(p.x + loc.tile - 3, p.y + loc.tile, gold[0], layer=layer)
        elif p.kind == "chest":
            sprite.fill_rect(p.x - 4, p.y - 3, p.x + 4, p.y, gold[0], layer=layer)
            sprite.fill_rect(p.x - 4, p.y - 6, p.x + 4, p.y - 3, gold[1], layer=layer)


def build_platformer_stage(
    sprite_cls,
    loc: Optional[LocationSpec] = None,
    **loc_kwargs,
):
    """Convenience: LocationSpec → Sprite with Maglione-style layer stack."""
    if loc is None:
        loc = make_platformer_room(**loc_kwargs)
    s = sprite_cls(loc.width, loc.height)
    s.add_layer("sky")
    s.add_layer("far")
    s.add_layer("close_bg")
    s.add_layer("world")
    s.add_layer("props")
    s.add_layer("near")  # foreground — never obscure player silhouette
    s.add_layer("shade", blend_mode="multiply", opacity=100)
    s.add_layer("beams", blend_mode="screen")
    s.add_layer("glow", blend_mode="addition")
    draw_location_base(s, loc, "world")
    draw_location_props(s, loc, "props")
    return s, loc

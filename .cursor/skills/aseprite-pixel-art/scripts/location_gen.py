"""Platformer location generation — rooms, platforms, tiles, parallax.

Produces a LocationSpec you draw into a Sprite. Includes collision AABB hints
for engine export (not drawn — metadata only).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

Color = Tuple[int, int, int, int]


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


@dataclass
class Prop:
    kind: str  # torch | banner | door | chest | spike | ladder | decor
    x: int
    y: int
    meta: Dict = field(default_factory=dict)


@dataclass
class LocationSpec:
    """Logical layout for a platformer stage / room."""

    name: str
    width: int
    height: int
    tile: int = 16
    theme: str = "castle"  # castle | cave | forest | dungeon | rooftop
    # Geometry
    solids: List[Rect] = field(default_factory=list)       # collision platforms
    one_way: List[Rect] = field(default_factory=list)      # jump-through
    hazards: List[Rect] = field(default_factory=list)
    climbables: List[Rect] = field(default_factory=list)
    # Spawns
    player_spawn: Tuple[int, int] = (32, 64)
    exits: List[Dict] = field(default_factory=list)        # {name,x,y,w,h,target}
    # Decor
    props: List[Prop] = field(default_factory=list)
    windows: List[Tuple[int, int]] = field(default_factory=list)  # light anchors
    lamps: List[Tuple[int, int]] = field(default_factory=list)
    # Parallax hints: list of {name, scroll, color}
    parallax: List[Dict] = field(default_factory=list)
    ground_y: int = 0
    seed: int = 0

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
        return out


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
    },
}


def theme_colors(theme: str) -> Dict[str, List[Color]]:
    return THEMES.get(theme, THEMES["castle"])


def make_platformer_room(
    name: str = "stage",
    width: int = 320,
    height: int = 176,
    tile: int = 16,
    theme: str = "castle",
    seed: int = 1,
    platforms: int = 5,
    style: str = "linear",  # linear | ascent | arena | pit
) -> LocationSpec:
    """Generate a playable side-view room layout."""
    rng = random.Random(seed)
    ground_y = height - tile * 2
    loc = LocationSpec(
        name=name, width=width, height=height, tile=tile,
        theme=theme, ground_y=ground_y, seed=seed,
        player_spawn=(tile * 2, ground_y - tile * 2),
    )

    # Floor + ceiling bounds
    loc.solids.append(Rect(0, ground_y, width, height - ground_y))
    loc.solids.append(Rect(0, 0, width, tile))  # ceiling strip
    loc.solids.append(Rect(0, 0, tile, height))  # left wall
    loc.solids.append(Rect(width - tile, 0, tile, height))  # right wall

    # Parallax suggestions
    loc.parallax = [
        {"name": "sky", "scroll": 0.0, "z": 0},
        {"name": "far", "scroll": 0.25, "z": 1},
        {"name": "mid", "scroll": 0.5, "z": 2},
        {"name": "near", "scroll": 1.0, "z": 3},
    ]

    if style == "linear":
        _gen_linear(loc, rng, platforms)
    elif style == "ascent":
        _gen_ascent(loc, rng, platforms)
    elif style == "arena":
        _gen_arena(loc, rng)
    elif style == "pit":
        _gen_pit(loc, rng, platforms)
    else:
        _gen_linear(loc, rng, platforms)

    # Props + lights from theme
    _scatter_props(loc, rng)
    return loc


def _gen_linear(loc: LocationSpec, rng: random.Random, n: int) -> None:
    t = loc.tile
    gy = loc.ground_y
    x = t * 3
    # Always place a couple of high windows for shafts
    loc.windows.extend([(loc.width // 3, t * 3), (2 * loc.width // 3, t * 3)])
    for i in range(n):
        w = rng.randint(3, 6) * t
        gap = rng.randint(2, 4) * t
        y = gy - rng.randint(2, 5) * t
        rect = Rect(x, y, w, t)
        if i % 2 == 0:
            loc.solids.append(rect)
        else:
            loc.one_way.append(rect)
        if rng.random() < 0.55:
            loc.lamps.append((x + w // 2, y - t // 2))
        x += w + gap
        if x > loc.width - t * 4:
            break
    loc.exits.append({"name": "right", "x": loc.width - t * 2, "y": gy - t * 2, "w": t, "h": t * 2, "target": "next"})


def _gen_ascent(loc: LocationSpec, rng: random.Random, n: int) -> None:
    t = loc.tile
    gy = loc.ground_y
    x = t * 2
    y = gy - t * 2
    for i in range(n):
        w = rng.randint(2, 4) * t
        loc.solids.append(Rect(x, y, w, t))
        if rng.random() < 0.5:
            loc.lamps.append((x + w // 2, y - 6))
        x += rng.randint(2, 4) * t
        y -= rng.randint(2, 3) * t
        if x > loc.width - t * 3:
            x = t * 2 + (i % 3) * t
        if y < t * 3:
            break
    loc.exits.append({"name": "top", "x": loc.width // 2, "y": t, "w": t * 2, "h": t, "target": "above"})


def _gen_arena(loc: LocationSpec, rng: random.Random) -> None:
    t = loc.tile
    gy = loc.ground_y
    # Side platforms
    loc.one_way.append(Rect(t * 3, gy - t * 3, t * 3, t))
    loc.one_way.append(Rect(loc.width - t * 6, gy - t * 3, t * 3, t))
    loc.solids.append(Rect(loc.width // 2 - t * 2, gy - t * 5, t * 4, t))
    loc.lamps.append((loc.width // 2, gy - t * 6))
    loc.windows.append((loc.width // 2, t * 3))


def _gen_pit(loc: LocationSpec, rng: random.Random, n: int) -> None:
    t = loc.tile
    gy = loc.ground_y
    # Gap in floor — mark hazard in the pit
    pit_x = loc.width // 2 - t * 2
    # Remove center floor by adding hazard over it conceptually
    loc.hazards.append(Rect(pit_x, gy, t * 4, loc.height - gy))
    # Floating platforms over pit
    for i in range(max(2, n // 2)):
        loc.one_way.append(Rect(pit_x - t + i * t * 2, gy - t * (2 + i), t * 2, t))
    loc.solids.append(Rect(t, gy, pit_x - t, loc.height - gy))
    loc.solids.append(Rect(pit_x + t * 4, gy, loc.width - (pit_x + t * 4) - t, loc.height - gy))


def _scatter_props(loc: LocationSpec, rng: random.Random) -> None:
    t = loc.tile
    gy = loc.ground_y
    # Torches along walls
    for x in range(t * 2, loc.width - t * 2, t * 5):
        if rng.random() < 0.55:
            loc.props.append(Prop("torch", x, gy - t * 3))
            loc.lamps.append((x, gy - t * 3 - 4))
    # Banners
    if loc.theme in ("castle", "dungeon"):
        for x in (t * 4, loc.width // 2, loc.width - t * 5):
            loc.props.append(Prop("banner", x, t * 2, {"color": "accent"}))
    # Door at exit
    for ex in loc.exits:
        loc.props.append(Prop("door", ex["x"], ex["y"], {"exit": ex["name"]}))
    # Occasional chest on a solid
    if loc.solids:
        plat = rng.choice([r for r in loc.solids if r.y < gy] or loc.solids)
        loc.props.append(Prop("chest", plat.x + plat.w // 2, plat.y - t, {}))


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
            int(bg[0][0] + (bg[1][0] - bg[0][0]) * t),
            int(bg[0][1] + (bg[1][1] - bg[0][1]) * t),
            int(bg[0][2] + (bg[1][2] - bg[0][2]) * t),
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
                    # arch
                    if dx * dx + (dy + 4) * (dy + 4) > 36:
                        continue
                sprite.put_pixel(wx + dx, wy + dy, stone[0], layer=layer, frame=0)
                if abs(dx) < 5 and -3 <= dy <= 10:
                    sprite.put_pixel(wx + dx, wy + dy, (60, 90, 130, 255), layer=layer, frame=0)
        sprite.put_pixel(wx, wy, gold[1], layer=layer, frame=0)

    def draw_rect(r: Rect, fill: Color, edge: Color) -> None:
        for y in range(r.y, r.y + r.h):
            for x in range(r.x, r.x + r.w):
                sprite.put_pixel(x, y, fill, layer=layer, frame=0)
        for x in range(r.x, r.x + r.w):
            sprite.put_pixel(x, r.y, edge, layer=layer, frame=0)
            if r.h > 2:
                sprite.put_pixel(x, r.y + 1, stone[2], layer=layer, frame=0)

    for r in loc.solids:
        draw_rect(r, stone[1], stone[3])
        for x in range(r.x, r.x + r.w, loc.tile):
            for y in range(r.y, r.y + r.h):
                sprite.put_pixel(x, y, stone[0], layer=layer, frame=0)
            # mortar row
            if r.h >= loc.tile:
                for xx in range(x, min(x + loc.tile, r.x + r.w)):
                    sprite.put_pixel(xx, r.y + loc.tile - 1, stone[0], layer=layer, frame=0)

    for r in loc.one_way:
        draw_rect(r, stone[2], stone[3])
        # grass/edge nubs for readability
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
    """Convenience: LocationSpec → Sprite with world/props/shade/beams/glow layers."""
    if loc is None:
        loc = make_platformer_room(**loc_kwargs)
    s = sprite_cls(loc.width, loc.height)
    s.add_layer("world")
    s.add_layer("props")
    s.add_layer("shade", blend_mode="multiply", opacity=100)
    s.add_layer("beams", blend_mode="screen")
    s.add_layer("glow", blend_mode="addition")
    draw_location_base(s, loc, "world")
    draw_location_props(s, loc, "props")
    return s, loc

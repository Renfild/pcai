"""Pure-Python Aseprite (.aseprite) reader/writer with blend-aware compositing.

Creates and previews multi-layer sprites without needing the Aseprite app.
Layer blend modes are stored in the file AND simulated in composite_frame()
so PNG/GIF previews match what you see when opening the file in Aseprite.
"""

from __future__ import annotations

import math
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Union

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise ImportError("Pillow is required: pip install pillow") from exc

Color = Tuple[int, int, int, int]  # RGBA 0-255
BlendModeName = str

BLEND_MODES: dict[str, int] = {
    "normal": 0,
    "multiply": 1,
    "screen": 2,
    "overlay": 3,
    "darken": 4,
    "lighten": 5,
    "color_dodge": 6,
    "color_burn": 7,
    "hard_light": 8,
    "soft_light": 9,
    "difference": 10,
    "exclusion": 11,
    "hue": 12,
    "saturation": 13,
    "color": 14,
    "luminosity": 15,
    "addition": 16,
    "add": 16,  # alias
    "subtract": 17,
    "divide": 18,
}

BLEND_MODE_IDS: dict[int, str] = {v: k for k, v in BLEND_MODES.items() if k != "add"}


def _clamp_byte(v: float) -> int:
    return max(0, min(255, int(round(v))))


def _ase_string(s: str) -> bytes:
    b = s.encode("utf-8")
    return struct.pack("<H", len(b)) + b


def _read_string(data: bytes, offset: int) -> Tuple[str, int]:
    (length,) = struct.unpack_from("<H", data, offset)
    offset += 2
    text = data[offset : offset + length].decode("utf-8", errors="replace")
    return text, offset + length


# ---------------------------------------------------------------------------
# Blend math (src over dst with Aseprite-style modes, premultiplied by opacity)
# ---------------------------------------------------------------------------

def _blend_channel(mode: str, cb: float, cs: float) -> float:
    """Channel blend (0..1). cb=backdrop, cs=source."""
    if mode == "multiply":
        return cb * cs
    if mode == "screen":
        return 1.0 - (1.0 - cb) * (1.0 - cs)
    if mode in ("addition", "add"):
        return min(1.0, cb + cs)
    if mode == "subtract":
        return max(0.0, cb - cs)
    if mode == "divide":
        return 1.0 if cs == 0 else min(1.0, cb / cs)
    if mode == "darken":
        return min(cb, cs)
    if mode == "lighten":
        return max(cb, cs)
    if mode == "difference":
        return abs(cb - cs)
    if mode == "exclusion":
        return cb + cs - 2.0 * cb * cs
    if mode == "overlay":
        return (2 * cb * cs) if cb < 0.5 else (1.0 - 2.0 * (1.0 - cb) * (1.0 - cs))
    if mode == "hard_light":
        return (2 * cb * cs) if cs < 0.5 else (1.0 - 2.0 * (1.0 - cb) * (1.0 - cs))
    if mode == "soft_light":
        if cs <= 0.5:
            return cb - (1.0 - 2.0 * cs) * cb * (1.0 - cb)
        d = math.sqrt(cb) if cb > 0.25 else ((16 * cb - 12) * cb + 4) * cb
        return cb + (2.0 * cs - 1.0) * (d - cb)
    if mode == "color_dodge":
        if cs >= 1.0:
            return 1.0
        return min(1.0, cb / (1.0 - cs))
    if mode == "color_burn":
        if cs <= 0.0:
            return 0.0
        return 1.0 - min(1.0, (1.0 - cb) / cs)
    # normal / unsupported HSL modes fall through to source
    return cs


def _compose_pixel(dst: Color, src: Color, mode: str, opacity: int) -> Color:
    """Compose one src pixel over dst with blend mode + layer/cel opacity (0-255)."""
    sr, sg, sb, sa = src
    dr, dg, db, da = dst
    if sa == 0 or opacity == 0:
        return dst

    sa_f = (sa / 255.0) * (opacity / 255.0)
    da_f = da / 255.0

    if mode in ("normal", "hue", "saturation", "color", "luminosity") or mode not in BLEND_MODES:
        # Standard src-over
        out_a = sa_f + da_f * (1.0 - sa_f)
        if out_a <= 0:
            return (0, 0, 0, 0)
        out_r = (sr * sa_f + dr * da_f * (1.0 - sa_f)) / out_a
        out_g = (sg * sa_f + dg * da_f * (1.0 - sa_f)) / out_a
        out_b = (sb * sa_f + db * da_f * (1.0 - sa_f)) / out_a
        return (_clamp_byte(out_r), _clamp_byte(out_g), _clamp_byte(out_b), _clamp_byte(out_a * 255))

    # Non-normal: blend RGB, then src-over with result
    if da_f <= 0:
        # No backdrop — just place source (still respect opacity)
        return (_clamp_byte(sr), _clamp_byte(sg), _clamp_byte(sb), _clamp_byte(sa_f * 255))

    br = _blend_channel(mode, dr / 255.0, sr / 255.0)
    bg = _blend_channel(mode, dg / 255.0, sg / 255.0)
    bb = _blend_channel(mode, db / 255.0, sb / 255.0)

    # Mix blended result with backdrop by source alpha (Aseprite-style)
    cr = (1.0 - sa_f) * (dr / 255.0) + sa_f * br
    cg = (1.0 - sa_f) * (dg / 255.0) + sa_f * bg
    cb = (1.0 - sa_f) * (db / 255.0) + sa_f * bb
    out_a = sa_f + da_f * (1.0 - sa_f)
    return (
        _clamp_byte(cr * 255),
        _clamp_byte(cg * 255),
        _clamp_byte(cb * 255),
        _clamp_byte(out_a * 255),
    )


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------

@dataclass
class Cel:
    x: int = 0
    y: int = 0
    opacity: int = 255
    # Sparse pixel map: (x,y) -> RGBA. Coordinates are absolute sprite coords.
    pixels: dict[Tuple[int, int], Color] = field(default_factory=dict)

    def set_pixel(self, x: int, y: int, color: Color) -> None:
        if color[3] <= 0:
            self.pixels.pop((x, y), None)
        else:
            self.pixels[(x, y)] = (
                int(color[0]) & 255,
                int(color[1]) & 255,
                int(color[2]) & 255,
                int(color[3]) & 255,
            )

    def get_pixel(self, x: int, y: int) -> Color:
        return self.pixels.get((x, y), (0, 0, 0, 0))

    def clear(self) -> None:
        self.pixels.clear()

    def bounds(self) -> Optional[Tuple[int, int, int, int]]:
        if not self.pixels:
            return None
        xs = [p[0] for p in self.pixels]
        ys = [p[1] for p in self.pixels]
        return min(xs), min(ys), max(xs), max(ys)

    def shift(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        self.pixels = {(x + dx, y + dy): c for (x, y), c in self.pixels.items()}
        self.x += dx
        self.y += dy


@dataclass
class Layer:
    """Image layer. blend_mode is a string name (e.g. 'addition', 'multiply')."""

    name: str
    blend_mode: BlendModeName = "normal"
    opacity: int = 255
    visible: bool = True
    # cels[frame_index] -> Cel | None
    cels: List[Optional[Cel]] = field(default_factory=list)

    @property
    def blend_mode_id(self) -> int:
        key = self.blend_mode.lower().replace("-", "_").replace(" ", "_")
        if key not in BLEND_MODES:
            raise ValueError(f"Unknown blend mode {self.blend_mode!r}. Use one of: {sorted(set(BLEND_MODES))}")
        return BLEND_MODES[key]


@dataclass
class Tag:
    name: str
    from_frame: int
    to_frame: int
    direction: str = "forward"  # forward | reverse | pingpong


@dataclass
class Sprite:
    width: int
    height: int
    frame_count: int = 1
    frame_durations: List[int] = field(default_factory=list)  # ms per frame
    layers: List[Layer] = field(default_factory=list)
    tags: List[Tag] = field(default_factory=list)
    palette: List[Color] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.frame_durations:
            self.frame_durations = [100] * self.frame_count
        while len(self.frame_durations) < self.frame_count:
            self.frame_durations.append(100)

    # -- structure ---------------------------------------------------------

    def add_layer(
        self,
        name: str,
        blend_mode: BlendModeName = "normal",
        opacity: int = 255,
        visible: bool = True,
    ) -> Layer:
        layer = Layer(name=name, blend_mode=blend_mode, opacity=opacity, visible=visible)
        layer.cels = [None] * self.frame_count
        self.layers.append(layer)
        return layer

    def ensure_cel(self, layer: Union[int, str, Layer], frame: int = 0) -> Cel:
        layer_obj = self._resolve_layer(layer)
        self._ensure_frame(frame)
        if layer_obj.cels[frame] is None:
            layer_obj.cels[frame] = Cel()
        return layer_obj.cels[frame]  # type: ignore[return-value]

    def add_frame(self, duration_ms: int = 100, copy_from: Optional[int] = None) -> int:
        idx = self.frame_count
        self.frame_count += 1
        self.frame_durations.append(duration_ms)
        for layer in self.layers:
            if copy_from is not None and layer.cels[copy_from] is not None:
                src = layer.cels[copy_from]
                assert src is not None
                layer.cels.append(
                    Cel(x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels))
                )
            else:
                layer.cels.append(None)
        return idx

    def set_frame_duration(self, frame: int, duration_ms: int) -> None:
        self._ensure_frame(frame)
        self.frame_durations[frame] = duration_ms

    def add_tag(self, name: str, from_frame: int, to_frame: int, direction: str = "forward") -> Tag:
        tag = Tag(name=name, from_frame=from_frame, to_frame=to_frame, direction=direction)
        self.tags.append(tag)
        return tag

    # -- drawing -----------------------------------------------------------

    def put_pixel(
        self,
        x: int,
        y: int,
        color: Color,
        layer: Union[int, str, Layer] = 0,
        frame: int = 0,
    ) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        cel = self.ensure_cel(layer, frame)
        cel.set_pixel(x, y, color)

    def fill_rect(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        color: Color,
        layer: Union[int, str, Layer] = 0,
        frame: int = 0,
    ) -> None:
        xa, xb = sorted((x0, x1))
        ya, yb = sorted((y0, y1))
        cel = self.ensure_cel(layer, frame)
        for y in range(ya, yb + 1):
            for x in range(xa, xb + 1):
                if 0 <= x < self.width and 0 <= y < self.height:
                    cel.set_pixel(x, y, color)

    def fill_circle(
        self,
        cx: int,
        cy: int,
        radius: int,
        color: Color,
        layer: Union[int, str, Layer] = 0,
        frame: int = 0,
        fill: bool = True,
    ) -> None:
        cel = self.ensure_cel(layer, frame)
        r2 = radius * radius
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                d2 = (x - cx) * (x - cx) + (y - cy) * (y - cy)
                if fill:
                    if d2 <= r2 and 0 <= x < self.width and 0 <= y < self.height:
                        cel.set_pixel(x, y, color)
                else:
                    # 1px outline ring
                    if abs(d2 - r2) <= radius and 0 <= x < self.width and 0 <= y < self.height:
                        cel.set_pixel(x, y, color)

    def stamp(
        self,
        pixels: Iterable[Tuple[int, int, Color]],
        layer: Union[int, str, Layer] = 0,
        frame: int = 0,
        ox: int = 0,
        oy: int = 0,
    ) -> None:
        cel = self.ensure_cel(layer, frame)
        for x, y, color in pixels:
            px, py = x + ox, y + oy
            if 0 <= px < self.width and 0 <= py < self.height:
                cel.set_pixel(px, py, color)

    # -- compositing / preview ---------------------------------------------

    def composite_frame(self, frame: int = 0, background: Optional[Color] = None) -> Image.Image:
        """Composite all visible layers for `frame` into a PIL RGBA image.

        Simulates Aseprite blend modes (addition, screen, multiply, …) so
        previews match the real .aseprite file.
        """
        self._ensure_frame(frame)
        img = Image.new("RGBA", (self.width, self.height), background or (0, 0, 0, 0))
        dst = img.load()
        assert dst is not None

        for layer in self.layers:
            if not layer.visible:
                continue
            cel = layer.cels[frame] if frame < len(layer.cels) else None
            if cel is None or not cel.pixels:
                continue
            mode = layer.blend_mode.lower().replace("-", "_").replace(" ", "_")
            layer_opacity = layer.opacity
            cel_opacity = cel.opacity
            # Combine opacities like Aseprite (layer * cel / 255)
            opacity = (layer_opacity * cel_opacity) // 255

            for (x, y), src in cel.pixels.items():
                if not (0 <= x < self.width and 0 <= y < self.height):
                    continue
                dst[x, y] = _compose_pixel(dst[x, y], src, mode, opacity)
        return img

    def preview(
        self,
        path: Union[str, Path],
        scale: int = 8,
        frame: int = 0,
        background: Optional[Color] = None,
    ) -> Path:
        path = Path(path)
        img = self.composite_frame(frame, background=background)
        if scale != 1:
            img = img.resize((self.width * scale, self.height * scale), Image.NEAREST)
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path)
        return path

    def preview_gif(
        self,
        path: Union[str, Path],
        scale: int = 8,
        background: Optional[Color] = (24, 24, 32, 255),
        frames: Optional[Sequence[int]] = None,
    ) -> Path:
        path = Path(path)
        indices = list(frames) if frames is not None else list(range(self.frame_count))
        images = []
        durations = []
        for fi in indices:
            img = self.composite_frame(fi, background=background)
            if scale != 1:
                img = img.resize((self.width * scale, self.height * scale), Image.NEAREST)
            images.append(img.convert("RGBA"))
            durations.append(self.frame_durations[fi])
        path.parent.mkdir(parents=True, exist_ok=True)
        if not images:
            raise ValueError("No frames to export")
        images[0].save(
            path,
            save_all=True,
            append_images=images[1:],
            duration=durations,
            loop=0,
            disposal=2,
        )
        return path

    # -- I/O ---------------------------------------------------------------

    def save(self, path: Union[str, Path]) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.to_bytes())
        return path

    def to_bytes(self) -> bytes:
        nframes = max(1, self.frame_count)
        while len(self.frame_durations) < nframes:
            self.frame_durations.append(100)

        header = bytearray()
        header += struct.pack("<H", 0xA5E0)
        header += struct.pack("<H", nframes)
        header += struct.pack("<HH", self.width, self.height)
        header += struct.pack("<H", 32)  # RGBA
        header += struct.pack("<I", 1)  # flags: layer opacity valid
        header += struct.pack("<H", self.frame_durations[0])
        header += struct.pack("<II", 0, 0)
        header += struct.pack("<B", 0)  # transparent index
        header += b"\x00\x00\x00"
        header += struct.pack("<H", len(self.palette) if self.palette else 0)
        header += struct.pack("<BB", 1, 1)
        header += struct.pack("<hh", 0, 0)
        header += struct.pack("<HH", 16, 16)
        header += b"\x00" * 84
        assert len(header) == 124

        frames_bin = bytearray()
        for fi in range(nframes):
            chunks = bytearray()
            if fi == 0:
                for layer in self.layers:
                    flags = 0
                    if layer.visible:
                        flags |= 1
                    flags |= 2  # editable
                    body = (
                        struct.pack("<H", flags)
                        + struct.pack("<H", 0)  # image layer
                        + struct.pack("<H", 0)  # child level
                        + struct.pack("<HH", 0, 0)
                        + struct.pack("<H", layer.blend_mode_id)
                        + struct.pack("<B", max(0, min(255, layer.opacity)))
                        + b"\x00\x00\x00"
                        + _ase_string(layer.name)
                    )
                    chunks += self._chunk(0x2004, body)

                if self.palette:
                    body = (
                        struct.pack("<I", len(self.palette))
                        + struct.pack("<I", 0)
                        + struct.pack("<I", len(self.palette) - 1)
                        + b"\x00" * 8
                    )
                    for r, g, b, a in self.palette:
                        body += struct.pack("<H", 0) + bytes((r, g, b, a))
                    chunks += self._chunk(0x2019, body)

                if self.tags:
                    body = struct.pack("<H", len(self.tags)) + b"\x00" * 8
                    dir_map = {"forward": 0, "reverse": 1, "pingpong": 2, "ping-pong": 2}
                    for tag in self.tags:
                        body += struct.pack("<HH", tag.from_frame, tag.to_frame)
                        body += struct.pack("<B", dir_map.get(tag.direction.lower(), 0))
                        body += struct.pack("<H", 0)
                        body += b"\x00" * 6
                        body += b"\x00\x00\x00\x00"
                        body += _ase_string(tag.name)
                    chunks += self._chunk(0x2018, body)

            for li, layer in enumerate(self.layers):
                cel = layer.cels[fi] if fi < len(layer.cels) else None
                if cel is None or not cel.pixels:
                    continue
                chunks += self._cel_chunk(li, cel)

            nchunks = self._count_chunks(chunks)
            frame = (
                struct.pack("<H", 0xF1FA)
                + struct.pack("<H", min(nchunks, 0xFFFF))
                + struct.pack("<H", self.frame_durations[fi])
                + b"\x00\x00"
                + struct.pack("<I", nchunks)
                + chunks
            )
            frames_bin += struct.pack("<I", len(frame) + 4) + frame

        payload = bytes(header) + bytes(frames_bin)
        return struct.pack("<I", len(payload) + 4) + payload

    @staticmethod
    def _chunk(ctype: int, data: bytes) -> bytes:
        return struct.pack("<I", len(data) + 6) + struct.pack("<H", ctype) + data

    @staticmethod
    def _count_chunks(chunks: bytes) -> int:
        offset = 0
        count = 0
        while offset + 6 <= len(chunks):
            (size,) = struct.unpack_from("<I", chunks, offset)
            if size < 6:
                break
            offset += size
            count += 1
        return count

    def _cel_chunk(self, layer_index: int, cel: Cel) -> bytes:
        b = cel.bounds()
        if b is None:
            return b""
        x0, y0, x1, y1 = b
        w = x1 - x0 + 1
        h = y1 - y0 + 1
        raw = bytearray(w * h * 4)
        for (x, y), (r, g, b_, a) in cel.pixels.items():
            lx, ly = x - x0, y - y0
            i = (ly * w + lx) * 4
            raw[i : i + 4] = bytes((r, g, b_, a))
        body = (
            struct.pack("<H", layer_index)
            + struct.pack("<hh", x0, y0)
            + struct.pack("<B", max(0, min(255, cel.opacity)))
            + struct.pack("<H", 2)  # compressed image
            + struct.pack("<h", 0)  # z-index
            + b"\x00" * 5
            + struct.pack("<HH", w, h)
            + zlib.compress(bytes(raw))
        )
        return self._chunk(0x2005, body)

    # -- helpers -----------------------------------------------------------

    def _resolve_layer(self, layer: Union[int, str, Layer]) -> Layer:
        if isinstance(layer, Layer):
            return layer
        if isinstance(layer, int):
            return self.layers[layer]
        for candidate in self.layers:
            if candidate.name == layer:
                return candidate
        raise KeyError(f"Layer not found: {layer!r}")

    def _ensure_frame(self, frame: int) -> None:
        if frame < 0:
            raise IndexError(frame)
        while self.frame_count <= frame:
            self.add_frame()


def load_aseprite(path: Union[str, Path]) -> Sprite:
    """Load an .aseprite file into a Sprite (RGBA image layers only)."""
    data = Path(path).read_bytes()
    if len(data) < 128:
        raise ValueError("File too small to be .aseprite")
    (_file_size, magic, nframes, width, height, color_depth, flags) = struct.unpack_from(
        "<IHHHHHI", data, 0
    )
    if magic != 0xA5E0:
        raise ValueError(f"Bad magic 0x{magic:04X}")
    if color_depth != 32:
        raise ValueError(f"Only RGBA (32bpp) is supported by this reader (got {color_depth})")

    sprite = Sprite(width=width, height=height, frame_count=nframes)
    sprite.frame_durations = [100] * nframes
    sprite.layers = []

    offset = 128
    for fi in range(nframes):
        if offset + 16 > len(data):
            break
        frame_size, frame_magic, old_chunks, duration, _pad, new_chunks = struct.unpack_from(
            "<IHHLHI", data, offset
        )
        if frame_magic != 0xF1FA:
            raise ValueError(f"Bad frame magic at frame {fi}")
        sprite.frame_durations[fi] = duration or 100
        nchunks = new_chunks or old_chunks
        chunk_offset = offset + 16
        frame_end = offset + frame_size

        for _ in range(nchunks):
            if chunk_offset + 6 > frame_end:
                break
            (chunk_size, chunk_type) = struct.unpack_from("<IH", data, chunk_offset)
            body = data[chunk_offset + 6 : chunk_offset + chunk_size]
            if chunk_type == 0x2004 and fi == 0:
                flags_w, _ltype, _child, _dw, _dh, blend_id, opacity = struct.unpack_from(
                    "<HHHHHHB", body, 0
                )
                name, _ = _read_string(body, 16)
                mode = BLEND_MODE_IDS.get(blend_id, "normal")
                layer = Layer(
                    name=name,
                    blend_mode=mode,
                    opacity=opacity,
                    visible=bool(flags_w & 1),
                )
                layer.cels = [None] * nframes
                sprite.layers.append(layer)
            elif chunk_type == 0x2005:
                layer_index, x, y, opacity, cel_type = struct.unpack_from("<HhhBH", body, 0)
                if cel_type == 2:
                    w, h = struct.unpack_from("<HH", body, 16)
                    compressed = body[20:]
                    raw = zlib.decompress(compressed)
                    if layer_index < len(sprite.layers):
                        cel = Cel(x=x, y=y, opacity=opacity)
                        for py in range(h):
                            for px in range(w):
                                i = (py * w + px) * 4
                                r, g, b, a = raw[i : i + 4]
                                if a:
                                    cel.set_pixel(x + px, y + py, (r, g, b, a))
                        sprite.layers[layer_index].cels[fi] = cel
                elif cel_type == 1:
                    # Linked cel — copy reference frame pixels shallowly at read time
                    (link_frame,) = struct.unpack_from("<H", body, 16)
                    if layer_index < len(sprite.layers) and link_frame < nframes:
                        src = sprite.layers[layer_index].cels[link_frame]
                        if src is not None:
                            sprite.layers[layer_index].cels[fi] = Cel(
                                x=src.x, y=src.y, opacity=src.opacity, pixels=dict(src.pixels)
                            )
            elif chunk_type == 0x2018 and fi == 0:
                (ntag,) = struct.unpack_from("<H", body, 0)
                pos = 10  # skip count + 8 reserved
                for _t in range(ntag):
                    frm, to, direction = struct.unpack_from("<HHB", body, pos)
                    pos += 17  # from/to/dir/repeat/reserved6/rgb3/extra
                    name, pos = _read_string(body, pos)
                    dir_name = {0: "forward", 1: "reverse", 2: "pingpong"}.get(direction, "forward")
                    sprite.tags.append(Tag(name=name, from_frame=frm, to_frame=to, direction=dir_name))
            chunk_offset += chunk_size
        offset = frame_end

    # Ensure every layer has frame_count cels slots
    for layer in sprite.layers:
        while len(layer.cels) < sprite.frame_count:
            layer.cels.append(None)
    return sprite

"""Editable, deterministic teaching diagrams drawn identically in SVG and PNG.

All marks, including plots and scene geometry, are local vector primitives.  The
small raster companions use the font shipped by matplotlib and a fixed palette;
they need neither a browser nor network access to regenerate.
"""

import html
import math
from pathlib import Path

import matplotlib
from PIL import Image, ImageDraw, ImageFont

INK = "#172b45"
MUTED = "#586b80"
BLUE = "#2976c9"
TEAL = "#008b87"
ORANGE = "#d98524"
RED = "#c84c61"
PURPLE = "#8057ad"
PALE = "#edf3f8"
GRID = "#d4dee8"
WHITE = "#ffffff"
BG = "#f8fafc"
GREEN = "#44854c"
WIDTH = 1200
HEIGHT = 760
PNG_COLORS = 32


class Canvas:
    """A single display list, with editable text and checked label extents."""

    width, height, scale = WIDTH, HEIGHT, 2

    def __init__(self):
        self.picture = Image.new("RGB", (self.width * self.scale, self.height * self.scale), BG)
        self.draw = ImageDraw.Draw(self.picture)
        self.font_root = Path(matplotlib.get_data_path()) / "fonts/ttf"
        self.fonts = {}
        self.parts = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" '
            'viewBox="0 0 1200 760">',
            f'<rect width="1200" height="760" fill="{BG}"/>',
            '<g font-family="DejaVu Sans">',
        ]

    def font(self, size, bold=False):
        key = (size, bold)
        if key not in self.fonts:
            name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
            self.fonts[key] = ImageFont.truetype(str(self.font_root / name), size * self.scale)
        return self.fonts[key]

    def text(self, x, y, value, size=18, color=INK, bold=False, anchor="start"):
        value = str(value)
        font = self.font(size, bold)
        width = self.draw.textlength(value, font=font) / self.scale
        left = x - (width / 2 if anchor == "middle" else width if anchor == "end" else 0)
        # Detect clipping during asset generation instead of silently losing text.
        top, bottom = font.getbbox(value, anchor="ls")[1::2]
        if (
            left < 15
            or left + width > self.width - 15
            or y + top / self.scale < 5
            or y + bottom / self.scale > 747
        ):
            raise ValueError(f"Illustration label outside canvas: {value!r} at {(x, y)}")
        weight = "bold" if bold else "normal"
        self.parts.append(
            f'<text x="{x:g}" y="{y:g}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{color}">{html.escape(value)}</text>'
        )
        self.draw.text(
            (left * self.scale, y * self.scale), value, font=font, fill=color, anchor="ls"
        )

    def rect(self, x, y, w, h, fill=WHITE, stroke=GRID, radius=10, width=1.5):
        self.parts.append(
            f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{radius:g}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{width:g}"/>'
        )
        self.draw.rounded_rectangle(
            (x * 2, y * 2, (x + w) * 2, (y + h) * 2),
            radius=radius * 2,
            fill=fill,
            outline=stroke,
            width=max(1, round(width * 2)),
        )

    def line(self, points, color=INK, width=2, dash=False):
        coords = " ".join(f"{x:g},{y:g}" for x, y in points)
        dashed = ' stroke-dasharray="6 5"' if dash else ""
        self.parts.append(
            f'<polyline points="{coords}" fill="none" stroke="{color}" '
            f'stroke-width="{width:g}" stroke-linejoin="round"{dashed}/>'
        )
        if dash:
            # SVG dashes advance continuously along a polyline. Preserve that
            # arc-length phase in PNG too, including short curve subdivisions.
            segments = []
            offset = 0.0
            for start, end in zip(points, points[1:]):
                length = math.dist(start, end)
                if length:
                    segments.append((start, end, offset, length))
                    offset += length
            for dash_start in range(0, math.ceil(offset), 11):
                dash_end = min(dash_start + 6, offset)
                for (x1, y1), (x2, y2), start, length in segments:
                    lo, hi = max(dash_start, start), min(dash_end, start + length)
                    if hi <= lo:
                        continue
                    a, b = (lo - start) / length, (hi - start) / length
                    self.draw.line(
                        [
                            (2 * (x1 + a * (x2 - x1)), 2 * (y1 + a * (y2 - y1))),
                            (2 * (x1 + b * (x2 - x1)), 2 * (y1 + b * (y2 - y1))),
                        ],
                        fill=color,
                        width=max(1, round(width * 2)),
                    )
        else:
            self.draw.line(
                [(x * 2, y * 2) for x, y in points],
                fill=color,
                width=max(1, round(width * 2)),
                joint="curve",
            )

    def polygon(self, points, fill, stroke=None, width=1.5):
        coords = " ".join(f"{x:g},{y:g}" for x, y in points)
        self.parts.append(
            f'<polygon points="{coords}" fill="{fill}" stroke="{stroke or fill}" '
            f'stroke-width="{width:g}"/>'
        )
        self.draw.polygon([(x * 2, y * 2) for x, y in points], fill=fill)
        if stroke:
            self.draw.line(
                [(x * 2, y * 2) for x, y in [*points, points[0]]],
                fill=stroke,
                width=max(1, round(width * 2)),
            )

    def ellipse(self, x, y, rx, ry, fill=WHITE, stroke=GRID, width=2):
        self.parts.append(
            f'<ellipse cx="{x:g}" cy="{y:g}" rx="{rx:g}" ry="{ry:g}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{width:g}"/>'
        )
        self.draw.ellipse(
            ((x - rx) * 2, (y - ry) * 2, (x + rx) * 2, (y + ry) * 2),
            fill=fill,
            outline=stroke,
            width=max(1, round(width * 2)),
        )

    def arrow(self, points, color=INK, width=2.3, dash=False):
        self.line(points, color, width, dash)
        x, y = points[-1]
        px, py = points[-2]
        angle = math.atan2(y - py, x - px)
        length = 10
        self.polygon(
            [
                (x, y),
                (x - length * math.cos(angle - 0.45), y - length * math.sin(angle - 0.45)),
                (x - length * math.cos(angle + 0.45), y - length * math.sin(angle + 0.45)),
            ],
            color,
        )

    def curve(self, points, color=BLUE, width=3, dash=False):
        """A cubic curve sampled once for the two output formats."""
        p0, p1, p2, p3 = points
        sampled = []
        for i in range(41):
            t = i / 40
            sampled.append(
                tuple(
                    (1 - t) ** 3 * p0[j]
                    + 3 * (1 - t) ** 2 * t * p1[j]
                    + 3 * (1 - t) * t * t * p2[j]
                    + t**3 * p3[j]
                    for j in range(2)
                )
            )
        self.line(sampled, color, width, dash)

    def node(self, x, y, w, h, title, color=BLUE, fill=WHITE, size=18):
        self.rect(x, y, w, h, fill, color)
        self.text(x + w / 2, y + h / 2 + size * 0.34, title, size, color, True, "middle")

    def section(self, x, y, number, title, color=BLUE):
        self.ellipse(x + 13, y - 7, 13, 13, color, color)
        self.text(x + 13, y - 1, number, 15, WHITE, True, "middle")
        self.text(x + 36, y, title, 20, INK, True)

    def matrix(
        self,
        x,
        y,
        values,
        cell_w=62,
        cell_h=44,
        row_labels=None,
        col_labels=None,
        colors=None,
        size=18,
    ):
        for i, row in enumerate(values):
            if row_labels:
                self.text(
                    x - 13, y + i * cell_h + cell_h * 0.65, row_labels[i], size, MUTED, anchor="end"
                )
            for j, value in enumerate(row):
                fill = colors[i][j] if colors else WHITE
                self.rect(
                    x + j * cell_w, y + i * cell_h, cell_w, cell_h, fill, GRID, radius=0, width=1
                )
                self.text(
                    x + (j + 0.5) * cell_w,
                    y + (i + 0.66) * cell_h,
                    value,
                    size,
                    INK,
                    anchor="middle",
                )
        if col_labels:
            for j, value in enumerate(col_labels):
                self.text(x + (j + 0.5) * cell_w, y - 12, value, size - 1, MUTED, anchor="middle")

    def bar(self, x, y, value, maximum, color, label, w=160, h=18):
        self.text(x, y - 8, label, 17, MUTED)
        self.rect(x, y, w, h, PALE, PALE, radius=3)
        if value:
            self.rect(x, y, w * value / maximum, h, color, color, radius=3)

    def finish(self, destination, identifier):
        destination.mkdir(parents=True, exist_ok=True)
        svg = destination / f"{identifier}.svg"
        png = destination / f"{identifier}.png"
        svg.write_text("\n".join([*self.parts, "</g></svg>"]) + "\n")
        reduced = self.picture.resize((self.width, self.height), Image.Resampling.LANCZOS)
        # Fix semantic colors rather than letting a mostly white image discard
        # low-area colors (for example, a red gradient barrier or orange mode).
        colors = [
            BG,
            WHITE,
            INK,
            MUTED,
            BLUE,
            TEAL,
            ORANGE,
            RED,
            PURPLE,
            GRID,
            "#e6f2f1",
            "#eaf2fb",
            "#f6e8eb",
            "#f9efdf",
            "#efeaf6",
            "#e7eee8",
            "#728095",
            "#a6afbb",
            "#cbd1d9",
            "#dde2e8",
            "#75a3d4",
            "#a7c5e5",
            "#75bdb9",
            "#a7d6d2",
            "#e0aa6b",
            "#ebc89d",
            "#d78a98",
            "#e7b9c1",
            "#aa8cc8",
            "#c9b6dd",
            "#eef1f6",
            "#e4eaf1",
        ]
        assert len(colors) == PNG_COLORS
        palette = Image.new("P", (1, 1))
        rgb = [channel for color in colors for channel in bytes.fromhex(color[1:])]
        palette.putpalette(rgb + [0] * (768 - len(rgb)))
        reduced.quantize(palette=palette, dither=Image.Dither.NONE).save(png, bits=8, optimize=True)


def _vehicle(c, x, y, color=BLUE, vertical=False, label=None):
    w, h = (23, 43) if vertical else (43, 23)
    c.rect(x - w / 2, y - h / 2, w, h, color, color, radius=5)
    c.rect(x - w * 0.2, y - h * 0.3, w * 0.4, h * 0.6, "#eaf2f8", color, radius=2, width=1)
    if label:
        c.text(x, y + h / 2 + 25, label, 17, color, True, "middle")


def _road(c, x, y, w, h):
    c.rect(x, y, w, h, "#e7eee8", "#e7eee8", radius=14)
    cx, cy = x + w * 0.53, y + h * 0.51
    c.rect(x + 1, cy - 47, w - 2, 94, "#dee6ec", "#dee6ec", radius=0)
    c.rect(cx - 47, y + 1, 94, h - 2, "#dee6ec", "#dee6ec", radius=0)
    for left, right in ((x + 12, cx - 52), (cx + 52, x + w - 12)):
        c.line([(left, cy), (right, cy)], WHITE, 2, True)
    for top, bottom in ((y + 12, cy - 52), (cy + 52, y + h - 12)):
        c.line([(cx, top), (cx, bottom)], WHITE, 2, True)
    # Vector crosswalks and curb lines make the observation scene recognizable.
    for j in range(5):
        c.rect(cx - 42 + j * 18, cy + 55, 9, 25, WHITE, WHITE, radius=0)
    c.line([(x + 12, cy - 48), (cx - 49, cy - 48), (cx - 49, y + 12)], MUTED, 1)
    c.line([(cx + 49, y + 12), (cx + 49, cy - 48), (x + w - 12, cy - 48)], MUTED, 1)
    return cx, cy


def _token_stack(c, x, y, count=5, color=BLUE, label=None):
    for i in reversed(range(count)):
        c.rect(x + i * 5, y - i * 5, 70, 32, WHITE, color, radius=3)
        for j in range(5):
            c.line(
                [
                    (x + i * 5 + 10 + j * 10, y - i * 5 + 9),
                    (x + i * 5 + 10 + j * 10, y - i * 5 + 23),
                ],
                color,
                2,
            )
    if label:
        c.text(x + 40, y + 61, label, 17, color, anchor="middle")


def _plus(c, x, y, color=INK, symbol="+"):
    c.ellipse(x, y, 17, 17, WHITE, color, 2)
    c.text(x, y + 6, symbol, 20, color, True, "middle")


def _overview(c):
    c.section(42, 143, "1", "Observe a shared scene")
    cx, cy = _road(c, 42, 167, 355, 350)
    _vehicle(c, 114, cy + 23, BLUE, label="agent A")
    _vehicle(c, cx + 22, 234, TEAL, True, "agent B")
    for off, color in ((-42, BLUE), (0, ORANGE), (42, PURPLE)):
        c.curve([(139, cy + 23), (220, cy + 23), (cx + 70, cy + off), (362, cy + off)], color, 3)
        c.curve([(cx + 22, 261), (cx + 22, cy), (cx + off, 420), (cx + off, 487)], color, 3, True)
    c.text(52, 552, "Solid: A  ·  dashed: B", 18, MUTED)
    c.text(52, 583, "Color = one joint mode", 18, INK, True)
    c.text(52, 620, "History: 11 samples at 0.1 s; future: 80 × 0.1 s", 16, MUTED)
    c.arrow([(410, 340), (463, 340)], BLUE, 3)
    c.section(470, 143, "2", "Encode, then reason")
    for y, title, color in (
        (190, "Actor histories → LSTMs", BLUE),
        (255, "Lanes / crosswalks → MLPs", TEAL),
    ):
        c.node(480, y, 305, 45, title, color, size=18)
    c.arrow([(785, 212), (815, 212), (815, 337), (785, 337)], BLUE)
    c.arrow([(632, 300), (632, 315)], TEAL)
    c.node(480, 315, 305, 48, "Scene Transformer · D = 256", PURPLE, size=17)
    c.arrow([(632, 363), (632, 409)], PURPLE)
    c.node(480, 409, 305, 55, "Level 0: agent + mode queries", BLUE, size=17)
    c.arrow([(632, 464), (632, 502)], BLUE)
    c.node(480, 502, 305, 56, "Level k responds to level k − 1", TEAL, size=16)
    c.arrow([(785, 530), (839, 530), (839, 245), (926, 245)], TEAL)
    c.text(632, 584, "Repeat response levels k = 1 … K", 16, TEAL, anchor="middle")
    c.text(477, 605, "Every level predicts means, uncertainty and scores.", 16, MUTED)
    c.section(867, 143, "3", "Learn and select")
    _token_stack(c, 926, 225, 6, PURPLE)
    c.text(1000, 309, "2 agents × 6 modes", 18, PURPLE, True, "middle")
    c.arrow([(855, 245), (855, 369), (868, 369)], RED)
    c.node(868, 340, 284, 58, "All-level supervision", RED)
    c.arrow([(1020, 241), (1170, 241), (1170, 479), (1152, 479)], BLUE)
    c.node(868, 450, 284, 58, "Scores select a joint mode", BLUE, size=17)
    c.text(876, 557, "One index selects both agents.", 17, INK)
    c.text(876, 589, "Targets supervise training only.", 16, MUTED)
    c.rect(470, 635, 680, 43, PALE, PALE)
    c.text(490, 663, "Output: [levels, B, P, M, T, 4]    4 = μx, μy, log σx, log σy", 17)


def _scene_tensors(c):
    c.section(45, 142, "1", "World → local frame")
    c.rect(45, 166, 493, 344, WHITE, GRID)
    ox, oy = 164, 417
    c.arrow([(81, oy), (470, oy)], MUTED)
    c.arrow([(ox, 477), (ox, 190)], MUTED)
    c.text(459, 447, "world x", 17, MUTED, anchor="end")
    c.text(177, 199, "world y", 17, MUTED)
    c.arrow([(ox, oy), (ox, oy - 150)], BLUE, 4)
    c.arrow([(ox, oy), (ox - 75, oy)], TEAL, 4)
    c.ellipse(ox, oy - 110, 7, 7, ORANGE, ORANGE)
    c.text(187, 311, "point (10, 6) m", 18, ORANGE, True)
    c.text(187, 347, "Δ = (0, 1) m", 18)
    c.text(187, 393, "focal (10, 5), heading 90°", 17, BLUE)
    c.text(86, 248, "+x local", 17, BLUE)
    c.text(63, 456, "+y local", 17, TEAL)
    c.text(61, 550, "p_local = R(−heading) · (p_world − origin)", 19, INK, True)
    c.text(61, 588, "(0, 1) world → (1, 0) local", 21, BLUE, True)
    c.text(61, 625, "+x follows the focal actor; +y points left.", 17, MUTED)
    c.section(589, 142, "2", "Coordinates and validity are separate")
    c.matrix(
        705,
        204,
        [["0", "0"], ["1", "0"], ["0", "0"]],
        95,
        51,
        ["focal", "point", "padding"],
        ["x (m)", "y (m)"],
        [["#e6f2f1"] * 2, [WHITE] * 2, [PALE] * 2],
    )
    c.matrix(
        955,
        204,
        [["true"], ["true"], ["false"]],
        130,
        51,
        col_labels=["validity"],
        colors=[["#e6f2f1"], ["#e6f2f1"], ["#f6e8eb"]],
    )
    c.line([(945, 202), (945, 360)], MUTED, 1, True)
    c.text(623, 409, "A valid origin is still data.", 22, TEAL, True)
    c.rect(598, 447, 550, 71, "#eaf2fb", BLUE)
    c.text(619, 476, "Observed history  [B, 34, 11, 9]", 20, BLUE, True)
    c.text(619, 502, "x, y, heading, vx, vy, length, width, height, type", 16, MUTED)
    c.rect(598, 555, 550, 73, "#f7edf0", RED)
    c.text(619, 585, "Future labels  [B, 2, 80, 2]", 20, RED, True)
    c.text(619, 611, "Separate future_valid mask; loss reads valid labels.", 16, MUTED)
    c.line([(857, 518), (857, 553)], RED, 2, True)
    c.line([(846, 528), (868, 546)], RED, 3)
    c.line([(868, 528), (846, 546)], RED, 3)
    c.text(884, 543, "No labels in encoder", 16, RED)
    c.text(611, 672, "Units: meters · radians · meters/second · seconds", 17, MUTED)


def _agent_history(c):
    c.section(43, 143, "1", "Unroll observed motion through time")
    for i, x in enumerate((100, 280, 460, 640)):
        c.node(x, 193, 110, 44, "LSTM 1", BLUE)
        c.node(x, 270, 110, 44, "LSTM 2", TEAL)
        c.arrow([(x + 55, 237), (x + 55, 270)], BLUE)
        c.text(x + 55, 359, ("t = −10", "t = −9", "…", "t = 0")[i], 18, MUTED, anchor="middle")
        c.arrow([(x + 55, 175), (x + 55, 193)], MUTED)
        c.text(x + 55, 166, "x_t", 16, MUTED, anchor="middle")
        if i:
            c.arrow([(x - 70, 215), (x, 215)], BLUE)
            c.arrow([(x - 70, 292), (x, 292)], TEAL)
    c.arrow([(750, 292), (813, 292)], TEAL)
    _plus(c, 839, 292, PURPLE)
    c.node(774, 181, 132, 54, "Type lookup", PURPLE, size=16)
    c.arrow([(839, 235), (839, 274)], PURPLE)
    c.arrow([(857, 292), (930, 292)], PURPLE)
    _token_stack(c, 950, 276, 4, PURPLE)
    c.text(992, 358, "Actor token · D = 256", 18, PURPLE, True, "middle")
    c.line([(45, 391), (1154, 391)], GRID, 1)
    c.section(43, 432, "2", "Inside one scalar LSTM memory cell")
    c.text(65, 494, "c_prev = 1.0", 19, BLUE, True)
    c.arrow([(206, 487), (295, 487)], BLUE)
    _plus(c, 319, 487, BLUE, "×")
    c.node(259, 538, 120, 42, "f = 0.8", BLUE)
    c.arrow([(319, 538), (319, 505)], BLUE)
    c.arrow([(337, 487), (442, 487)], BLUE)
    c.text(387, 470, "0.8", 17, BLUE)
    _plus(c, 460, 487, INK)
    c.node(389, 611, 130, 40, "i = 0.5", TEAL)
    c.node(568, 611, 130, 40, "g = 0.4", ORANGE)
    _plus(c, 543, 558, TEAL, "×")
    c.arrow([(454, 611), (454, 558), (525, 558)], TEAL)
    c.arrow([(633, 611), (633, 558), (561, 558)], ORANGE)
    c.arrow([(543, 540), (543, 521), (460, 521), (460, 505)], TEAL)
    c.text(572, 538, "0.2", 17, TEAL)
    c.arrow([(478, 487), (674, 487)], INK)
    c.text(570, 470, "c_new = 1.0", 19, INK, True, "middle")
    c.node(674, 465, 108, 44, "tanh", PURPLE)
    c.arrow([(782, 487), (860, 487)], PURPLE)
    _plus(c, 878, 487, PURPLE, "×")
    c.node(818, 551, 120, 42, "o = 0.5", PURPLE)
    c.arrow([(878, 551), (878, 505)], PURPLE)
    c.arrow([(896, 487), (964, 487)], PURPLE)
    c.text(975, 494, "h = 0.3808", 20, PURPLE, True)
    c.text(981, 547, "+ type 0.1", 18, MUTED)
    c.text(981, 580, "= 0.4808", 20, PURPLE, True)
    c.text(
        67,
        686,
        "Toy arithmetic uses one channel. Focal and background actors have separate two-layer LSTMs.",
        17,
        MUTED,
    )


def _lane_encoding(c):
    c.section(43, 142, "1", "Geometry and semantics")
    c.rect(44, 171, 336, 310, "#e7eee8", GRID)
    for k, color in ((0, BLUE), (-38, MUTED), (38, MUTED)):
        c.curve(
            [(67, 436 + k), (180, 410 + k), (194, 263 + k), (353, 222 + k)],
            color,
            3 if k == 0 else 2,
            k == 0,
        )
    for x, y in ((111, 413), (191, 351), (252, 266)):
        c.ellipse(x, y, 6, 6, BLUE, BLUE)
    c.text(64, 206, "Left / center / right polylines", 16, MUTED)
    c.arrow([(191, 351), (220, 311)], BLUE)
    c.text(224, 310, "heading", 17, BLUE)
    c.node(57, 504, 145, 43, "Speed: m/s", ORANGE, size=17)
    c.node(217, 504, 148, 43, "Signal / IDs", PURPLE, size=17)
    c.text(57, 585, "Point fields: 17 channels", 19, INK, True)
    c.text(57, 618, "100 ordered points per lane", 17, MUTED)
    c.text(57, 651, "Legacy ID offsets are explicit.", 16, MUTED)
    c.section(420, 142, "2", "Parallel embeddings → point token")
    lanes = [
        (202, "Center xyz*", "128", BLUE),
        (265, "Left xyz*", "128", BLUE),
        (328, "Right xyz*", "128", BLUE),
        (391, "Speed", "64", ORANGE),
        (454, "Σ ID lookups", "64", PURPLE),
    ]
    for y, title, width, color in lanes:
        c.node(434, y, 162, 42, title, color, size=17)
        c.arrow([(596, y + 21), (630, y + 21)], color)
        c.node(630, y, 68, 42, width, color)
        c.line([(698, y + 21), (740, y + 21)], color)
    c.line([(740, 223), (740, 475)], INK, 2)
    c.arrow([(740, 349), (779, 349)], INK)
    c.node(779, 295, 95, 108, "512", BLUE, size=24)
    c.text(827, 433, "concat", 17, MUTED, anchor="middle")
    c.arrow([(874, 349), (912, 349)], BLUE)
    c.node(912, 295, 88, 108, "384", TEAL, size=24)
    c.text(956, 433, "ReLU", 17, MUTED, anchor="middle")
    c.arrow([(1000, 349), (1039, 349)], TEAL)
    c.node(1039, 295, 108, 108, "D256", PURPLE, size=23)
    c.arrow([(1093, 403), (1093, 501)], PURPLE)
    _plus(c, 1093, 519, PURPLE)
    c.curve([(755, 554), (800, 491), (845, 618), (890, 554)], ORANGE, 3)
    c.curve([(890, 554), (935, 491), (980, 618), (1025, 554)], ORANGE, 3)
    c.arrow([(1025, 554), (1093, 554), (1093, 537)], ORANGE)
    c.text(739, 609, "Sinusoidal point position", 18, ORANGE, True)
    c.text(739, 641, "Toy: (0.5, 0.6) + (0, 1) = (0.5, 1.6)", 17, MUTED)
    c.text(
        432,
        687,
        "* xyz here denotes (x, y, heading). Dropout follows position addition during training.",
        16,
        MUTED,
    )


def _crosswalk_encoding(c):
    c.section(43, 142, "1", "Polygon point inputs")
    c.rect(46, 174, 315, 280, "#e5eceb", GRID)
    for i in range(7):
        c.polygon(
            [(65 + i * 38, 420), (83 + i * 38, 420), (112 + i * 31, 205), (97 + i * 31, 205)], WHITE
        )
    for x, y in ((89, 407), (295, 399), (309, 219), (116, 215)):
        c.ellipse(x, y, 6, 6, TEAL, TEAL)
    c.ellipse(295, 399, 10, 10, ORANGE, ORANGE)
    c.text(64, 489, "Toy point: (2, −1, 0)", 20, ORANGE, True)
    c.text(64, 524, "x, y in meters; heading in radians", 16, MUTED)
    c.section(410, 142, "2", "A shared point-wise MLP")
    c.matrix(
        454,
        224,
        [["1", "0", "0"], ["0", "−1", "0"]],
        63,
        55,
        row_labels=["out 0", "out 1"],
        col_labels=["x", "y", "θ"],
        colors=[["#e6f2f1", WHITE, WHITE], [WHITE, "#f9efdf", WHITE]],
    )
    c.text(548, 373, "Toy W · point", 19, TEAL, True, "middle")
    c.arrow([(667, 278), (716, 278)], INK)
    c.matrix(727, 224, [["2"], ["1"]], 72, 55)
    c.arrow([(799, 278), (846, 278)], TEAL)
    c.node(846, 252, 105, 52, "ReLU", TEAL)
    c.arrow([(951, 278), (998, 278)], TEAL)
    c.matrix(1010, 224, [["2"], ["1"]], 72, 55, colors=[["#e6f2f1"], ["#e6f2f1"]])
    c.text(999, 373, "Negatives clipped to 0", 16, MUTED, anchor="middle")
    c.line([(411, 412), (1148, 412)], GRID)
    c.text(428, 453, "Actual widths", 19, INK, True)
    for i, (x, value) in enumerate(((432, "3"), (600, "64"), (768, "128"), (936, "256"))):
        c.node(x, 479, 105, 62, value, (BLUE, TEAL, TEAL, PURPLE)[i], size=24)
        if i < 3:
            c.arrow([(x + 105, 510), (x + 168, 510)], TEAL)
            if i < 2:
                c.text(x + 136, 569, "ReLU", 15, MUTED, anchor="middle")
    c.text(53, 605, "Full input", 18, MUTED)
    c.text(53, 638, "[B, P, 4, 50, 3]", 22, TEAL, True)
    c.arrow([(314, 625), (425, 625)], TEAL)
    c.text(446, 637, "[B, P, 4, 50, 256]", 22, PURPLE, True)
    c.text(780, 622, "The point axis is preserved.", 18, INK, True)
    c.text(780, 653, "No lane positional embedding.", 17, MUTED)


def _map_segments(c):
    c.section(43, 142, "1", "Mask points before reducing channels")
    c.matrix(
        145,
        208,
        [["1", "4"], ["7", "2"], ["99", "99"]],
        100,
        63,
        ["A ✓", "B ✓", "pad ×"],
        ["ch 0", "ch 1"],
        [[WHITE, "#e6f2f1"], ["#eaf2fb", WHITE], ["#f6e8eb"] * 2],
        23,
    )
    c.arrow([(370, 300), (440, 300)], RED)
    c.text(405, 259, "mask", 17, RED, True, "middle")
    c.matrix(
        449,
        208,
        [["1", "4"], ["7", "2"], ["−∞", "−∞"]],
        85,
        63,
        col_labels=["ch 0", "ch 1"],
        colors=[[WHITE, "#e6f2f1"], ["#eaf2fb", WHITE], [PALE] * 2],
        size=23,
    )
    c.arrow([(645, 301), (729, 301)], BLUE)
    c.text(687, 259, "max", 18, BLUE, True, "middle")
    c.matrix(743, 269, [["7", "4"]], 105, 64, colors=[["#eaf2fb", "#e6f2f1"]], size=28)
    c.text(851, 373, "Different channel winners", 19, INK, True, "middle")
    c.arrow([(195, 302), (195, 436), (797, 436), (797, 333)], BLUE, 2, True)
    c.arrow([(297, 238), (297, 162), (903, 162), (903, 268)], TEAL, 2, True)
    c.text(1002, 287, "B → 7", 19, BLUE, True)
    c.text(1002, 325, "A → 4", 19, TEAL, True)
    c.section(43, 497, "2", "Feature reduction and key visibility are different decisions")
    groups = [
        (65, "Strict / released", [True, True, False], "Hidden", RED),
        (451, "Practical / partial", [True, True, False], "Visible", TEAL),
        (837, "Empty group", [False, False, False], "Zero + hidden", MUTED),
    ]
    for x, title, flags, result, color in groups:
        c.text(x, 544, title, 19, color, True)
        for i, flag in enumerate(flags):
            c.node(x + i * 77, 568, 60, 44, "✓" if flag else "×", TEAL if flag else RED, size=23)
        c.text(x, 650, result, 22, color, True)
    c.text(
        65,
        687,
        "Full groups contain 10 points. Padding never wins the channel-wise max.",
        17,
        MUTED,
    )


def _scene_attention(c):
    c.section(43, 142, "1", "A masked attention read, computed explicitly")
    c.matrix(
        145,
        210,
        [["0", "2"], ["ln 3", "4"], ["masked", "99"]],
        118,
        53,
        ["key A", "key B", "padding"],
        ["logit", "value"],
        [[WHITE] * 2, [WHITE] * 2, ["#f6e8eb"] * 2],
    )
    c.arrow([(410, 289), (475, 289)], BLUE)
    for y, value, color, name in (
        (219, 0.25, BLUE, "A: 0.25"),
        (289, 0.75, TEAL, "B: 0.75"),
        (359, 0, RED, "padding: 0"),
    ):
        c.bar(496, y, value, 1, color, name, 220, 24)
    c.text(608, 409, "softmax over visible keys", 17, MUTED, anchor="middle")
    c.arrow([(747, 289), (805, 289)], TEAL)
    c.text(834, 255, "0.25 × 2 + 0.75 × 4", 22, INK, True)
    c.text(965, 316, "read = 3.5", 32, TEAL, True, "middle")
    c.text(832, 365, "The masked 99 contributes zero.", 17, RED)
    c.line([(45, 442), (1154, 442)], GRID)
    c.section(43, 472, "2", "Residual paths depend on the attention block")
    for y, title, self_attention, color in (
        (548, "Scene / future self-attention", True, BLUE),
        (644, "Released cross-attention", False, PURPLE),
    ):
        c.text(47, y, title, 17, color, True)
        c.node(365, y - 31, 111, 44, "Read", color)
        c.arrow([(477, y - 9), (515, y - 9)], color)
        if self_attention:
            _plus(c, 534, y - 9, color)
            c.arrow([(406, y - 49), (534, y - 49), (534, y - 27)], color)
            c.text(469, y - 58, "query q", 15, color, anchor="middle")
        else:
            c.text(535, y - 37, "no +q", 16, color, True, "middle")
        c.arrow([(552, y - 9), (591, y - 9)], color)
        c.node(592, y - 31, 102, 44, "Norm", color)
        c.arrow([(694, y - 9), (737, y - 9)], color)
        c.node(738, y - 31, 91, 44, "FFN", color)
        c.arrow([(829, y - 9), (869, y - 9)], color)
        _plus(c, 887, y - 9, color)
        c.arrow([(710, y - 9), (710, y + 32), (887, y + 32), (887, y + 9)], color)
        c.arrow([(905, y - 9), (949, y - 9)], color)
        c.node(950, y - 31, 102, 44, "Norm", color)
        c.arrow([(1052, y - 9), (1126, y - 9)], color)


def _initial_query(c):
    c.section(43, 142, "1", "Add the scene actor token, agent identity and shared mode identity")
    c.text(70, 207, "Scene actor", 18, BLUE, True)
    c.matrix(73, 228, [["1", "2"]], 63, 46, colors=[["#eaf2fb"] * 2])
    c.text(239, 258, "+", 28, MUTED)
    c.text(294, 207, "Mode m", 18, ORANGE, True)
    c.matrix(281, 228, [["0.5", "0"]], 65, 46, colors=[["#f9efdf"] * 2])
    c.text(447, 258, "+", 28, MUTED)
    c.text(505, 207, "Agent A", 18, TEAL, True)
    c.matrix(489, 228, [["0", "−0.5"]], 70, 46, colors=[["#e6f2f1"] * 2])
    c.arrow([(654, 252), (725, 252)], INK)
    c.matrix(750, 228, [["1.5", "1.5"]], 80, 46, colors=[["#efeaf6"] * 2])
    c.text(831, 207, "q[A,m]", 19, PURPLE, True, "middle")
    c.text(955, 252, "Toy D = 2", 18, MUTED)
    c.section(43, 354, "2", "One query per agent × mode")
    c.matrix(
        170,
        429,
        [["q A,0", "q A,1", "q A,2"], ["q B,0", "q B,1", "q B,2"]],
        122,
        65,
        ["agent A", "agent B"],
        ["mode 0", "mode 1", "mode 2"],
        [["#eaf2fb", "#f9efdf", "#efeaf6"]] * 2,
    )
    c.text(171, 599, "The mode column is shared across agents.", 17, MUTED)
    c.arrow([(567, 492), (647, 492)], PURPLE)
    c.node(648, 456, 206, 72, "Cross-attention", PURPLE)
    _token_stack(c, 700, 356, 4, TEAL)
    c.arrow([(744, 394), (744, 455)], TEAL)
    c.text(835, 383, "scene K,V", 17, TEAL)
    c.arrow([(855, 491), (925, 491)], PURPLE)
    c.line([(925, 420), (925, 566)], PURPLE)
    c.arrow([(925, 420), (970, 420)], BLUE)
    c.arrow([(925, 566), (970, 566)], ORANGE)
    c.node(970, 394, 175, 54, "Gaussian head", BLUE, size=17)
    c.node(970, 540, 175, 54, "Score head", ORANGE)
    c.text(967, 488, "[P, M, T, 4]", 18, BLUE)
    c.text(967, 634, "[P, M] logits", 18, ORANGE)
    c.text(
        62,
        685,
        "Full shape [B, 2, 6, 256]. No previous future and no mode-wise self-attention at level 0.",
        17,
        MUTED,
    )


def _gaussian_head(c):
    c.section(43, 142, "1", "Predict offsets from the observed current position")
    c.rect(44, 169, 658, 455, WHITE, GRID)
    ox, oy, unit = 115, 558, 70
    for i in range(6):
        c.line([(ox + i * unit, 206), (ox + i * unit, oy)], GRID, 1)
        c.text(ox + i * unit, oy + 29, 10 + i, 16, MUTED, anchor="middle")
    for i in range(5):
        c.line([(ox, oy - i * unit), (622, oy - i * unit)], GRID, 1)
        c.text(ox - 19, oy - i * unit + 6, i, 16, MUTED, anchor="end")
    c.arrow([(ox, oy), (641, oy)], MUTED)
    c.arrow([(ox, oy), (ox, 194)], MUTED)
    c.text(636, 597, "x (m)", 16, MUTED, anchor="end")
    c.text(133, 196, "y (m)", 16, MUTED)
    current, mean = (115, 418), (325, 348)
    c.ellipse(*mean, 70, 140, "#edf5fa", BLUE, 2)
    c.ellipse(*mean, 35, 70, "#e2edf7", BLUE, 2)
    c.arrow([current, mean], ORANGE, 3)
    _vehicle(c, *current, TEAL)
    c.ellipse(*mean, 6, 6, BLUE, BLUE)
    c.text(147, 459, "current (10, 2)", 18, TEAL, True)
    c.text(346, 348, "μ = (13, 3)", 21, BLUE, True)
    c.text(154, 367, "offset (3, 1)", 18, ORANGE, True)
    c.line([(mean[0], mean[1]), (mean[0] + 70, mean[1])], BLUE, 2)
    c.line([(mean[0], mean[1]), (mean[0], mean[1] + 140)], BLUE, 2)
    c.text(365, 383, "σx = 1", 17, BLUE)
    c.text(340, 480, "σy = 2", 17, BLUE)
    c.section(745, 142, "2", "Separate means, scale and score")
    c.node(759, 194, 375, 55, "μ = current xy + head offset", BLUE, size=19)
    c.text(763, 290, "log σ = (0, ln 2)", 21, PURPLE, True)
    c.arrow([(946, 307), (946, 347)], PURPLE)
    c.text(944, 381, "σ = exp(log σ) = (1, 2)", 21, PURPLE, True, "middle")
    c.text(768, 428, "Diagonal covariance: axes stay independent.", 16, MUTED)
    for y, value, color, label in (
        (480, 0.1, BLUE, "mode 0: 0.1"),
        (541, 0.8, ORANGE, "mode 1: 0.8"),
        (602, 0.1, PURPLE, "mode 2: 0.1"),
    ):
        c.bar(777, y, value, 1, color, label, 330, 20)
    c.text(777, 665, "Scores become probabilities across modes.", 17, MUTED)
    c.text(
        60,
        673,
        "Offsets are direct, not cumulative. Log standard deviation is not variance.",
        17,
        INK,
        True,
    )


def _future_encoding(c):
    c.section(43, 142, "1", "Build kinematics from previous predicted xy")
    c.arrow([(79, 255), (289, 255)], MUTED)
    _vehicle(c, 101, 255, TEAL)
    c.ellipse(265, 255, 7, 7, BLUE, BLUE)
    c.text(74, 311, "current (0, 0)", 17, TEAL)
    c.text(231, 311, "next (1, 0) m", 17, BLUE)
    c.text(99, 215, "Δxy = (1, 0) m; Δt = 0.1 s", 19, INK, True)
    c.arrow([(340, 255), (408, 255)], INK)
    c.text(438, 218, "velocity = Δxy / Δt = (10, 0) m/s", 21, BLUE, True)
    c.text(438, 262, "heading = atan2(0, 1) = 0 rad", 21, TEAL, True)
    c.text(438, 307, "size = (4, 2, 1.5) m from current state", 18, MUTED)
    c.text(872, 219, "Released heading uses", 16, MUTED)
    c.text(872, 247, "clamp(dx, min=0.001)", 16, MUTED)
    c.text(872, 277, "before atan2.", 16, MUTED)
    c.section(43, 381, "2", "Detach the eight kinematic inputs, then learn future features")
    c.matrix(
        65,
        448,
        [["x", "y", "θ", "vx", "vy", "L", "W", "H"], ["1", "0", "0", "10", "0", "4", "2", "1.5"]],
        54,
        44,
        colors=[["#eaf2fb"] * 5 + ["#e6f2f1"] * 3, [WHITE] * 8],
        size=17,
    )
    c.arrow([(498, 492), (546, 492)], BLUE)
    c.rect(546, 425, 12, 157, RED, RED, radius=0)
    c.text(552, 414, "detach", 19, RED, True, "middle")
    c.arrow([(558, 492), (601, 492)], BLUE)
    c.node(601, 463, 135, 58, "8 → 64 → D", BLUE, size=19)
    c.text(665, 558, "shared MLP", 17, BLUE, anchor="middle")
    c.arrow([(736, 492), (758, 492), (758, 411), (849, 411), (849, 428)], BLUE)
    c.matrix(
        792,
        429,
        [[".2", ".8"], [".9", ".3"], [".4", ".6"]],
        58,
        43,
        ["t1", "t2", "…"],
        colors=[[WHITE, "#e6f2f1"], ["#eaf2fb", WHITE], [WHITE] * 2],
        size=17,
    )
    c.text(849, 595, "max over time", 17, TEAL, anchor="middle")
    c.arrow([(909, 492), (948, 492)], TEAL)
    _plus(c, 968, 492, PURPLE)
    c.node(913, 370, 113, 47, "Type emb.", PURPLE, size=17)
    c.arrow([(969, 417), (969, 474)], PURPLE)
    c.arrow([(986, 492), (1030, 492)], PURPLE)
    _token_stack(c, 1040, 478, 3, PURPLE)
    c.text(1068, 572, "[P, M, D]", 18, PURPLE, True, "middle")
    c.arrow([(1046, 634), (667, 634), (667, 557)], RED, dash=True)
    c.text(876, 665, "MLP parameters receive gradients", 17, RED, anchor="middle")
    c.line([(540, 615), (560, 635)], RED, 3)
    c.line([(560, 615), (540, 635)], RED, 3)
    c.text(65, 669, "No gradient to xy through this path.", 18, RED, True)


def _future_interaction(c):
    c.section(43, 142, "1", "Probability weighting retains the released 1/M factor")
    c.matrix(
        142,
        217,
        [["2", "4"], ["0.25", "0.75"]],
        108,
        57,
        ["feature", "softmax"],
        ["mode 0", "mode 1"],
        [["#eaf2fb", "#efeaf6"], [WHITE] * 2],
        22,
    )
    c.arrow([(388, 274), (449, 274)], BLUE)
    c.text(481, 207, "element-wise ×", 18, MUTED)
    c.matrix(483, 244, [["0.5", "3.0"]], 102, 61, colors=[["#eaf2fb", "#efeaf6"]], size=25)
    c.arrow([(710, 274), (773, 274)], BLUE)
    c.text(805, 228, "mean over M = 2", 20, INK, True)
    c.text(946, 289, "(0.5 + 3) / 2 = 1.75", 24, TEAL, True, "middle")
    c.text(800, 337, "A normalized sum would be 3.5.", 18, MUTED)
    c.line([(46, 390), (1154, 390)], GRID)
    c.section(43, 436, "2", "Self-attention mixes future tokens across agents")
    c.node(87, 490, 191, 55, "A: pooled future", BLUE, size=18)
    c.node(87, 611, 191, 55, "B: pooled future", TEAL, size=18)
    c.node(430, 477, 270, 192, "Future self-attention", PURPLE, size=19)
    for sy in (518, 639):
        c.arrow([(279, sy), (430, 518)], BLUE if sy == 518 else TEAL)
        c.arrow([(279, sy), (430, 639)], BLUE if sy == 518 else TEAL)
    c.arrow([(700, 518), (799, 518)], PURPLE)
    c.arrow([(700, 639), (799, 639)], PURPLE)
    c.node(800, 491, 326, 54, "Mixed A future token", BLUE, size=19)
    c.node(800, 612, 326, 54, "Mixed B future token", TEAL, size=19)
    c.text(958, 583, "Includes residual + norm + FFN", 17, MUTED, anchor="middle")
    c.text(
        81,
        701,
        "The future MLP is shared across levels; each level has its own interaction attention.",
        17,
        MUTED,
    )


def _reasoning_mask(c):
    c.section(43, 142, "1", "Mix future agents before applying the cross-attention key mask")
    c.node(53, 192, 163, 51, "A future", BLUE)
    c.node(53, 305, 163, 51, "B future", TEAL)
    c.node(343, 207, 177, 138, "Self-attention", PURPLE, size=18)
    for sy, color in ((218, BLUE), (331, TEAL)):
        c.arrow([(217, sy), (343, 236)], color)
        c.arrow([(217, sy), (343, 316)], color)
    c.arrow([(520, 238), (597, 238)], PURPLE)
    c.arrow([(520, 315), (597, 315)], PURPLE)
    contexts = [
        (212, "mixed A", RED, "HIDDEN"),
        (290, "mixed B", TEAL, "VISIBLE"),
        (368, "scene", BLUE, "VISIBLE"),
        (446, "padding", RED, "HIDDEN"),
    ]
    for y, name, color, flag in contexts:
        c.node(598, y, 174, 49, name, color, PALE if flag == "HIDDEN" else WHITE)
        c.text(789, y + 31, flag, 15, color, True)
        if flag == "VISIBLE":
            c.arrow([(882, y + 24), (942, y + 24), (942, 369), (974, 369)], color)
        else:
            c.line([(880, y + 24), (920, y + 24)], RED, 2, True)
            c.line([(923, y + 13), (923, y + 35)], RED, 3)
    c.node(974, 330, 178, 78, "Cross-attention", PURPLE, size=17)
    c.text(595, 541, "Agent A reads B and valid scene keys.", 19, INK, True)
    c.node(61, 553, 218, 56, "Previous content", BLUE, size=18)
    c.node(61, 636, 218, 52, "Own multi-future", TEAL, size=18)
    _plus(c, 340, 582, PURPLE)
    c.arrow([(279, 581), (322, 581)], BLUE)
    c.arrow([(279, 662), (340, 662), (340, 600)], TEAL)
    c.arrow([(358, 582), (1064, 582), (1064, 408)], PURPLE)
    c.text(646, 613, "query retains own future feature", 18, PURPLE, True, "middle")
    c.arrow([(140, 192), (140, 162), (558, 162), (558, 315), (598, 315)], ORANGE, 2, True)
    c.text(573, 183, "A can already influence mixed B", 16, ORANGE, True, "middle")
    c.text(592, 675, "The mask is not total causal isolation.", 22, ORANGE, True)


def _full_assembly(c):
    c.section(43, 142, "1", "Encode observations once")
    _token_stack(c, 83, 216, 5, BLUE, "34 actors")
    _token_stack(c, 242, 216, 5, TEAL, "local map")
    c.arrow([(140, 294), (140, 332), (214, 332), (214, 366)], BLUE)
    c.arrow([(291, 294), (291, 332), (214, 332)], TEAL)
    c.node(71, 366, 287, 66, "Scene Transformer × E6", PURPLE, size=19)
    c.arrow([(214, 432), (214, 490)], PURPLE)
    c.node(71, 490, 287, 79, "[B, 2, 114, 256]", PURPLE, size=23)
    c.text(76, 621, "2 target-specific map contexts", 16, MUTED)
    c.text(76, 655, "Same observed actors; local maps", 16, MUTED)
    c.section(405, 142, "2", "Initial prediction + three interaction levels")
    for i, x in enumerate((412, 599, 786, 973)):
        color = BLUE if i == 0 else TEAL
        c.node(x, 237, 151, 74, f"Level {i}", color, size=22)
        c.text(x + 75, 347, "xy, log σ, scores", 15, color, anchor="middle")
        if i < 3:
            c.arrow([(x + 151, 274), (x + 187, 274)], color)
        c.arrow([(x + 75, 311), (x + 75, 398)], color)
        c.rect(x + 11, 398, 128, 57, WHITE, color, radius=5)
        for j in range(4):
            c.line([(x + 26, 411 + j * 10), (x + 120, 411 + j * 10)], color, 2)
    c.line([(358, 529), (390, 529), (390, 194), (1048, 194)], PURPLE)
    for x in (487, 674, 861, 1048):
        c.arrow([(x, 194), (x, 237)], PURPLE)
    c.text(758, 181, "scene context reused at every level", 16, PURPLE, anchor="middle")
    c.node(
        411,
        518,
        714,
        61,
        "Between levels: shared future MLP → pool → interaction attention",
        ORANGE,
        size=17,
    )
    c.text(411, 624, "Keep all four stages", 20, INK, True)
    c.text(411, 662, "Trajectories [4, B, 2, 6, 80, 4]    Scores [4, B, 2, 6]", 21, PURPLE, True)
    c.text(411, 697, "K6 is the separately named paper-recipe reconstruction.", 16, MUTED)


def _joint_objective(c):
    c.section(43, 142, "1", "Choose one mode using both agents' valid target distances")
    c.matrix(
        176,
        214,
        [["0", "10", "20"], ["2", "2", "8"]],
        140,
        64,
        ["mode 0", "mode 1"],
        ["A error (m)", "B error (m)", "joint cost"],
        [[WHITE] * 3, ["#e6f2f1"] * 3],
        size=25,
    )
    c.arrow([(630, 279), (706, 279)], TEAL)
    c.node(724, 227, 397, 90, "Winner: mode 1 for A and B", TEAL, size=22)
    c.text(650, 357, "Constant errors: mean + 3, 5, 8 s terms.", 18, MUTED)
    c.line([(46, 394), (1154, 394)], GRID)
    c.section(43, 439, "2", "Regress the winner: constant-free NLL")
    c.ellipse(174, 560, 85, 85, "#edf5fa", BLUE)
    c.ellipse(174, 560, 43, 43, "#e2edf7", BLUE)
    c.ellipse(174, 560, 5, 5, BLUE, BLUE)
    c.ellipse(260, 560, 6, 6, RED, RED)
    c.arrow([(174, 560), (260, 560)], RED)
    c.text(79, 677, "dx = 2, dy = 0; σ = 1", 17, MUTED)
    c.text(305, 512, "NLL = log σx + log σy", 21, BLUE, True)
    c.text(305, 548, "+ ½ [(dx/σx)² + (dy/σy)²]", 21, BLUE, True)
    c.text(305, 600, "Toy NLL = 0 + ½ · 2² = 2", 21, INK, True)
    c.text(305, 641, "Mean + 3, 5, 8 s terms → 8", 18, MUTED)
    c.line([(730, 448), (730, 692)], GRID)
    c.text(762, 466, "Score supervision at every level", 18, PURPLE, True)
    c.text(762, 512, "joint logits = logits A + logits B", 18, PURPLE)
    c.text(762, 548, "2 × cross-entropy; smoothing 0.2", 18, MUTED)
    c.text(762, 606, "Planning only, at levels k ≥ 1:", 18, ORANGE, True)
    c.text(762, 643, "+ 0.1 × interaction potential", 18, ORANGE)
    c.text(762, 678, "At d = 1 m: 1 / (1 + 1) = 0.5", 17, MUTED)


def _optimizer_update(c):
    c.section(43, 142, "1", "A visible parameter update")
    c.rect(45, 169, 450, 337, WHITE, GRID)
    ox, oy = 100, 457
    c.arrow([(ox, oy), (459, oy)], MUTED)
    c.arrow([(ox, oy), (ox, 192)], MUTED)
    points = [(ox + i * 13, oy - 0.5 * (i / 10) ** 2 * 80) for i in range(26)]
    c.line(points, BLUE, 3)
    old, new = (ox + 260, oy - 160), (ox + 247, oy - 0.5 * 1.9**2 * 80)
    c.line([(old[0] - 70, old[1] + 86), (old[0] + 60, old[1] - 74)], RED, 2)
    c.ellipse(*old, 7, 7, RED, RED)
    c.ellipse(*new, 6, 6, TEAL, TEAL)
    c.text(141, 220, "L = ½w²", 23, BLUE, True)
    c.text(147, 264, "dL/dw = w = 2", 19, RED)
    c.text(257, 441, "1.9 ← 2.0", 20, TEAL, True)
    c.text(442, 485, "w", 18, MUTED)
    c.text(65, 549, "First AdamW step (toy: lr = 0.1, decay = 0)", 17, MUTED)
    c.text(65, 588, "m̂ = 2     v̂ = 4", 24, INK, True)
    c.text(65, 630, "w_new = 2 − 0.1 · 2 / √4 = 1.9", 23, TEAL, True)
    c.section(542, 142, "2", "Actual training step")
    steps = [
        (181, "Zero grads → forward (optional autocast)", BLUE),
        (260, "Sample-weighted FP32 loss → backward", RED),
        (339, "Accumulate microbatch gradients", PURPLE),
        (418, "Unscale → clip gradient norm at 5", ORANGE),
        (497, "AdamW step", TEAL),
    ]
    for i, (y, title, color) in enumerate(steps):
        c.node(564, y, 564, 52, title, color, size=20)
        if i < len(steps) - 1:
            c.arrow([(847, y + 52), (847, y + 79)], color)
    c.rect(565, 592, 563, 80, PALE, PALE)
    c.text(585, 624, "Final partial accumulation group is smaller.", 18, INK, True)
    c.text(585, 654, "Normalize by its actual sample count.", 18, MUTED)
    c.text(
        66, 695, "Illustrative parameter arithmetic; no training benchmark is implied.", 17, MUTED
    )


def _decoding_metrics(c):
    c.section(43, 142, "1", "Select from scores at inference")
    for x, value, color, name in (
        (65, 0.1, BLUE, "mode 0"),
        (214, 0.8, ORANGE, "mode 1"),
        (363, 0.1, PURPLE, "mode 2"),
    ):
        c.rect(x, 182, 97, 150, PALE, PALE, radius=4)
        c.rect(x, 332 - value * 150, 97, value * 150, color, color, radius=4)
        c.text(x + 48, 363, name, 17, color, True, "middle")
        c.text(x + 48, 395, value, 20, INK, True, "middle")
    c.text(62, 438, "Joint logits sum across agents.", 19, INK, True)
    c.text(62, 470, "Joint mode 1 selects both agents.", 18, ORANGE, True)
    c.text(62, 508, "Planning uses each agent's argmax.", 17, MUTED)
    c.section(545, 142, "2", "Diagnostic errors need valid labels")
    c.line([(628, 245), (834, 245), (1040, 245)], TEAL, 2)
    for x, error in ((628, 1), (834, 2), (1040, 3)):
        c.ellipse(x, 245, 6, 6, TEAL, TEAL)
        c.ellipse(x, 245 + error * 34, 7, 7, BLUE, BLUE)
        c.line([(x, 245), (x, 245 + error * 34)], RED, 2, True)
        c.text(x + 18, 260 + error * 16, f"{error} m", 18, RED, True)
    c.line([(628, 279), (834, 313), (1040, 347)], BLUE, 3)
    c.text(586, 401, "ADE = (1 + 2 + 3) / 3 = 2 m", 22, BLUE, True)
    c.text(586, 444, "FDE = final valid error = 3 m", 22, TEAL, True)
    c.text(587, 486, "Targets never choose the inference mode.", 18, MUTED)
    c.line([(46, 543), (1153, 543)], GRID)
    c.section(43, 586, "3", "Official adapter boundary: 80 steps at 10 Hz → 16 steps at 2 Hz")
    c.line([(82, 636), (1110, 636)], MUTED, 2)
    for i in range(80):
        x = 82 + i * 13
        sampled = i % 5 == 4
        c.line(
            [(x, 630 if sampled else 633), (x, 650 if sampled else 639)],
            BLUE if sampled else GRID,
            2 if sampled else 1,
        )
    for second in (3, 5, 8):
        x = 82 + (second * 10 - 1) * 13
        c.ellipse(x, 636, 6, 6, ORANGE, ORANGE)
        c.text(x, 680, f"{second} s", 17, ORANGE, True, "middle")
    c.text(
        83,
        705,
        "Use 4::5. Official minADE / minFDE / miss / mAP require the WOMD SDK and real data.",
        17,
        MUTED,
    )


def _checkpoint_resume(c):
    c.section(43, 142, "1", "A coherent snapshot at a complete epoch boundary")
    c.line([(82, 205), (1114, 205)], MUTED, 3)
    for x, title, color in (
        (150, "Epoch 5", BLUE),
        (469, "Epoch 6", TEAL),
        (1082, "Epoch 7", BLUE),
    ):
        c.ellipse(x, 205, 8, 8, color, color)
        c.text(x, 177, title, 19, color, True, "middle")
    c.line([(660, 187), (660, 226)], RED, 3)
    c.text(660, 262, "save boundary", 18, RED, True, "middle")
    c.section(43, 327, "2", "Publish atomically")
    states = [
        (62, 364, "Model", BLUE),
        (205, 364, "AdamW", BLUE),
        (62, 427, "Scheduler", TEAL),
        (205, 427, "Scaler", TEAL),
        (62, 490, "RNG", PURPLE),
        (205, 490, "Shuffle", PURPLE),
        (62, 553, "Epoch / step", ORANGE),
        (205, 553, "Config / ID", ORANGE),
    ]
    for x, y, title, color in states:
        c.node(x, y, 130, 44, title, color, size=17)
    c.line([(352, 387), (374, 387), (374, 576), (352, 576)], INK)
    c.arrow([(374, 480), (435, 480)], INK)
    c.node(435, 432, 170, 92, "latest.tmp", ORANGE, size=21)
    c.text(518, 565, "write → flush → fsync", 17, ORANGE, anchor="middle")
    c.arrow([(606, 480), (695, 480)], TEAL, 3)
    c.text(652, 414, "atomic", 18, TEAL, True, "middle")
    c.text(652, 439, "rename", 18, TEAL, True, "middle")
    c.node(696, 432, 170, 92, "latest.pt", TEAL, size=22)
    c.arrow([(866, 480), (933, 480)], TEAL)
    c.node(934, 432, 214, 92, "Resume epoch 7", BLUE, size=20)
    c.text(935, 566, "Construct → restore state", 16, MUTED)
    c.text(935, 593, "Restore RNG last", 18, PURPLE, True)
    c.rect(61, 640, 1086, 56, PALE, PALE)
    c.text(
        83,
        675,
        "Interrupted temp write leaves the old checkpoint intact. Recipe changes are rejected; no mid-epoch claim.",
        17,
        INK,
    )


def _tracking_eta(c):
    c.section(43, 142, "1", "Distinguish elapsed wall time from active work")
    c.text(61, 191, "Wall time = 100 s", 20, INK, True)
    c.rect(62, 216, 1050, 56, PALE, PALE, radius=5)
    c.rect(62, 216, 420, 56, BLUE, BLUE, radius=5)
    c.rect(482, 216, 420, 56, GRID, GRID, radius=0)
    c.rect(902, 216, 210, 56, TEAL, TEAL, radius=5)
    c.text(271, 252, "prior active: 40 s", 21, WHITE, True, "middle")
    c.text(692, 252, "inactive: 40 s", 21, MUTED, True, "middle")
    c.text(1007, 251, "new: 20 s", 20, WHITE, True, "middle")
    c.text(61, 312, "Active total = 40 + 20 = 60 s", 21, BLUE, True)
    c.text(691, 313, "New session: 2 completed epochs / 20 s", 19, TEAL, True)
    c.section(43, 387, "2", "Estimate only the remaining work from the resumed session's rate")
    for i in range(10):
        color = BLUE if i < 4 else TEAL if i < 6 else MUTED
        c.node(64 + i * 108, 429, 89, 65, str(i + 1), color, color if i < 6 else WHITE, size=23)
        # Numeric labels on completed blocks need the same foreground in both formats.
        if i < 6:
            c.text(108 + i * 108, 469, str(i + 1), 23, WHITE, True, "middle")
    c.text(64, 534, "Completed: 6 / 10 = 60%", 22, INK, True)
    c.text(716, 534, "Remaining: 10 − 6 = 4 epochs", 22, MUTED, True)
    c.arrow([(424, 581), (516, 581)], TEAL)
    c.text(63, 587, "Rate = 2 / 20 = 0.1 epoch/s", 22, TEAL, True)
    c.node(539, 550, 604, 63, "Remaining time = 4 / 0.1 = 40 s", TEAL, size=26)
    c.rect(62, 649, 1082, 53, PALE, PALE)
    c.text(
        81,
        681,
        "Show timezone on expected finish; provisional before 2 epochs. Include validation and save overhead.",
        17,
        MUTED,
    )


_DRAWERS = {
    "overview": _overview,
    "scene-tensors": _scene_tensors,
    "agent-history": _agent_history,
    "lane-encoding": _lane_encoding,
    "crosswalk-encoding": _crosswalk_encoding,
    "map-segments": _map_segments,
    "scene-attention": _scene_attention,
    "initial-query": _initial_query,
    "gaussian-head": _gaussian_head,
    "future-encoding": _future_encoding,
    "future-interaction": _future_interaction,
    "reasoning-mask": _reasoning_mask,
    "full-assembly": _full_assembly,
    "joint-objective": _joint_objective,
    "optimizer-update": _optimizer_update,
    "decoding-metrics": _decoding_metrics,
    "checkpoint-resume": _checkpoint_resume,
    "tracking-eta": _tracking_eta,
}


def draw_illustration(spec, destination):
    """Draw one FIGURES spec to identically composed editable SVG and PNG files."""
    identifier, title, subtitle, *rest = spec
    source = rest[-1]
    c = Canvas()
    c.text(43, 49, title, 29, INK, True)
    c.text(44, 82, subtitle, 16, MUTED)
    c.line([(44, 103), (1155, 103)], GRID, 1)
    _DRAWERS[identifier](c)
    c.line([(44, 720), (1155, 720)], GRID, 1)
    evidence = (
        "Conceptual architecture" if identifier == "overview" else "Illustrative values · untrained"
    )
    c.text(44, 743, evidence, 13, MUTED)
    c.text(1154, 743, f"Local source: {source}   ·   {identifier}", 13, MUTED, anchor="end")
    c.finish(Path(destination), identifier)

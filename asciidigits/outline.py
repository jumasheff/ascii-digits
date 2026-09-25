"""Glyph outlines from TTF files, filled by a small numpy rasterizer.

Fonts are read with fontTools, which returns the designer's outlines without
hinting. The filling is plain integer and float arithmetic in numpy, so a
digit renders to exactly the same pixels in CPython on any OS and in
Pyodide. (Pillow was tried first: its bundled FreeType versions differ
between platforms and rendered hinted fonts differently.)
"""

import math
from functools import lru_cache

import numpy as np
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

CURVE_STEPS = 8         # line segments per Bezier curve


class _FlattenPen(BasePen):
    """Collects each contour as a list of points, curves flattened to lines."""

    def __init__(self, glyph_set):
        super().__init__(glyph_set)
        self.contours, self._current = [], []

    def _moveTo(self, pt):
        self._current = [pt]

    def _lineTo(self, pt):
        self._current.append(pt)

    def _qCurveToOne(self, pt1, pt2):
        (x0, y0), (x1, y1), (x2, y2) = self._current[-1], pt1, pt2
        for i in range(1, CURVE_STEPS + 1):
            t = i / CURVE_STEPS
            a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
            self._current.append((a * x0 + b * x1 + c * x2, a * y0 + b * y1 + c * y2))

    def _curveToOne(self, pt1, pt2, pt3):
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = self._current[-1], pt1, pt2, pt3
        for i in range(1, CURVE_STEPS + 1):
            t = i / CURVE_STEPS
            a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
            self._current.append((a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3))

    def _closePath(self):
        if len(self._current) > 2:
            self.contours.append(np.array(self._current, dtype=np.float64))
        self._current = []

    _endPath = _closePath


@lru_cache(maxsize=None)
def _font(path: str):
    font = TTFont(path)
    return font, font.getGlyphSet(), font.getBestCmap()


@lru_cache(maxsize=None)
def glyph(path: str, char: str) -> tuple:
    """(contours in font units with y up, advance width, units per em, ascent, descent)."""
    font, glyph_set, cmap = _font(path)
    name = cmap[ord(char)]
    pen = _FlattenPen(glyph_set)
    glyph_set[name].draw(pen)
    hhea = font["hhea"]
    return tuple(pen.contours), glyph_set[name].width, font["head"].unitsPerEm, hhea.ascent, hhea.descent


def rotation(angle: float) -> tuple:
    """(cos, sin) of an angle in degrees, rounded so every platform's libm agrees."""
    radians = math.radians(angle)
    return round(math.cos(radians), 12), round(math.sin(radians), 12)


def fill(contours: list, width: int, height: int) -> np.ndarray:
    """Boolean (height, width) image: pixel centres inside the outline, nonzero winding rule."""
    if not contours:
        return np.zeros((height, width), dtype=bool)
    starts = np.concatenate(contours)
    ends = np.concatenate([np.roll(c, -1, axis=0) for c in contours])
    x0, y0, x1, y1 = starts[:, 0], starts[:, 1], ends[:, 0], ends[:, 1]
    keep = y0 != y1
    x0, y0, x1, y1 = x0[keep], y0[keep], x1[keep], y1[keep]
    direction = np.where(y1 > y0, 1, -1).astype(np.int32)
    # Index arrays use np.intp: int64 in CPython, int32 in Pyodide (32-bit WebAssembly).
    first = np.clip(np.ceil(np.minimum(y0, y1) - 0.5), 0, height).astype(np.intp)
    last = np.clip(np.ceil(np.maximum(y0, y1) - 0.5), 0, height).astype(np.intp)
    counts = np.maximum(last - first, 0)
    edge = np.repeat(np.arange(len(x0), dtype=np.intp), counts)
    offset = np.arange(counts.sum(), dtype=np.intp) - np.repeat(np.cumsum(counts) - counts, counts)
    row = first[edge] + offset
    centre_y = row + 0.5
    cross_x = x0[edge] + (centre_y - y0[edge]) * (x1[edge] - x0[edge]) / (y1[edge] - y0[edge])
    col = np.clip(np.ceil(cross_x - 0.5), 0, width).astype(np.intp)
    winding = np.zeros((height, width + 1), dtype=np.int32)
    np.add.at(winding, (row, col), direction[edge])
    return np.cumsum(winding[:, :width], axis=1) != 0


def dilate(image: np.ndarray, radius: int) -> np.ndarray:
    """Grow the ink by `radius` pixels in every direction (a square brush)."""
    out = image.copy()
    for axis in (0, 1):
        grown = out.copy()
        for shift in range(1, radius + 1):
            forward = np.zeros_like(out)
            backward = np.zeros_like(out)
            if axis == 0:
                forward[shift:], backward[:-shift] = out[:-shift], out[shift:]
            else:
                forward[:, shift:], backward[:, :-shift] = out[:, :-shift], out[:, shift:]
            grown |= forward | backward
        out = grown
    return out

"""TTF digit -> grayscale bitmap -> ASCII rows, by shape matching.

Each character cell is SUB_W x SUB_H sub-pixels (cells are about twice as
tall as wide, like terminal characters). A cell becomes the character whose
own shape, drawn from the bundled monospace font, is closest to that piece
of the glyph. Glyphs are filled by outline.py and distances are computed in
integers, so the result is exactly the same on every platform.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import outline

SUB_W, SUB_H = 6, 12
SUPERSAMPLE = 4                     # fill at 4x, then average 4x4 blocks: smooth edges
CHARS = " _-|/\\()<>.,'`^~=+:;!lI[]{}7LJVv#"
SINGLE_SYMBOLS = "#@$%&8*+="
RAMP = " .:-=+*#%@"
BLANK_LIMIT = int(0.06 * 255 * SUB_W * SUB_H)   # cells with less ink than this stay blank
MASK_FONT = "JetBrainsMono.ttf"


@dataclass(frozen=True)
class CharMasks:
    chars: str
    masks: np.ndarray      # (len(chars), SUB_W * SUB_H) int64, 0..255
    norms: np.ndarray      # (len(chars),) int64, sum of squares of each mask


def downsample(image: np.ndarray, factor: int) -> np.ndarray:
    """Boolean image -> uint8, averaging factor x factor blocks (integer arithmetic)."""
    height, width = image.shape
    blocks = image.reshape(height // factor, factor, width // factor, factor).sum(axis=(1, 3))
    return (blocks * 255 // (factor * factor)).astype(np.uint8)


@lru_cache(maxsize=None)
def build_char_masks(mono_font: Path) -> CharMasks:
    """Each character drawn in one cell: the monospace font's line (ascent to descent) fills the cell's height."""
    box_w, box_h = SUB_W * SUPERSAMPLE, SUB_H * SUPERSAMPLE
    rows = []
    for ch in CHARS:
        if ch == " ":
            rows.append(np.zeros(SUB_W * SUB_H, dtype=np.int64))
            continue
        contours, advance, _, ascent, descent = outline.glyph(str(mono_font), ch)
        scale = box_h / (ascent - descent)
        left = (box_w - advance * scale) / 2
        placed = [np.column_stack((left + c[:, 0] * scale, (ascent - c[:, 1]) * scale)) for c in contours]
        image = outline.dilate(outline.fill(placed, box_w, box_h), 1)
        rows.append(downsample(image, SUPERSAMPLE).astype(np.int64).ravel())
    masks = np.stack(rows)
    return CharMasks(CHARS, masks, (masks ** 2).sum(axis=1))


def render_ttf(digit: str, font_path: Path, cols: int, rows: int, *, fill: float = 0.85,
               dx: float = 0.0, dy: float = 0.0, angle: float = 0.0, thicken: float = 0.0) -> np.ndarray:
    """The digit as a (rows*SUB_H, cols*SUB_W) uint8 array, ink = 255.

    fill: fraction of the grid the glyph fills. dx, dy: shift as a fraction of
    the grid. angle: degrees counter-clockwise. thicken: extra stroke width,
    in cell widths (for hairline fonts).
    """
    width, height = cols * SUB_W * SUPERSAMPLE, rows * SUB_H * SUPERSAMPLE
    contours = outline.glyph(str(font_path), digit)[0]
    points = np.concatenate(contours)
    low, high = points.min(axis=0), points.max(axis=0)
    centre = (low + high) / 2
    scale = min(fill * width / (high[0] - low[0]), fill * height / (high[1] - low[1]))
    cos, sin = outline.rotation(angle)
    target_x, target_y = width / 2 + dx * width, height / 2 + dy * height
    placed = []
    for contour in contours:
        u, v = (contour[:, 0] - centre[0]) * scale, (contour[:, 1] - centre[1]) * scale
        placed.append(np.column_stack((target_x + u * cos - v * sin, target_y - (u * sin + v * cos))))
    image = outline.fill(placed, width, height)
    if thicken > 0:
        image = outline.dilate(image, round(thicken * SUB_W * SUPERSAMPLE / 2))
    return downsample(image, SUPERSAMPLE)


def bitmap_to_ascii(bitmap: np.ndarray, cols: int, rows: int, masks: CharMasks,
                    mode: str = "symbols", symbol: str = "#") -> list:
    """Rows of text, one character per cell.

    mode "symbols": shape-matched characters. "single": every inked cell is
    `symbol`. "ramp": a density ramp from light to dark.
    """
    cells = (bitmap.reshape(rows, SUB_H, cols, SUB_W).transpose(0, 2, 1, 3)
             .reshape(rows * cols, SUB_H * SUB_W).astype(np.int64))
    ink = cells.sum(axis=1)
    if mode == "symbols":
        distances = (cells ** 2).sum(axis=1, keepdims=True) - 2 * cells @ masks.masks.T + masks.norms
        chars = np.array(list(masks.chars))[distances.argmin(axis=1)]
    elif mode == "single":
        chars = np.full(rows * cols, symbol)
    elif mode == "ramp":
        # full ink at half coverage, so strokes reach the dark end of the ramp
        levels = np.minimum(ink * 2 * (len(RAMP) - 1) // (255 * SUB_W * SUB_H), len(RAMP) - 1)
        chars = np.array(list(RAMP))[levels]
    else:
        raise ValueError(f"unknown ink mode {mode!r}")
    chars[ink < BLANK_LIMIT] = " "
    return ["".join(row) for row in chars.reshape(rows, cols)]

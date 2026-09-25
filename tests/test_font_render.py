from pathlib import Path

import numpy as np
import pytest

from asciidigits.font_render import (BLANK_LIMIT, MASK_FONT, RAMP, SINGLE_SYMBOLS, SUB_H, SUB_W,
                                     SUPERSAMPLE, bitmap_to_ascii, build_char_masks, downsample, render_ttf)
from asciidigits.outline import fill

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
BOX_W, BOX_H = SUB_W * SUPERSAMPLE, SUB_H * SUPERSAMPLE      # one cell at 4x: 24 x 48


@pytest.fixture(scope="module")
def masks():
    return build_char_masks(FONTS / MASK_FONT)


def cell(*polygons):
    """One cell: fill polygons given in 4x pixel coordinates, then average down like render_ttf."""
    return downsample(fill([np.array(p, dtype=float) for p in polygons], BOX_W, BOX_H), SUPERSAMPLE)


def thick_line(x0, y0, x1, y1, width):
    nx, ny = y0 - y1, x1 - x0
    length = (nx * nx + ny * ny) ** 0.5
    nx, ny = nx / length * width / 2, ny / length * width / 2
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


def test_each_character_matches_its_own_shape(masks):
    visible = [i for i, ch in enumerate(masks.chars) if masks.masks[i].sum() >= BLANK_LIMIT]
    assert len(visible) >= 25                       # most characters are big enough to be matched
    for i in visible:
        own = masks.masks[i].reshape(SUB_H, SUB_W).astype(np.uint8)
        assert bitmap_to_ascii(own, 1, 1, masks) == [masks.chars[i]]


@pytest.mark.parametrize("polygons, expected", [
    ([[(8, 0), (16, 0), (16, 48), (8, 48)]], "|"),               # vertical bar
    ([[(0, 40), (24, 40), (24, 48), (0, 48)]], "_"),             # bar along the bottom
    ([thick_line(2, 44, 22, 4, 6)], "/"),
    ([thick_line(2, 4, 22, 44, 6)], "\\"),
    ([[(0, 0), (24, 0), (24, 48), (0, 48)]], "#"),               # full cell
    ([], " "),                                                   # empty cell
])
def test_simple_strokes(masks, polygons, expected):
    assert bitmap_to_ascii(cell(*polygons), 1, 1, masks) == [expected]


def test_fill_uses_the_nonzero_rule_so_holes_stay_open():
    outer = [(0, 0), (20, 0), (20, 20), (0, 20)]
    hole = [(5, 5), (5, 15), (15, 15), (15, 5)]                  # opposite direction: a hole
    image = fill([np.array(outer, float), np.array(hole, float)], 20, 20)
    assert image[2, 2] and not image[10, 10]


def test_render_shape_and_ink():
    bitmap = render_ttf("8", FONTS / "ComicNeue-Regular.ttf", 16, 10)
    assert bitmap.shape == (10 * SUB_H, 16 * SUB_W) and bitmap.dtype == np.uint8
    ys, xs = np.nonzero(bitmap > 128)
    assert abs(xs.mean() - bitmap.shape[1] / 2) < bitmap.shape[1] * 0.1    # centred
    assert abs(ys.mean() - bitmap.shape[0] / 2) < bitmap.shape[0] * 0.1


def test_render_is_deterministic():
    kwargs = dict(fill=0.8, dx=0.03, dy=-0.02, angle=5.0, thicken=0.2)
    a = render_ttf("3", FONTS / "Pacifico-Regular.ttf", 16, 10, **kwargs)
    b = render_ttf("3", FONTS / "Pacifico-Regular.ttf", 16, 10, **kwargs)
    assert np.array_equal(a, b)


def test_rotation_turns_the_glyph_counter_clockwise():
    upright = render_ttf("1", FONTS / "ComicNeue-Regular.ttf", 16, 10, fill=0.9)
    tilted = render_ttf("1", FONTS / "ComicNeue-Regular.ttf", 16, 10, fill=0.9, angle=12)
    def top_minus_bottom_x(bitmap):
        ys, xs = np.nonzero(bitmap > 128)
        top, bottom = ys < np.percentile(ys, 20), ys > np.percentile(ys, 80)
        return xs[top].mean() - xs[bottom].mean()
    assert top_minus_bottom_x(tilted) < top_minus_bottom_x(upright) - 3    # the top leans left


def test_thickening_adds_ink():
    thin = render_ttf("1", FONTS / "GreatVibes-Regular.ttf", 16, 10)
    thick = render_ttf("1", FONTS / "GreatVibes-Regular.ttf", 16, 10, thicken=0.35)
    assert thick.astype(int).sum() > thin.astype(int).sum() * 1.3


def test_output_has_exactly_the_grid_size(masks):
    for cols, rows in [(8, 6), (16, 10), (40, 24)]:
        lines = bitmap_to_ascii(render_ttf("0", FONTS / "Bangers-Regular.ttf", cols, rows), cols, rows, masks)
        assert len(lines) == rows and all(len(line) == cols for line in lines)
        assert any(ch != " " for line in lines for ch in line)


def test_ink_modes(masks):
    bitmap = render_ttf("5", FONTS / "ComicNeue-Regular.ttf", 16, 10)
    single = "".join(bitmap_to_ascii(bitmap, 16, 10, masks, "single", symbol="@"))
    assert set(single) == {" ", "@"} and "@" in SINGLE_SYMBOLS
    ramp = "".join(bitmap_to_ascii(bitmap, 16, 10, masks, "ramp"))
    assert set(ramp) <= set(RAMP) and len(set(ramp)) > 3
    with pytest.raises(ValueError, match="unknown ink mode"):
        bitmap_to_ascii(bitmap, 16, 10, masks, "crayon")

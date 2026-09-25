import random
from pathlib import Path

import pytest

from asciidigits.font_render import MASK_FONT, build_char_masks
from asciidigits.sample import render_sample
from asciidigits.settings import Settings
from asciidigits.styles import available_styles, load_styles

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
MASKS = build_char_masks(FONTS / MASK_FONT)


@pytest.mark.parametrize("style", available_styles(load_styles(), 16, 10), ids=lambda s: s.id)
def test_every_style_renders_every_digit_at_the_grid_size(style):
    s = Settings(ink_modes=("symbols", "single", "ramp"), ink_swap=0.5)
    for digit in range(10):
        rows = render_sample(style, digit, s, random.Random(digit), FONTS, MASKS)
        assert len(rows) == 10 and all(len(row) == 16 for row in rows), style.id
        assert sum(ch != " " for row in rows for ch in row) > 5, (style.id, digit)


def test_same_rng_same_sample():
    style = next(s for s in load_styles() if s.id == "ttf:comic-neue")
    a = render_sample(style, 4, Settings(), random.Random(9), FONTS, MASKS)
    b = render_sample(style, 4, Settings(), random.Random(9), FONTS, MASKS)
    assert a == b

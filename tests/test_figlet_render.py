import pytest

from asciidigits.figlet_render import digit_size, figlet_digit, place


def test_digits_are_trimmed():
    glyph = figlet_digit("big", "8")
    assert glyph[0].strip() and glyph[-1].strip()            # no blank first or last row
    assert any(not line.startswith(" ") for line in glyph)   # no blank left column
    assert all(line == line.rstrip() for line in glyph)


def test_known_digit_sizes():
    assert digit_size("big") == (8, 6)
    assert digit_size("starwars") == (8, 6)
    assert digit_size("larry3d") == (12, 7)


def test_place_centres_and_pads_to_the_grid():
    glyph = ("ab", "cd")
    assert place(glyph, 6, 4) == ["      ", "  ab  ", "  cd  ", "      "]


def test_place_moves_and_clamps():
    glyph = ("ab", "cd")
    assert place(glyph, 6, 4, dx=1, dy=-1)[0] == "   ab "
    assert place(glyph, 6, 4, dx=99, dy=99)[-1] == "    cd"      # clamped inside the grid


def test_place_refuses_a_glyph_bigger_than_the_grid():
    with pytest.raises(ValueError, match="grid is 4x4"):
        place(("abcde",), 4, 4)

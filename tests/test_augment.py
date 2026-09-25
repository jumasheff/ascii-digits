import random

from asciidigits.augment import INK, cell_noise, figlet_offset, ink_swap, ttf_params
from asciidigits.settings import Settings


def test_no_noise_changes_nothing():
    rows = [" /\\ ", "|__|"]
    assert cell_noise(rows, 0.0, random.Random(1)) == rows


def test_full_noise_flips_every_cell():
    rows = [" # ", "# #"]
    out = cell_noise(rows, 1.0, random.Random(1))
    assert out[0][1] == " " and out[1][0] == " " and out[1][2] == " "
    assert out[0][0] in INK and out[0][2] in INK and out[1][1] in INK


def test_ink_swap_keeps_blanks():
    assert ink_swap([" /_ ", "|  |"], "@") == [" @@ ", "@  @"]


def test_ttf_params_stay_in_range():
    s = Settings()
    for i in range(200):
        p = ttf_params(random.Random(i), s)
        assert 0.75 <= p.fill <= 0.95 and abs(p.dx) <= 0.06 and abs(p.dy) <= 0.06 and abs(p.angle) <= 8


def test_zero_shift_means_centred_figlet_digits():
    assert figlet_offset(random.Random(3), Settings(shift=0.0)) == (0, 0)


def test_settings_do_not_shift_the_random_stream():
    # rotation 0 or 8: the next random number must be the same
    a, b = random.Random(5), random.Random(5)
    ttf_params(a, Settings(rotation=0.0))
    ttf_params(b, Settings(rotation=8.0))
    assert a.random() == b.random()

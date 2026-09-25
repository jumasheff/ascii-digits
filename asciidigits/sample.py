"""Render one sample: a digit in a style, with the settings' random damage."""

from pathlib import Path

from .augment import cell_noise, figlet_offset, ink_swap, ttf_params
from .figlet_render import figlet_digit, place
from .font_render import SINGLE_SYMBOLS, bitmap_to_ascii, render_ttf


def render_sample(style, digit: int, settings, rng, fonts_dir: Path, masks) -> list:
    """The sample's rows: exactly settings.height strings of settings.width characters."""
    ink_mode = rng.choice(settings.ink_modes)
    symbol = rng.choice(SINGLE_SYMBOLS)
    if style.source == "ttf":
        p = ttf_params(rng, settings)
        bitmap = render_ttf(str(digit), Path(fonts_dir) / style.font_file, settings.width, settings.height,
                            fill=p.fill, dx=p.dx, dy=p.dy, angle=p.angle, thicken=style.thicken)
        rows = bitmap_to_ascii(bitmap, settings.width, settings.height, masks, ink_mode, symbol)
    else:
        dx, dy = figlet_offset(rng, settings)
        rows = place(figlet_digit(style.figlet_font, str(digit)), settings.width, settings.height, dx, dy)
        if rng.random() < settings.ink_swap:
            rows = ink_swap(rows, symbol)
    return cell_noise(rows, settings.noise, rng)

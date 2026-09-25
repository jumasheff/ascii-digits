"""FIGlet digits: render, trim, and place in the grid."""

from functools import lru_cache

import pyfiglet


@lru_cache(maxsize=None)
def figlet_digit(font: str, digit: str) -> tuple:
    """The digit's rows in a FIGlet font, with blank rows and columns trimmed."""
    text = pyfiglet.Figlet(font=font, width=200).renderText(digit)
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return ()
    left = min(len(line) - len(line.lstrip(" ")) for line in lines if line.strip())
    return tuple(line[left:] for line in lines)


def digit_size(font: str) -> tuple:
    """(width of the widest digit, height of the tallest digit), after trimming."""
    glyphs = [figlet_digit(font, str(d)) for d in range(10)]
    return (max(len(line) for glyph in glyphs for line in glyph),
            max(len(glyph) for glyph in glyphs))


def place(glyph: tuple, cols: int, rows: int, dx: int = 0, dy: int = 0) -> list:
    """The glyph centred in a cols x rows grid, moved by (dx, dy) cells, clamped inside."""
    width, height = max(len(line) for line in glyph), len(glyph)
    if width > cols or height > rows:
        raise ValueError(f"glyph is {width}x{height}, grid is {cols}x{rows}")
    x = min(max((cols - width) // 2 + dx, 0), cols - width)
    y = min(max((rows - height) // 2 + dy, 0), rows - height)
    blank = " " * cols
    return [blank] * y + [(" " * x + line).ljust(cols) for line in glyph] + [blank] * (rows - height - y)

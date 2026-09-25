"""Screen every pyfiglet font for usable digits; write tools/figlet_candidates.json.

    python tools/screen_figlet.py

A font is usable when all ten digits render, are different from each other,
and use only printable ASCII. The candidates then go through the
readability check (see the README, "Curating styles").
"""

import json
import math
import sys
from pathlib import Path

import pyfiglet

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asciidigits.figlet_render import digit_size, figlet_digit  # noqa: E402
from asciidigits.settings import PRESETS  # noqa: E402
from asciidigits.styles import MIN_HEIGHT_FRACTION  # noqa: E402

OUT = Path(__file__).resolve().parent / "figlet_candidates.json"


def screen_font(font: str):
    """(width, height) of the font's digits, or None if the font is unusable."""
    try:
        glyphs = [figlet_digit(font, str(d)) for d in range(10)]
    except Exception:          # a few bundled fonts fail to load
        return None
    if not all(glyphs) or len(set(glyphs)) < 10:
        return None
    if any(not 32 <= ord(ch) < 127 for glyph in glyphs for line in glyph for ch in line):
        return None
    return digit_size(font)


def main() -> None:
    fonts = []
    for font in sorted(pyfiglet.FigletFont.getFonts()):
        size = screen_font(font)
        if size:
            fonts.append({"font": font, "width": size[0], "height": size[1]})
    OUT.write_text(json.dumps({"pyfiglet": pyfiglet.__version__, "fonts": fonts}, indent=1) + "\n", encoding="utf-8")
    print(f"{len(fonts)} usable fonts -> {OUT}")
    for name, (width, height) in PRESETS.items():
        need = math.ceil(MIN_HEIGHT_FRACTION * height)
        count = sum(1 for f in fonts if f["width"] <= width and need <= f["height"] <= height)
        print(f"  {name}: {count} fit")


if __name__ == "__main__":
    main()

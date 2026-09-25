"""The style registry: which fonts exist and at which grid sizes they can be used."""

import json
import math
from dataclasses import dataclass
from pathlib import Path

from .settings import PRESETS, SettingsError

STYLES_JSON = Path(__file__).resolve().parent / "data" / "styles.json"
FAMILIES = ("cursive", "comic", "display", "figlet")
MIN_HEIGHT_FRACTION = 0.6       # FIGlet digits must fill at least this much of the grid's height


@dataclass(frozen=True)
class Style:
    id: str                         # "ttf:comic-neue", "figlet:big"
    name: str                       # shown on the page
    family: str                     # one of FAMILIES
    source: str                     # "ttf" or "figlet"
    font_file: str = ""             # TTF: file in assets/fonts
    thicken: float = 0.0            # TTF: extra stroke width in cell widths
    presets: tuple = ()             # TTF: presets where the readability check passed
    figlet_font: str = ""           # FIGlet: pyfiglet font name
    digit_size: tuple = (0, 0)      # FIGlet: (widest, tallest) digit after trimming


def load_styles(path: Path = STYLES_JSON) -> list:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    styles = []
    for entry in data["styles"]:
        entry = dict(entry)
        entry["presets"] = tuple(entry.get("presets", ()))
        entry["digit_size"] = tuple(entry.get("digit_size", (0, 0)))
        styles.append(Style(**entry))
    return styles


def unavailable_reason(style: Style, width: int, height: int):
    """None if the style can be used at width x height; otherwise a short reason for the page."""
    if style.source == "figlet":
        digits_w, digits_h = style.digit_size
        need = math.ceil(MIN_HEIGHT_FRACTION * height)
        if digits_w > width:
            return f"digits are {digits_w} wide; the grid is {width}"
        if digits_h > height:
            return f"digits are {digits_h} tall; the grid is {height}"
        if digits_h < need:
            return f"digits are {digits_h} rows tall; this grid needs at least {need}"
        return None
    passed = [PRESETS[p] for p in style.presets]
    if any(w <= width and h <= height for w, h in passed):
        return None
    if not passed:
        return "failed the readability check"
    smallest = min(passed, key=lambda size: size[0] * size[1])
    return f"not readable below {smallest[0]}x{smallest[1]}"


def available_styles(styles: list, width: int, height: int) -> list:
    return [s for s in styles if unavailable_reason(s, width, height) is None]


def resolve(settings, styles: list) -> list:
    """The styles a run uses: the selected ones, or every available one if none are selected."""
    size = f"{settings.width}x{settings.height}"
    by_id = {s.id: s for s in styles}
    if settings.styles:
        unknown = [i for i in settings.styles if i not in by_id]
        if unknown:
            raise SettingsError(f"unknown style(s): {', '.join(unknown)}")
        chosen = [by_id[i] for i in settings.styles]
        blocked = [f"{s.name} ({reason})" for s in chosen
                   if (reason := unavailable_reason(s, settings.width, settings.height))]
        if blocked:
            raise SettingsError(f"not available at {size}: {'; '.join(blocked)}")
    else:
        chosen = available_styles(styles, settings.width, settings.height)
    if not chosen:
        raise SettingsError(f"no styles are available at {size}")
    return sorted(chosen, key=lambda s: s.id)

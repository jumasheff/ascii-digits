import json
from pathlib import Path

import pytest

from asciidigits.figlet_render import digit_size
from asciidigits.settings import Settings, SettingsError
from asciidigits.styles import FAMILIES, Style, available_styles, load_styles, resolve, unavailable_reason

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
MANIFEST_FILES = {f["file"] for f in json.loads((FONTS / "manifest.json").read_text(encoding="utf-8"))["fonts"]}


def test_the_registry_is_consistent():
    styles = load_styles()
    assert len({s.id for s in styles}) == len(styles)
    for s in styles:
        assert s.family in FAMILIES, s.id
        if s.source == "ttf":
            assert s.font_file in MANIFEST_FILES and s.font_file != "JetBrainsMono.ttf", s.id
            assert s.presets, s.id
        else:
            assert s.family == "figlet" and s.figlet_font, s.id
            assert s.digit_size == digit_size(s.figlet_font), s.id


def figlet(w, h):
    return Style(id="figlet:x", name="x", family="figlet", source="figlet", figlet_font="x", digit_size=(w, h))


def ttf(*presets):
    return Style(id="ttf:x", name="x", family="comic", source="ttf", font_file="x.ttf", presets=presets)


@pytest.mark.parametrize("style, size, reason", [
    (figlet(8, 6), (16, 10), None),
    (figlet(17, 6), (16, 10), "digits are 17 wide; the grid is 16"),
    (figlet(8, 11), (16, 10), "digits are 11 tall; the grid is 10"),
    (figlet(8, 5), (16, 10), "digits are 5 rows tall; this grid needs at least 6"),
    (ttf("16x10"), (16, 10), None),
    (ttf("16x10"), (12, 8), "not readable below 16x10"),
    (ttf(), (16, 10), "failed the readability check"),
])
def test_unavailable_reasons(style, size, reason):
    assert unavailable_reason(style, *size) == reason


# Custom sizes between presets.
def test_a_custom_size_bigger_than_a_passed_preset_is_allowed():
    assert unavailable_reason(ttf("16x10"), 20, 12) is None
    assert unavailable_reason(ttf("16x10"), 15, 10) == "not readable below 16x10"
    assert unavailable_reason(ttf("16x10"), 40, 9) == "not readable below 16x10"


def test_resolve_defaults_to_everything_available():
    styles = [figlet(8, 6), ttf("24x14")]
    assert [s.id for s in resolve(Settings(), styles)] == ["figlet:x"]


def test_resolve_explains_unknown_and_unavailable_styles():
    styles = [figlet(8, 6), ttf("24x14")]
    with pytest.raises(SettingsError, match="unknown style"):
        resolve(Settings(styles=("figlet:nope",)), styles)
    with pytest.raises(SettingsError, match=r"not available at 16x10: x \(not readable below 24x14\)"):
        resolve(Settings(styles=("ttf:x",)), styles)
    with pytest.raises(SettingsError, match="no styles are available at 8x6"):
        resolve(Settings(width=8, height=6), [ttf("24x14")])


def test_available_styles_at_the_default_size_include_every_family():
    at_default = available_styles(load_styles(), 16, 10)
    assert {s.family for s in at_default} == set(FAMILIES)


def test_below_the_smallest_preset_only_figlet_fonts_are_available():
    small = available_styles(load_styles(), 8, 6)
    assert small and all(style.source == "figlet" for style in small)

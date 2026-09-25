import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from apply_curation import curated_entries  # noqa: E402

from asciidigits.styles import load_styles  # noqa: E402

CURRENT = load_styles()
TTF_KEYS = [s.id.removeprefix("ttf:") for s in CURRENT if s.source == "ttf"]


def test_presets_are_applied_and_failed_styles_dropped():
    curation = {"ttf": {key: ["16x10"] for key in TTF_KEYS}, "figlet": ["big", "doom"]}
    curation["ttf"]["sacramento"] = []
    curation["ttf"]["comic-neue"] = ["24x14", "12x8"]
    entries = {e["id"]: e for e in curated_entries(curation, CURRENT)}
    assert "ttf:sacramento" not in entries
    assert entries["ttf:comic-neue"]["presets"] == ["12x8", "24x14"]     # preset order, not input order
    assert entries["ttf:great-vibes"]["thicken"] == 0.35
    assert entries["figlet:big"]["digit_size"] == [8, 6]
    assert [e["id"] for e in entries.values() if e["source"] == "figlet"] == ["figlet:big", "figlet:doom"]


def test_every_ttf_style_must_be_reviewed():
    with pytest.raises(SystemExit, match="missing"):
        curated_entries({"ttf": {"comic-neue": ["16x10"]}, "figlet": []}, CURRENT)


def test_unknown_presets_are_rejected():
    curation = {"ttf": {key: ["16x10"] for key in TTF_KEYS}, "figlet": []}
    curation["ttf"]["caveat"] = ["20x10"]
    with pytest.raises(SystemExit, match="unknown presets"):
        curated_entries(curation, CURRENT)

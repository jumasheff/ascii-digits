import hashlib
import json
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
MANIFEST = json.loads((FONTS_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_every_font_matches_its_pinned_hash():
    for font in MANIFEST["fonts"]:
        data = (FONTS_DIR / font["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == font["sha256"], font["file"]


def test_only_openly_licensed_fonts_ship_each_with_its_license():
    for font in MANIFEST["fonts"]:
        assert font["license"] in ("OFL-1.1", "Apache-2.0"), font["file"]
        text = (FONTS_DIR / "licenses" / (font["file"].rsplit(".", 1)[0] + ".txt")).read_text(encoding="utf-8", errors="replace").lower()
        expected = "open font license" if font["license"] == "OFL-1.1" else "apache license"
        assert expected in text, font["file"]


def test_no_unlisted_font_files():
    listed = {font["file"] for font in MANIFEST["fonts"]}
    on_disk = {path.name for path in FONTS_DIR.glob("*.ttf")}
    assert on_disk == listed


def test_the_character_shape_font_is_bundled():
    assert "JetBrainsMono.ttf" in {font["file"] for font in MANIFEST["fonts"]}

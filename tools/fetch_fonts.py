"""Download the bundled fonts and their licenses from google/fonts at a pinned commit.

    python tools/fetch_fonts.py

Every font's SHA-256 is checked against assets/fonts/manifest.json, so a
changed upstream file can't slip in. To add a font: add a manifest entry with
an empty sha256, run this, and copy the printed hash into the manifest.
"""

import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
MANIFEST = FONTS_DIR / "manifest.json"
LICENSE_FILES = {"OFL-1.1": "OFL.txt", "Apache-2.0": "LICENSE.txt"}


def license_copy_name(font: dict) -> str:
    """assets/fonts/licenses/<font file without .ttf>.txt"""
    return font["file"].rsplit(".", 1)[0] + ".txt"


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    base = f"https://raw.githubusercontent.com/google/fonts/{manifest['commit']}/"
    (FONTS_DIR / "licenses").mkdir(exist_ok=True)
    failed = False
    for font in manifest["fonts"]:
        data = fetch(base + urllib.parse.quote(font["source"]))
        digest = hashlib.sha256(data).hexdigest()
        if digest != font["sha256"]:
            print(f"MISMATCH {font['file']}: got {digest}, manifest says {font['sha256'] or '(empty)'}")
            failed = True
            continue
        (FONTS_DIR / font["file"]).write_bytes(data)
        license_url = base + urllib.parse.quote(font["source"].rsplit("/", 1)[0] + "/" + LICENSE_FILES[font["license"]])
        (FONTS_DIR / "licenses" / license_copy_name(font)).write_bytes(fetch(license_url))
        print(f"ok {font['file']} ({len(data):,} bytes, {font['license']})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

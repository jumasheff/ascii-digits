"""Write asciidigits/data/styles.json from the readability review in tools/curation.json.

    python tools/apply_curation.py

tools/curation.json, filled in by the person reviewing the sheets:
    {
      "ttf": {"comic-neue": ["12x8", "16x10", "24x14"], "sacramento": []},
      "figlet": ["big", "doom", "starwars"]
    }
"ttf" maps each TTF style (id without "ttf:") to the presets where all ten
digits were readable; [] means it failed everywhere and is dropped.
"figlet" lists the FIGlet fonts to keep.
"""

import json
import sys
from datetime import date
from pathlib import Path

GENERATOR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GENERATOR))
from asciidigits.figlet_render import digit_size  # noqa: E402
from asciidigits.settings import PRESETS  # noqa: E402
from asciidigits.styles import FAMILIES, STYLES_JSON, available_styles, load_styles  # noqa: E402

CURATION = Path(__file__).resolve().parent / "curation.json"


def curated_entries(curation: dict, current: list) -> list:
    """styles.json entries: TTF styles with their passed presets, then the chosen FIGlet fonts."""
    ttf = {s.id.removeprefix("ttf:"): s for s in current if s.source == "ttf"}
    unknown = sorted(set(curation["ttf"]) - set(ttf))
    missing = sorted(set(ttf) - set(curation["ttf"]))
    if unknown or missing:
        raise SystemExit(f"curation.json must list every TTF style exactly: unknown {unknown}, missing {missing}")
    entries = []
    for key, style in ttf.items():
        presets = curation["ttf"][key]
        bad = [p for p in presets if p not in PRESETS]
        if bad:
            raise SystemExit(f"{key}: unknown presets {bad}")
        if presets:
            entry = {"id": style.id, "name": style.name, "family": style.family, "source": "ttf",
                     "font_file": style.font_file, "presets": sorted(presets, key=list(PRESETS).index)}
            if style.thicken:
                entry["thicken"] = style.thicken
            entries.append(entry)
    for font in sorted(set(curation["figlet"])):
        entries.append({"id": f"figlet:{font}", "name": f"FIGlet {font}", "family": "figlet",
                        "source": "figlet", "figlet_font": font, "digit_size": list(digit_size(font))})
    return entries


def main() -> None:
    curation = json.loads(CURATION.read_text(encoding="utf-8"))
    entries = curated_entries(curation, load_styles())
    STYLES_JSON.write_text(json.dumps(
        {"note": f"Curated {date.today().isoformat()} by the readability check (tools/curation.json).",
         "styles": entries}, indent=1) + "\n", encoding="utf-8")
    styles = load_styles()
    print(f"wrote {STYLES_JSON}: {len(styles)} styles")
    for name, (width, height) in PRESETS.items():
        counts = {family: 0 for family in FAMILIES}
        for style in available_styles(styles, width, height):
            counts[style.family] += 1
        warn = [f for f, n in counts.items() if n < 3]
        print(f"  {name}: {counts}" + (f"  (fewer than 3: {', '.join(warn)})" if warn else ""))


if __name__ == "__main__":
    main()

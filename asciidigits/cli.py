"""Command line: generate a dataset, list styles, or write readability sheets.

    python -m asciidigits generate --seed 42 --out ascii-digits-42.zip
    python -m asciidigits styles --size 8x6
    python -m asciidigits sheet --size 16x10 --out sheets/16x10.txt
"""

import argparse
import json
import platform
import random
import sys
from pathlib import Path

from .dataset import DEFAULT_FONTS_DIR, FontMissingError, Generator
from .font_render import MASK_FONT, build_char_masks
from .sample import render_sample
from .settings import INK_MODES, SPLIT_MODES, Settings, SettingsError, parse_size
from .styles import Style, load_styles, unavailable_reason


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m asciidigits")
    commands = parser.add_subparsers(dest="command", required=True)

    gen = commands.add_parser("generate", help="write a dataset zip")
    gen.add_argument("--seed", type=int, default=42)
    gen.add_argument("--size", default="16x10", help="WIDTHxHEIGHT in characters")
    gen.add_argument("--per-digit", type=int, nargs=3, default=[500, 100, 100], metavar=("TRAIN", "VAL", "TEST"))
    gen.add_argument("--split", choices=SPLIT_MODES, default="heldout")
    gen.add_argument("--styles", nargs="*", default=[], help="style ids; default: every available style")
    gen.add_argument("--ink", nargs="+", choices=INK_MODES, default=["symbols"])
    for name, default in (("noise", 0.03), ("rotation", 8.0), ("shift", 0.06), ("size-jitter", 0.2), ("ink-swap", 0.0)):
        gen.add_argument(f"--{name}", type=float, default=default)
    gen.add_argument("--out", type=Path, help="default: ascii-digits-SEED.zip")

    styles = commands.add_parser("styles", help="list styles and whether they fit a size")
    styles.add_argument("--size", default="16x10")

    sheet = commands.add_parser("sheet", help="write a readability sheet: every style, every digit")
    sheet.add_argument("--size", default="16x10")
    sheet.add_argument("--out", type=Path, required=True)
    sheet.add_argument("--ignore-presets", action="store_true",
                       help="show TTF styles even where they haven't passed the check yet")
    sheet.add_argument("--figlet-candidates", type=Path,
                       help="show these FIGlet fonts (tools/figlet_candidates.json) instead of the registry's")

    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            return _generate(args)
        if args.command == "styles":
            return _styles(args)
        return _sheet(args)
    except (SettingsError, FontMissingError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def _generate(args) -> int:
    width, height = parse_size(args.size)
    settings = Settings(seed=args.seed, width=width, height=height, per_digit=tuple(args.per_digit),
                        split_mode=args.split, styles=tuple(args.styles), ink_modes=tuple(args.ink),
                        noise=args.noise, rotation=args.rotation, shift=args.shift,
                        size_jitter=args.size_jitter, ink_swap=args.ink_swap)
    generator = Generator(settings)
    for notice in generator.style_plan.notices:
        print(f"note: {notice}")
    while generator.done < generator.total:
        done = generator.run_chunk(500)
        print(f"\r{done}/{generator.total} samples", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)
    data, sha = generator.finish(runtime=f"cli {platform.system()} {platform.machine()}")
    out = args.out or Path(generator.filename)
    out.write_bytes(data)
    print(f"wrote {out}: {generator.total} samples, dataset_sha256 {sha}")
    return 0


def _styles(args) -> int:
    width, height = parse_size(args.size)
    for style in load_styles():
        reason = unavailable_reason(style, width, height)
        print(f"{style.id:28s} {style.family:8s} {'ok' if reason is None else 'no: ' + reason}")
    return 0


def _sheet(args) -> int:
    width, height = parse_size(args.size)
    settings = Settings(width=width, height=height).validate()
    styles = [s for s in load_styles() if not (args.figlet_candidates and s.source == "figlet")]
    if args.figlet_candidates:
        for font in json.loads(args.figlet_candidates.read_text(encoding="utf-8"))["fonts"]:
            styles.append(Style(id=f"figlet:{font['font']}", name=f"FIGlet {font['font']}", family="figlet",
                                source="figlet", figlet_font=font["font"],
                                digit_size=(font["width"], font["height"])))
    masks = build_char_masks(DEFAULT_FONTS_DIR / MASK_FONT)
    clean = Settings(width=width, height=height, noise=0.0, rotation=0.0, shift=0.0, size_jitter=0.0)
    out = []
    shown = 0
    for style in styles:
        reason = unavailable_reason(style, width, height)
        if reason and not (args.ignore_presets and style.source == "ttf" and "readable" in reason):
            continue
        shown += 1
        out.append(f"== {style.id}  ({style.name}, {style.family})")
        for label, row_settings, seed in (("clean", clean, 0), ("damaged", settings, 1), ("damaged", settings, 2)):
            glyphs = [render_sample(style, d, row_settings, random.Random(f"{style.id}|{d}|{seed}"),
                                    DEFAULT_FONTS_DIR, masks) for d in range(10)]
            out.append(f"   {label}")
            for r in range(height):
                out.append("   " + "  ".join(glyph[r] for glyph in glyphs))
        out.append("")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {args.out}: {shown} styles at {width}x{height}")
    return 0

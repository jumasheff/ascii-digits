"""Hashes of fixed outputs, for comparing runtimes (the golden test).

The CLI (CPython) and the web page (Pyodide) must return the same hashes.
"""

import hashlib
import random
from pathlib import Path

from .dataset import DEFAULT_FONTS_DIR, generate_dataset
from .font_render import MASK_FONT, build_char_masks
from .sample import render_sample
from .settings import Settings
from .styles import available_styles, load_styles


def samples_hash(width: int, height: int, fonts_dir: Path) -> str:
    """Every style available at the size, every digit, every ink mode, with damage."""
    settings = Settings(width=width, height=height, ink_modes=("symbols", "single", "ramp"),
                        noise=0.05, ink_swap=0.5).validate()
    masks = build_char_masks(fonts_dir / MASK_FONT)
    digest = hashlib.sha256()
    for style in available_styles(load_styles(), width, height):
        for digit in range(10):
            for variant in range(3):
                rng = random.Random(f"{style.id}|{digit}|{variant}")
                for row in render_sample(style, digit, settings, rng, fonts_dir, masks):
                    digest.update(row.encode() + b"\n")
    return digest.hexdigest()


def self_check(fonts_dir=None) -> dict:
    fonts_dir = Path(fonts_dir) if fonts_dir else DEFAULT_FONTS_DIR
    small = dict(per_digit=(3, 1, 1), seed=11)
    return {
        "samples-16x10": samples_hash(16, 10, fonts_dir),
        "samples-24x14": samples_hash(24, 14, fonts_dir),
        "dataset-heldout": generate_dataset(Settings(**small), fonts_dir, created_at="-")[1],
        "dataset-random": generate_dataset(Settings(split_mode="random", ink_modes=("ramp", "single"),
                                                    **small), fonts_dir, created_at="-")[1],
    }

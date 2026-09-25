"""Generate a dataset in chunks (for the web worker) or all at once (for the CLI)."""

import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import fontTools
import numpy
import pyfiglet

from .export import build_zip, sample_line
from .font_render import MASK_FONT, build_char_masks
from .rng import rng_for
from .sample import render_sample
from .settings import SPLITS
from .splits import assign_styles, plan_samples
from .styles import load_styles, resolve

DEFAULT_FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


class FontMissingError(RuntimeError):
    """A bundled font is missing. Generation stops instead of silently dropping the style."""


def check_fonts(styles: list, fonts_dir: Path) -> None:
    for name in [MASK_FONT] + [s.font_file for s in styles if s.source == "ttf"]:
        if not (fonts_dir / name).is_file():
            raise FontMissingError(
                f"font file missing: {name}. Generation stopped, because skipping the style would "
                f"silently change the dataset for this seed.")


def library_versions() -> dict:
    return {"python": platform.python_version(), "numpy": numpy.__version__,
            "fonttools": fontTools.version, "pyfiglet": pyfiglet.__version__, "platform": sys.platform}


class Generator:
    """Plans a dataset from settings, then renders it chunk by chunk.

    The output doesn't depend on the chunk sizes: every sample has its own
    random generator, derived from (seed, split, index).
    """

    def __init__(self, settings, fonts_dir=None, styles=None):
        self.settings = settings.validate()
        self.fonts_dir = Path(fonts_dir) if fonts_dir else DEFAULT_FONTS_DIR
        self.styles = resolve(settings, styles if styles is not None else load_styles())
        check_fonts(self.styles, self.fonts_dir)
        self.by_id = {s.id: s for s in self.styles}
        self.masks = build_char_masks(self.fonts_dir / MASK_FONT)
        self.style_plan = assign_styles(self.styles, settings.split_mode, settings.seed)
        self.specs = plan_samples(self.style_plan, settings.per_digit, settings.seed)
        self.lines = {split: [] for split in SPLITS}
        self.labels = {split: [] for split in SPLITS}
        self.done = 0

    @property
    def total(self) -> int:
        return len(self.specs)

    @property
    def filename(self) -> str:
        return f"ascii-digits-{self.settings.seed}.zip"

    def run_chunk(self, count: int = 200) -> int:
        """Render the next `count` samples; returns how many are done."""
        for spec in self.specs[self.done:self.done + count]:
            style = self.by_id[spec.style_id]
            rng = rng_for(self.settings.seed, "sample", spec.split, spec.index)
            rows = render_sample(style, spec.label, self.settings, rng, self.fonts_dir, self.masks)
            self.lines[spec.split].append(sample_line(spec, style, rows))
            self.labels[spec.split].append(spec.label)
        self.done = min(self.done + count, self.total)
        return self.done

    def finish(self, runtime: str, created_at=None) -> tuple:
        """(zip bytes, dataset_sha256) once every sample is rendered."""
        if self.done < self.total:
            raise RuntimeError(f"only {self.done} of {self.total} samples are rendered")
        created_at = created_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        return build_zip(self.settings, self.style_plan, self.lines, self.labels,
                         runtime=runtime, created_at=created_at, versions=library_versions())


def generate_dataset(settings, fonts_dir=None, runtime="cli", created_at=None) -> tuple:
    """(zip bytes, dataset_sha256) in one call."""
    generator = Generator(settings, fonts_dir)
    while generator.done < generator.total:
        generator.run_chunk(1000)
    return generator.finish(runtime, created_at)


def preview(settings, count: int = 30, fonts_dir=None) -> list:
    """`count` random samples from the selected styles (no split rules, so 1 style is fine)."""
    settings.validate()
    fonts_dir = Path(fonts_dir) if fonts_dir else DEFAULT_FONTS_DIR
    styles = resolve(settings, load_styles())
    check_fonts(styles, fonts_dir)
    masks = build_char_masks(fonts_dir / MASK_FONT)
    samples = []
    for i in range(count):
        rng = rng_for(settings.seed, "preview", i)
        style, label = styles[rng.randrange(len(styles))], rng.randrange(10)
        rows = render_sample(style, label, settings, rng, fonts_dir, masks)
        samples.append({"label": label, "style": style.id, "name": style.name, "rows": rows})
    return samples

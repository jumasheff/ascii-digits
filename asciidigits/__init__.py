"""Labelled ASCII-art digit datasets in many styles.

Source: https://github.com/jumasheff/ascii-digits
"""

__version__ = "1.0.0"

from .dataset import FontMissingError, Generator, generate_dataset, preview  # noqa: E402
from .settings import Settings, SettingsError  # noqa: E402

__all__ = ["FontMissingError", "Generator", "Settings", "SettingsError", "generate_dataset", "preview",
           "__version__"]

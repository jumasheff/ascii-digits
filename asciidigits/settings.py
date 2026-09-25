"""Dataset settings: defaults, limits, validation, and conversion to and from JSON.

The same Settings object is built by the CLI (from flags) and by the web page
(from the form and the URL), so every limit lives here once.
"""

from dataclasses import asdict, dataclass, fields

PRESETS = {"12x8": (12, 8), "16x10": (16, 10), "24x14": (24, 14)}
MIN_WIDTH, MIN_HEIGHT = 6, 4
MAX_WIDTH, MAX_HEIGHT = 40, 24
MAX_CELLS = 8_000_000          # samples x width x height in one run
SPLITS = ("train", "val", "test")
SPLIT_MODES = ("heldout", "random")
INK_MODES = ("symbols", "single", "ramp")
FLOAT_LIMITS = {               # name: (min, max)
    "noise": (0.0, 0.3),
    "rotation": (0.0, 15.0),
    "shift": (0.0, 0.15),
    "size_jitter": (0.0, 0.3),
    "ink_swap": (0.0, 1.0),
}


class SettingsError(ValueError):
    """A setting is invalid. The message is shown to the user as-is."""


@dataclass(frozen=True)
class Settings:
    seed: int = 42
    width: int = 16
    height: int = 10
    per_digit: tuple = (500, 100, 100)     # samples per digit in train, val, test
    split_mode: str = "heldout"
    styles: tuple = ()                     # style ids; empty = every style available at this size
    ink_modes: tuple = ("symbols",)        # TTF inking; each sample picks one of these
    noise: float = 0.03                    # chance that a cell flips
    rotation: float = 8.0                  # TTF: up to this many degrees either way
    shift: float = 0.06                    # TTF: up to this fraction of the grid; FIGlet: +/-1 cell if > 0
    size_jitter: float = 0.2               # TTF glyph fills between (0.95 - size_jitter) and 0.95 of the grid
    ink_swap: float = 0.0                  # FIGlet: chance that all ink becomes one random symbol

    def __post_init__(self):
        # The page sends ink modes in checkbox order and the CLI in flag order. The order
        # picks each sample's mode, so keep one canonical order (and no duplicates).
        rank = {mode: i for i, mode in enumerate(INK_MODES)}
        modes = sorted(dict.fromkeys(self.ink_modes), key=lambda mode: rank.get(mode, len(rank)))
        object.__setattr__(self, "ink_modes", tuple(modes))

    @property
    def total_samples(self) -> int:
        return 10 * sum(self.per_digit)

    def validate(self) -> "Settings":
        if not 0 <= self.seed < 2 ** 32:
            raise SettingsError(f"seed must be between 0 and {2 ** 32 - 1}, got {self.seed}")
        if not MIN_WIDTH <= self.width <= MAX_WIDTH:
            raise SettingsError(f"width must be {MIN_WIDTH} to {MAX_WIDTH}, got {self.width}")
        if not MIN_HEIGHT <= self.height <= MAX_HEIGHT:
            raise SettingsError(f"height must be {MIN_HEIGHT} to {MAX_HEIGHT}, got {self.height}")
        if len(self.per_digit) != 3 or any(n < 0 for n in self.per_digit):
            raise SettingsError("per_digit needs three counts (train, val, test), none negative")
        if self.per_digit[0] < 1:
            raise SettingsError("train needs at least 1 sample per digit")
        cells = self.total_samples * self.width * self.height
        if cells > MAX_CELLS:
            raise SettingsError(
                f"too big: {self.total_samples:,} samples x {self.width}x{self.height} = {cells:,} cells; "
                f"the limit is {MAX_CELLS:,}")
        if self.split_mode not in SPLIT_MODES:
            raise SettingsError(f"split_mode must be one of {', '.join(SPLIT_MODES)}, got {self.split_mode!r}")
        if not self.ink_modes or any(mode not in INK_MODES for mode in self.ink_modes):
            raise SettingsError(f"ink_modes must be one or more of {', '.join(INK_MODES)}")
        for name, (low, high) in FLOAT_LIMITS.items():
            value = getattr(self, name)
            if not low <= value <= high:
                raise SettingsError(f"{name} must be {low} to {high}, got {value}")
        return self

    def to_dict(self) -> dict:
        data = asdict(self)
        for name in ("per_digit", "styles", "ink_modes"):
            data[name] = list(data[name])
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """Build and validate settings from JSON-like data. Missing keys keep their defaults."""
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            raise SettingsError(f"unknown setting(s): {', '.join(unknown)}")
        values = {}
        for name, raw in data.items():
            if name in ("seed", "width", "height"):
                values[name] = _int(name, raw)
            elif name == "per_digit":
                values[name] = tuple(_int(name, n) for n in _list(name, raw))
            elif name in ("styles", "ink_modes"):
                values[name] = tuple(dict.fromkeys(_str(name, s) for s in _list(name, raw)))
            elif name == "split_mode":
                values[name] = _str(name, raw)
            else:
                values[name] = _float(name, raw)
        return cls(**values).validate()


def parse_size(text: str) -> tuple:
    """'16x10' -> (16, 10)."""
    try:
        width, height = (int(part) for part in text.lower().split("x"))
    except ValueError:
        raise SettingsError(f"size must look like 16x10, got {text!r}") from None
    return width, height


def _int(name, raw):
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        raise SettingsError(f"{name} must be a whole number, got {raw!r}")
    if isinstance(raw, int):
        return raw                          # range checks happen in validate()
    try:
        value = float(raw)
        whole = int(value)                  # nan -> ValueError, inf and 1e400 -> OverflowError
    except (ValueError, OverflowError):
        raise SettingsError(f"{name} must be a whole number, got {raw!r}") from None
    if value != whole:
        raise SettingsError(f"{name} must be a whole number, got {raw!r}")
    return whole


def _float(name, raw):
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        raise SettingsError(f"{name} must be a number, got {raw!r}")
    try:
        return float(raw)
    except ValueError:
        raise SettingsError(f"{name} must be a number, got {raw!r}") from None


def _str(name, raw):
    if not isinstance(raw, str):
        raise SettingsError(f"{name} must be text, got {raw!r}")
    return raw


def _list(name, raw):
    if isinstance(raw, str):
        return [part for part in raw.split(",") if part]
    if not isinstance(raw, (list, tuple)):
        raise SettingsError(f"{name} must be a list, got {raw!r}")
    return list(raw)

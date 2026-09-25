"""Random damage: TTF scale/shift/rotation, FIGlet offsets, cell noise, ink swap.

Every function takes the sample's own random.Random and draws the same number
of values whatever the settings, so one setting never shifts another's randomness.
"""

from dataclasses import dataclass

INK = "_|/\\()<>,'"      # the characters that damage writes into blank cells


@dataclass(frozen=True)
class TtfParams:
    fill: float
    dx: float
    dy: float
    angle: float


def ttf_params(rng, settings) -> TtfParams:
    return TtfParams(
        fill=rng.uniform(0.95 - settings.size_jitter, 0.95),
        dx=rng.uniform(-settings.shift, settings.shift),
        dy=rng.uniform(-settings.shift, settings.shift),
        angle=rng.uniform(-settings.rotation, settings.rotation),
    )


def figlet_offset(rng, settings) -> tuple:
    dx, dy = rng.randint(-1, 1), rng.randint(-1, 1)
    return (dx, dy) if settings.shift > 0 else (0, 0)


def cell_noise(rows: list, prob: float, rng) -> list:
    """Each cell flips with probability prob: blank -> random ink, ink -> blank."""
    out = []
    for row in rows:
        chars = []
        for ch in row:
            flip, ink = rng.random() < prob, rng.choice(INK)
            chars.append((ink if ch == " " else " ") if flip else ch)
        out.append("".join(chars))
    return out


def ink_swap(rows: list, symbol: str) -> list:
    return ["".join(" " if ch == " " else symbol for ch in row) for row in rows]

"""Which styles go to which split, and which label and style every sample gets."""

from dataclasses import dataclass

from .rng import rng_for
from .settings import SPLITS, SettingsError

TARGET = {"train": 0.70, "val": 0.15, "test": 0.15}


@dataclass(frozen=True)
class StylePlan:
    by_split: dict          # split -> tuple of style ids
    notices: tuple          # sentences for the page and metadata.json


@dataclass(frozen=True)
class SampleSpec:
    split: str
    index: int              # position in the split's file
    label: int
    style_id: str


def assign_styles(styles: list, mode: str, seed: int) -> StylePlan:
    ids = sorted(s.id for s in styles)
    if mode == "random":
        return StylePlan({split: tuple(ids) for split in SPLITS}, ())
    if len(ids) < 3:
        raise SettingsError("held-out styles needs at least 3 styles, one per split: "
                            "select more styles or use random mode")
    rng = rng_for(seed, "styles")
    families = {}
    for style in sorted(styles, key=lambda s: s.id):
        families.setdefault(style.family, []).append(style.id)
    out = {split: [] for split in SPLITS}
    small = []
    for family in sorted(families):
        members = families[family][:]
        rng.shuffle(members)
        if len(members) >= 3:              # stratified: at least one style in every split
            n_val = max(1, round(TARGET["val"] * len(members)))
            n_test = max(1, round(TARGET["test"] * len(members)))
            out["val"] += members[:n_val]
            out["test"] += members[n_val:n_val + n_test]
            out["train"] += members[n_val + n_test:]
        else:
            small += members
    for style_id in small:                 # families too small to spread: fill gaps, then balance
        empty = [split for split in SPLITS if not out[split]]
        if empty:
            target = empty[0]
        else:
            total = sum(len(v) for v in out.values()) + 1
            target = max(SPLITS, key=lambda split: TARGET[split] * total - len(out[split]))
        out[target].append(style_id)
    notices = []
    for family in sorted(families):
        members = families[family]
        if len(members) < 3:
            where = [split for split in SPLITS if any(m in out[split] for m in members)]
            count = f"{len(members)} {family} style{'s' if len(members) > 1 else ''}"
            notices.append(f"only {count} selected, so that family appears only in {' and '.join(where)}")
    return StylePlan({split: tuple(sorted(out[split])) for split in SPLITS}, tuple(notices))


def plan_samples(style_plan: StylePlan, per_digit: tuple, seed: int) -> list:
    """Every sample's split, index, label and style. Labels are balanced and shuffled."""
    specs = []
    for split, count in zip(SPLITS, per_digit):
        labels = [digit for digit in range(10) for _ in range(count)]
        rng_for(seed, "order", split).shuffle(labels)
        choices = style_plan.by_split[split]
        for index, label in enumerate(labels):
            style_id = choices[rng_for(seed, "style", split, index).randrange(len(choices))]
            specs.append(SampleSpec(split, index, label, style_id))
    return specs

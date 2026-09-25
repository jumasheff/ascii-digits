import pytest

from asciidigits.settings import SPLITS, SettingsError
from asciidigits.splits import assign_styles, plan_samples
from asciidigits.styles import Style


def styles(**families):
    """styles(cursive=5, figlet=2) -> 7 fake styles."""
    return [Style(id=f"{family}:{i}", name=f"{family} {i}", family=family, source="ttf")
            for family, count in families.items() for i in range(count)]


def test_random_mode_uses_every_style_everywhere():
    plan = assign_styles(styles(cursive=2, figlet=3), "random", 1)
    assert all(len(plan.by_split[split]) == 5 for split in SPLITS)


def test_held_out_splits_are_disjoint_and_cover_everything():
    chosen = styles(cursive=5, comic=5, display=6, figlet=30)
    plan = assign_styles(chosen, "heldout", 1)
    sets = [set(plan.by_split[split]) for split in SPLITS]
    assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
    assert set().union(*sets) == {s.id for s in chosen}
    assert 0.6 <= len(sets[0]) / len(chosen) <= 0.8                 # about 70% train


def test_every_family_with_three_or_more_styles_reaches_every_split():
    plan = assign_styles(styles(cursive=3, comic=4, figlet=12), "heldout", 5)
    for family in ("cursive", "comic", "figlet"):
        for split in SPLITS:
            assert any(i.startswith(family) for i in plan.by_split[split]), (family, split)


def test_small_families_are_placed_and_explained():
    plan = assign_styles(styles(comic=1, figlet=6), "heldout", 2)
    assert all(plan.by_split[split] for split in SPLITS)
    assert len(plan.notices) == 1 and plan.notices[0].startswith("only 1 comic style selected")


def test_only_small_families_still_fill_every_split():
    plan = assign_styles(styles(cursive=1, comic=1, display=1), "heldout", 3)
    assert all(len(plan.by_split[split]) == 1 for split in SPLITS)


def test_held_out_needs_three_styles():
    with pytest.raises(SettingsError, match="at least 3 styles"):
        assign_styles(styles(figlet=2), "heldout", 1)


def test_the_seed_decides_the_split():
    chosen = styles(figlet=20)
    assert assign_styles(chosen, "heldout", 1) == assign_styles(chosen, "heldout", 1)
    assert assign_styles(chosen, "heldout", 1) != assign_styles(chosen, "heldout", 2)


def test_labels_are_balanced_and_shuffled():
    plan = assign_styles(styles(figlet=6), "heldout", 1)
    specs = plan_samples(plan, (20, 5, 5), 1)
    for split, count in zip(SPLITS, (20, 5, 5)):
        labels = [s.label for s in specs if s.split == split]
        assert sorted(labels) == [d for d in range(10) for _ in range(count)]
        if split == "train":
            assert labels != sorted(labels)
        assert all(s.style_id in plan.by_split[split] for s in specs if s.split == split)

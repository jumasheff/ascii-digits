from asciidigits.rng import derive_seed, rng_for


def test_known_value_never_changes():
    # If this fails, every dataset ever generated would change. Don't "fix" the number.
    assert derive_seed(42, "sample", "train", 0) == 18221302402548492509
    assert rng_for(42, "sample", "train", 0).random() == 0.6318821719881448


def test_same_inputs_same_seed():
    assert derive_seed(7, "a", 1) == derive_seed(7, "a", 1)


def test_every_part_matters():
    base = derive_seed(7, "sample", "train", 3)
    assert derive_seed(8, "sample", "train", 3) != base
    assert derive_seed(7, "sample", "val", 3) != base
    assert derive_seed(7, "sample", "train", 4) != base


def test_seed_fits_in_64_bits():
    assert 0 <= derive_seed(123, "x") < 2 ** 64

"""Seeds that are the same on every platform and in every runtime.

Every random choice in a dataset comes from a random.Random seeded by
derive_seed(global seed, labels...). Python's hash() is salted per process,
so it is never used here; SHA-256 is.
"""

import hashlib
import random


def derive_seed(seed: int, *parts: object) -> int:
    """A 64-bit seed from the global seed and any labels."""
    text = "|".join([str(seed), *(str(part) for part in parts)])
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def rng_for(seed: int, *parts: object) -> random.Random:
    """A random generator for one purpose, e.g. rng_for(42, "sample", "train", 7)."""
    return random.Random(derive_seed(seed, *parts))

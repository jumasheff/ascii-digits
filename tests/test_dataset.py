import io
import json
import shutil
import zipfile
from pathlib import Path

import pytest

from asciidigits import FontMissingError, Generator, Settings, SettingsError, generate_dataset, preview
from asciidigits.dataset import DEFAULT_FONTS_DIR

SMALL = Settings(seed=3, per_digit=(4, 2, 2))


def unzip(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {name: archive.read(name).decode() for name in archive.namelist()}


@pytest.fixture(scope="module")
def small_zip():
    return generate_dataset(SMALL, created_at="2026-01-01T00:00:00+00:00")


def test_the_zip_has_the_five_files(small_zip):
    files = unzip(small_zip[0])
    assert sorted(files) == ["README.txt", "metadata.json", "test.jsonl", "train.jsonl", "val.jsonl"]


def test_every_line_follows_the_format(small_zip):
    files = unzip(small_zip[0])
    for split, count in (("train", 40), ("val", 20), ("test", 20)):
        lines = files[f"{split}.jsonl"].splitlines()
        assert len(lines) == count
        labels = []
        for i, line in enumerate(lines):
            sample = json.loads(line)
            assert set(sample) == {"id", "label", "style", "family", "rows"}
            assert sample["id"] == f"{split}-{i:06d}"
            assert len(sample["rows"]) == 10 and all(len(row) == 16 for row in sample["rows"])
            labels.append(sample["label"])
        assert sorted(labels) == [d for d in range(10) for _ in range(count // 10)]


def test_metadata(small_zip):
    meta = json.loads(unzip(small_zip[0])["metadata.json"])
    assert meta["dataset_sha256"] == small_zip[1]
    assert meta["settings"] == SMALL.to_dict()
    assert meta["counts"]["train"] == {str(d): 4 for d in range(10)}
    assert set(meta["styles"]["train"]).isdisjoint(meta["styles"]["test"])
    assert meta["provenance"]["runtime"] == "cli"


def test_two_runs_give_identical_zips(small_zip):
    assert generate_dataset(SMALL, created_at="2026-01-01T00:00:00+00:00") == small_zip


def test_chunk_size_does_not_change_the_dataset(small_zip):
    for chunk in (1, 7, 1000):
        generator = Generator(SMALL)
        while generator.done < generator.total:
            generator.run_chunk(chunk)
        assert generator.finish("cli", "2026-01-01T00:00:00+00:00")[1] == small_zip[1]


def test_a_different_seed_gives_a_different_dataset(small_zip):
    assert generate_dataset(Settings(seed=4, per_digit=(4, 2, 2)))[1] != small_zip[1]


def test_a_missing_font_stops_generation(tmp_path):
    fonts = tmp_path / "fonts"
    shutil.copytree(DEFAULT_FONTS_DIR, fonts)
    (fonts / "ComicNeue-Regular.ttf").unlink()
    with pytest.raises(FontMissingError, match="ComicNeue-Regular.ttf"):
        Generator(Settings(per_digit=(1, 1, 1)), fonts_dir=fonts)


def test_held_out_with_too_few_styles_is_a_settings_error():
    with pytest.raises(SettingsError, match="at least 3 styles"):
        Generator(Settings(styles=("figlet:big", "ttf:comic-neue")))


def test_finish_refuses_a_half_done_dataset():
    generator = Generator(SMALL)
    generator.run_chunk(5)
    with pytest.raises(RuntimeError, match="only 5 of 80"):
        generator.finish("cli")


def test_preview_works_with_a_single_style():
    samples = preview(Settings(styles=("figlet:big",)), count=12)
    assert len(samples) == 12 and {s["style"] for s in samples} == {"figlet:big"}
    assert all(len(s["rows"]) == 10 for s in samples)

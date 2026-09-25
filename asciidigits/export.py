"""The download: JSONL per split, metadata.json, README.txt, in a zip.

The three .jsonl files are the dataset and are byte-identical wherever it is
generated. metadata.json adds a "provenance" block (runtime, creation time,
library versions) that differs between runs, and zlib may compress
differently on different platforms, so compare datasets by
metadata["dataset_sha256"], not by the zip's bytes.
"""

import hashlib
import io
import json
import zipfile

from . import __version__
from .settings import SPLITS

FORMAT = "ascii-digits/1"
ZIP_TIME = (1980, 1, 1, 0, 0, 0)

README = """ASCII digit dataset, made by asciidigits {version}

Files
  train.jsonl, val.jsonl, test.jsonl   one sample per line
  metadata.json                        settings, styles in each split, counts, versions

Each line is a JSON object:
  id      e.g. "train-000123"
  label   the digit, 0-9
  style   e.g. "ttf:comic-neue" or "figlet:big"
  family  cursive, comic, display or figlet
  rows    {height} strings of exactly {width} characters

Load a split in Python (standard library only):

    import json

    def load(path):
        samples = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                s = json.loads(line)
                vector = [0 if ch == " " else 1 for row in s["rows"] for ch in row]
                samples.append((vector, s["label"]))
        return samples

    train = load("train.jsonl")
"""


def sample_line(spec, style, rows: list) -> str:
    return json.dumps({"id": f"{spec.split}-{spec.index:06d}", "label": spec.label,
                       "style": style.id, "family": style.family, "rows": rows})


def split_texts(lines: dict) -> dict:
    return {split: "".join(line + "\n" for line in lines[split]) for split in SPLITS}


def dataset_sha256(texts: dict) -> str:
    digest = hashlib.sha256()
    for split in SPLITS:
        digest.update(f"{split}.jsonl\n".encode())
        digest.update(texts[split].encode("utf-8"))
    return digest.hexdigest()


def build_zip(settings, style_plan, lines: dict, labels: dict, *, runtime: str, created_at: str,
              versions: dict) -> tuple:
    """(zip bytes, dataset_sha256). labels: split -> list of labels, for the counts."""
    texts = split_texts(lines)
    sha = dataset_sha256(texts)
    metadata = {
        "format": FORMAT,
        "generator_version": __version__,
        "settings": settings.to_dict(),
        "grid": {"width": settings.width, "height": settings.height},
        "styles": {split: list(style_plan.by_split[split]) for split in SPLITS},
        "notices": list(style_plan.notices),
        "counts": {split: {str(d): labels[split].count(d) for d in range(10)} for split in SPLITS},
        "dataset_sha256": sha,
        "provenance": {"runtime": runtime, "created_at": created_at, "versions": versions},
    }
    files = {f"{split}.jsonl": texts[split] for split in SPLITS}
    files["metadata.json"] = json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    files["README.txt"] = README.format(version=__version__, width=settings.width, height=settings.height)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, text in files.items():
            info = zipfile.ZipInfo(name, date_time=ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, text.encode("utf-8"))
    return buffer.getvalue(), sha

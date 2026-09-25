"""Assemble the deployable site in dist/.

    python tools/build_site.py          # .github/workflows/pages.yml runs this, then deploys dist/

dist/ gets the current release twice, at the root and under /v<version>/,
plus every earlier release (git tags asciidigits-v<version>) under its own
/v<version>/, so links made with an old version keep generating the same data.
"""

import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

GENERATOR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GENERATOR))
from asciidigits import __version__  # noqa: E402

SITE_ITEMS = ["index.html", "web", "asciidigits", "assets/fonts", "wheels"]
TAG_PREFIX = "asciidigits-v"


def copy_site(source: Path, target: Path) -> None:
    for item in SITE_ITEMS:
        src, dst = source / item, target / item
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=GENERATOR, check=True, capture_output=True, text=True).stdout


def earlier_releases(workdir: Path) -> list:
    """[(version, folder with that release's generator/)] for every release tag."""
    prefix = git("rev-parse", "--show-prefix").strip()          # "" at the repository root
    releases = []
    for tag in git("tag", "--list", f"{TAG_PREFIX}*").split():
        archive = subprocess.run(["git", "archive", tag, *([prefix] if prefix else [])], cwd=GENERATOR,
                                 check=True, capture_output=True).stdout
        folder = workdir / tag
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(folder, filter="data")
        releases.append((tag.removeprefix(TAG_PREFIX), folder / prefix))
    return releases


def build(dist: Path, version: str, releases: list) -> None:
    if dist.exists():
        shutil.rmtree(dist)
    copy_site(GENERATOR, dist)
    releases = dict(releases)
    releases.setdefault(version, GENERATOR)     # not tagged yet: this tree is the release
    for release, folder in releases.items():    # a tagged version is always published as tagged
        copy_site(folder, dist / f"v{release}")


def main() -> None:
    dist = GENERATOR / "dist"
    with tempfile.TemporaryDirectory() as workdir:
        releases = earlier_releases(Path(workdir))
        build(dist, __version__, releases)
    print(f"built {dist}: current {__version__}, earlier: {[v for v, _ in releases if v != __version__] or 'none'}")


if __name__ == "__main__":
    main()

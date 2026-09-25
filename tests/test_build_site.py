import sys
from pathlib import Path

GENERATOR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GENERATOR / "tools"))
from build_site import build, copy_site  # noqa: E402


def test_the_site_is_at_the_root_and_under_its_version(tmp_path):
    dist = tmp_path / "dist"
    build(dist, "1.0.0", [])
    for root in (dist, dist / "v1.0.0"):
        assert (root / "index.html").is_file()
        assert (root / "web" / "worker.js").is_file()
        assert (root / "asciidigits" / "webapi.py").is_file()
        assert (root / "asciidigits" / "data" / "styles.json").is_file()
        assert (root / "assets" / "fonts" / "JetBrainsMono.ttf").is_file()
        assert next((root / "wheels").glob("pyfiglet-*.whl"))


def test_only_site_files_are_published(tmp_path):
    dist = tmp_path / "dist"
    build(dist, "1.0.0", [])
    names = {p.name for p in dist.rglob("*")}
    assert not names & {"tests", "tools", "__pycache__", "requirements.txt", "node_modules"}


def test_earlier_releases_keep_their_own_folder(tmp_path):
    old = tmp_path / "old-release"
    copy_site(GENERATOR, old)
    (old / "index.html").write_text("<p>version 0.9</p>", encoding="utf-8")
    dist = tmp_path / "dist"
    build(dist, "1.0.0", [("0.9.0", old)])
    assert (dist / "v0.9.0" / "index.html").read_text(encoding="utf-8") == "<p>version 0.9</p>"
    assert (dist / "index.html").read_text(encoding="utf-8") != "<p>version 0.9</p>"


def test_a_tagged_version_is_published_from_its_tag(tmp_path):
    # Links to /v<version>/ must keep their data even after the working tree moves on.
    tagged = tmp_path / "tagged"
    copy_site(GENERATOR, tagged)
    (tagged / "index.html").write_text("<p>as tagged</p>", encoding="utf-8")
    dist = tmp_path / "dist"
    build(dist, "1.0.0", [("1.0.0", tagged)])
    assert (dist / "v1.0.0" / "index.html").read_text(encoding="utf-8") == "<p>as tagged</p>"
    assert (dist / "index.html").read_text(encoding="utf-8") != "<p>as tagged</p>"

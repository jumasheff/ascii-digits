import json
import subprocess
import sys
import zipfile
from pathlib import Path

GENERATOR = Path(__file__).resolve().parent.parent


def run(*args):
    return subprocess.run([sys.executable, "-m", "asciidigits", *args], cwd=GENERATOR,
                          capture_output=True, text=True)


def test_generate_writes_a_zip_and_prints_its_hash(tmp_path):
    out = tmp_path / "small.zip"
    result = run("generate", "--seed", "7", "--per-digit", "3", "1", "1", "--split", "random",
                 "--styles", "figlet:big", "ttf:comic-neue", "--out", str(out))
    assert result.returncode == 0, result.stderr
    meta = json.loads(zipfile.ZipFile(out).read("metadata.json"))
    assert f"dataset_sha256 {meta['dataset_sha256']}" in result.stdout
    assert meta["settings"]["styles"] == ["figlet:big", "ttf:comic-neue"]


def test_generate_reports_bad_settings_without_a_traceback(tmp_path):
    result = run("generate", "--size", "99x10", "--out", str(tmp_path / "x.zip"))
    assert result.returncode == 2 and "error: width must be 6 to 40" in result.stderr
    assert "Traceback" not in result.stderr


def test_styles_lists_reasons():
    result = run("styles", "--size", "8x6")
    assert result.returncode == 0 and "figlet:big" in result.stdout and "no: " in result.stdout


def test_sheet_shows_every_available_style(tmp_path):
    out = tmp_path / "sheet.txt"
    result = run("sheet", "--size", "16x10", "--out", str(out))
    assert result.returncode == 0, result.stderr
    text = out.read_text(encoding="utf-8")
    assert "== figlet:big" in text and "== ttf:comic-neue" in text and "   damaged" in text

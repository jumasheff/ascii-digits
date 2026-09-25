"""The page, the worker, and the Python package must agree on names and versions."""

import json
import re
from pathlib import Path

import pytest

import asciidigits

GENERATOR = Path(__file__).resolve().parent.parent
WORKER = (GENERATOR / "web" / "worker.js").read_text(encoding="utf-8")
NOT_IN_BROWSER = {"__main__.py", "cli.py", "selfcheck.py"}


def test_page_and_package_versions_match():
    version_js = (GENERATOR / "web" / "version.js").read_text(encoding="utf-8")
    assert f'export const VERSION = "{asciidigits.__version__}";' in version_js


# Review focus: a new module added to the package but not to the worker breaks only the web page.
def test_the_worker_loads_every_module_the_package_has():
    listed = set(json.loads("[" + re.search(r"const PACKAGE_FILES = \[(.*?)\];", WORKER, re.S).group(1)
                            .replace("\n", "").rstrip().rstrip(",") + "]"))
    package = {p.relative_to(GENERATOR / "asciidigits").as_posix()
               for p in (GENERATOR / "asciidigits").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    assert listed == package - NOT_IN_BROWSER


def test_pinned_versions_agree():
    assert WORKER.count("cdn.jsdelivr.net/pyodide/v314.0.7/full/") == 2
    golden = json.loads((GENERATOR / "tests" / "golden" / "package.json").read_text(encoding="utf-8"))
    assert golden["dependencies"]["pyodide"] == "314.0.7"
    wheel = re.search(r'"wheels/(pyfiglet-[^"]+\.whl)"', WORKER).group(1)
    assert (GENERATOR / "wheels" / wheel).is_file()
    assert "pyfiglet==1.0.4" in (GENERATOR / "requirements.txt").read_text(encoding="utf-8") and "1.0.4" in wheel


def test_requirements_match_the_pyodide_build():
    lock_file = GENERATOR / "tests" / "golden" / "node_modules" / "pyodide" / "pyodide-lock.json"
    if not lock_file.is_file():
        pytest.skip("run `npm ci` in tests/golden first")
    lock = json.loads(lock_file.read_text(encoding="utf-8"))["packages"]
    requirements = (GENERATOR / "requirements.txt").read_text(encoding="utf-8")
    for name in ("numpy", "fonttools"):
        assert f"{name}=={lock[name]['version']}" in requirements

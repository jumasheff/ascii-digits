"""Every runtime must reproduce the recorded hashes in tests/golden/expected.json.

The hashes come from Pyodide (the web page's runtime), which is the reference.
CI runs the CPython test on Linux and macOS. The Pyodide test needs
Node.js: once, `cd tests/golden && npm ci`.

When an intentional change alters the output (new styles, a rendering change),
regenerate the reference and review the diff:
    cd tests/golden && node golden.mjs > expected.json
"""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from asciidigits.selfcheck import self_check

GOLDEN = Path(__file__).resolve().parent / "golden"
EXPECTED = json.loads((GOLDEN / "expected.json").read_text(encoding="utf-8"))


def test_cpython_reproduces_the_recorded_hashes():
    assert self_check() == EXPECTED


@pytest.mark.node
@pytest.mark.slow
def test_pyodide_reproduces_the_recorded_hashes():
    if shutil.which("node") is None:
        pytest.skip("Node.js is not installed")
    if not (GOLDEN / "node_modules" / "pyodide").is_dir():
        pytest.skip("run `npm ci` in tests/golden first")
    result = subprocess.run(["node", "golden.mjs"], cwd=GOLDEN, capture_output=True, text=True, timeout=900)
    assert result.returncode == 0, result.stderr[-2000:]
    assert json.loads(result.stdout[result.stdout.index("{"):]) == EXPECTED


def test_the_wheel_is_the_pinned_one():
    wheel = GOLDEN.parent.parent / "wheels" / "pyfiglet-1.0.4-py3-none-any.whl"
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert digest == "65b57b7a8e1dff8a67dc8e940a117238661d5e14c3e49121032bd404d9b2b39f"

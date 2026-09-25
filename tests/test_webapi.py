import io
import json
import zipfile

from asciidigits import webapi


def test_defaults_and_styles():
    defaults = json.loads(webapi.defaults_json())
    assert defaults["settings"]["width"] == 16 and defaults["presets"]["16x10"] == [16, 10]
    styles = json.loads(webapi.styles_json(8, 6))
    assert any(s["reason"] for s in styles) and any(s["reason"] is None for s in styles)


def test_validate_reports_errors_instead_of_raising():
    assert json.loads(webapi.validate_json('{"width": 99}')) == {"ok": False, "error": "width must be 6 to 40, got 99"}
    assert json.loads(webapi.validate_json('{"seed": "5"}'))["settings"]["seed"] == 5


def test_start_step_finish():
    webapi.configure("")                    # "" -> the package's own assets/fonts
    info = json.loads(webapi.start(json.dumps({"per_digit": [2, 1, 1], "seed": 8})))
    assert info["total"] == 40 and info["filename"] == "ascii-digits-8.zip"
    done = 0
    while done < info["total"]:
        done = webapi.step(15)
    data = webapi.finish("test")
    assert zipfile.ZipFile(io.BytesIO(data)).testzip() is None


def test_preview_json():
    samples = json.loads(webapi.preview_json('{"styles": ["figlet:doom"]}', 3))
    assert [s["style"] for s in samples] == ["figlet:doom"] * 3

"""The web worker's interface: JSON strings in, JSON strings (or zip bytes) out.

worker.js calls these through Pyodide. Keeping the boundary to plain strings
avoids converting Python objects in JavaScript.
"""

import json

from . import __version__
from .dataset import Generator, preview
from .settings import (FLOAT_LIMITS, INK_MODES, MAX_CELLS, MAX_HEIGHT, MAX_WIDTH, MIN_HEIGHT,
                       MIN_WIDTH, PRESETS, SPLIT_MODES, Settings, SettingsError)
from .styles import load_styles, unavailable_reason

_state = {"fonts_dir": None, "generator": None}


def configure(fonts_dir: str) -> str:
    _state["fonts_dir"] = fonts_dir
    return json.dumps({"version": __version__})


def defaults_json() -> str:
    return json.dumps({
        "version": __version__, "settings": Settings().to_dict(), "presets": PRESETS,
        "limits": {"width": [MIN_WIDTH, MAX_WIDTH], "height": [MIN_HEIGHT, MAX_HEIGHT],
                   "cells": MAX_CELLS, **FLOAT_LIMITS},
        "ink_modes": INK_MODES, "split_modes": SPLIT_MODES,
    })


def styles_json(width: int, height: int) -> str:
    return json.dumps([{"id": s.id, "name": s.name, "family": s.family,
                        "reason": unavailable_reason(s, width, height)} for s in load_styles()])


def _settings(settings_json: str) -> Settings:
    return Settings.from_dict(json.loads(settings_json))


def validate_json(settings_json: str) -> str:
    try:
        return json.dumps({"ok": True, "settings": _settings(settings_json).to_dict()})
    except SettingsError as error:
        return json.dumps({"ok": False, "error": str(error)})


def preview_json(settings_json: str, count: int = 30) -> str:
    return json.dumps(preview(_settings(settings_json), count, _state["fonts_dir"]))


def start(settings_json: str) -> str:
    generator = Generator(_settings(settings_json), _state["fonts_dir"])
    _state["generator"] = generator
    return json.dumps({"total": generator.total, "filename": generator.filename,
                       "notices": list(generator.style_plan.notices),
                       "styles": {k: list(v) for k, v in generator.style_plan.by_split.items()}})


def step(count: int) -> int:
    return _state["generator"].run_chunk(count)


def finish(runtime: str) -> bytes:
    zip_bytes, sha = _state["generator"].finish(runtime)
    _state["generator"] = None
    return zip_bytes


def cancel() -> None:
    _state["generator"] = None

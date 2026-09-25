import pytest

from asciidigits.settings import MAX_CELLS, Settings, SettingsError, parse_size


def test_defaults_match_the_spec():
    s = Settings().validate()
    assert (s.width, s.height) == (16, 10)
    assert s.per_digit == (500, 100, 100)
    assert s.total_samples == 7000
    assert s.split_mode == "heldout"
    assert s.noise == 0.03 and s.rotation == 8.0


def test_round_trip_through_json_types():
    s = Settings(seed=7, per_digit=(3, 1, 1), styles=("figlet:big",), ink_modes=("symbols", "ramp"))
    assert Settings.from_dict(s.to_dict()) == s


@pytest.mark.parametrize("changes, message", [
    ({"width": 5}, "width must be 6 to 40"),
    ({"height": 25}, "height must be 4 to 24"),
    ({"per_digit": [0, 1, 1]}, "train needs at least 1"),
    ({"per_digit": [1, 1]}, "three counts"),
    ({"per_digit": [5, -1, 1]}, "none negative"),
    ({"split_mode": "stratified"}, "split_mode must be one of"),
    ({"ink_modes": []}, "ink_modes must be one or more"),
    ({"ink_modes": ["crayon"]}, "ink_modes must be one or more"),
    ({"noise": 0.5}, "noise must be 0.0 to 0.3"),
    ({"seed": -1}, "seed must be between"),
])
def test_out_of_range_values_are_rejected_with_a_readable_message(changes, message):
    with pytest.raises(SettingsError, match=message):
        Settings.from_dict(changes)


def test_the_cell_cap():
    # 40x24 grid: 8,000,000 / 960 cells = 8,333 samples at most
    Settings.from_dict({"width": 40, "height": 24, "per_digit": [633, 100, 100]})       # 8,330 samples
    with pytest.raises(SettingsError, match="too big"):
        Settings.from_dict({"width": 40, "height": 24, "per_digit": [634, 100, 100]})  # 8,340 samples
    assert MAX_CELLS == 8_000_000


# Review focus: settings from an old or hand-edited URL arrive as strings, or garbage.
@pytest.mark.parametrize("data, message", [
    ({"width": "abc"}, "width must be a whole number"),
    ({"width": "16.5"}, "width must be a whole number"),
    ({"noise": "lots"}, "noise must be a number"),
    ({"styles": 5}, "styles must be a list"),
    ({"seed": True}, "seed must be a whole number"),
    ({"colour": "red"}, "unknown setting"),
])
def test_bad_input_types_give_settings_errors_not_crashes(data, message):
    with pytest.raises(SettingsError, match=message):
        Settings.from_dict(data)


def test_strings_from_a_url_are_accepted():
    s = Settings.from_dict({"seed": "9", "width": "12", "height": "8", "per_digit": "10,2,2",
                            "styles": "figlet:big,ttf:comic-neue", "noise": "0.1"})
    assert (s.seed, s.width, s.height, s.per_digit) == (9, 12, 8, (10, 2, 2))
    assert s.styles == ("figlet:big", "ttf:comic-neue")


def test_duplicate_styles_are_dropped_keeping_order():
    s = Settings.from_dict({"styles": ["b", "a", "b"]})
    assert s.styles == ("b", "a")


def test_parse_size():
    assert parse_size("16x10") == (16, 10)
    assert parse_size("24X14") == (24, 14)
    with pytest.raises(SettingsError, match="16x10"):
        parse_size("big")

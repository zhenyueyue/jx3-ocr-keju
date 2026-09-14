from ocr_keju.capture import CaptureRegion
from ocr_keju.preferences import PreferencesStore, UserPreferences


def test_preferences_round_trip(tmp_path) -> None:
    store = PreferencesStore(tmp_path / "settings.json")
    expected = UserPreferences(
        capture_region=CaptureRegion(10, 20, 600, 180, "DISPLAY1"),
        hotkey="<ctrl>+<alt>+k",
        local_match_threshold=0.81,
        overlay_timeout_ms=4500,
    )

    store.save(expected)

    assert store.load() == expected

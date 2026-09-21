from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from ocr_keju.capture import CaptureRegion


@dataclass(frozen=True, slots=True)
class UserPreferences:
    capture_region: CaptureRegion | None = None
    local_match_threshold: float = 0.78
    overlay_timeout_ms: int = 6000


class PreferencesStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self) -> UserPreferences:
        if not self.path.exists():
            return UserPreferences()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return UserPreferences()
        if not isinstance(payload, dict):
            return UserPreferences()
        threshold = payload.get("local_match_threshold", 0.78)
        timeout = payload.get("overlay_timeout_ms", 6000)
        try:
            threshold_value = min(1.0, max(0.0, float(threshold)))
        except (TypeError, ValueError):
            threshold_value = 0.78
        try:
            timeout_value = max(1000, int(timeout))
        except (TypeError, ValueError):
            timeout_value = 6000
        return UserPreferences(
            capture_region=CaptureRegion.from_dict(payload.get("capture_region")),
            local_match_threshold=threshold_value,
            overlay_timeout_ms=timeout_value,
        )

    def save(self, preferences: UserPreferences) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "capture_region": (
                preferences.capture_region.to_dict()
                if preferences.capture_region is not None
                else None
            ),
            "local_match_threshold": preferences.local_match_threshold,
            "overlay_timeout_ms": preferences.overlay_timeout_ms,
        }
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.path)

    def update_region(
        self, preferences: UserPreferences, region: CaptureRegion
    ) -> UserPreferences:
        updated = replace(preferences, capture_region=region)
        self.save(updated)
        return updated

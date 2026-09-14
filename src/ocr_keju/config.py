from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_API_BASE_URL = "https://pull-gplugin.jx3box.com"


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    database_path: Path
    api_base_url: str = DEFAULT_API_BASE_URL
    api_timeout_seconds: float = 8.0

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.environ.get("OCR_KEJU_DATA_DIR", "data")).expanduser()
        api_base_url = os.environ.get("OCR_KEJU_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")
        timeout = float(os.environ.get("OCR_KEJU_API_TIMEOUT", "8"))
        return cls(
            data_dir=data_dir,
            database_path=data_dir / "questions.db",
            api_base_url=api_base_url,
            api_timeout_seconds=timeout,
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

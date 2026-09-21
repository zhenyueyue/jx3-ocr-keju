from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_API_BASE_URL = "https://pull-gplugin.jx3box.com"
APP_DATA_DIR_NAME = "jx3-ocr-keju"


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _windows_persistent_data_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data).expanduser() / APP_DATA_DIR_NAME
    return Path.home() / "AppData" / "Local" / APP_DATA_DIR_NAME


def _copy_missing_tree(source: Path, destination: Path) -> None:
    if not source.exists() or source.resolve() == destination.resolve():
        return
    for source_path in source.rglob("*"):
        relative = source_path.relative_to(source)
        target_path = destination / relative
        if source_path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue
        if target_path.exists():
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    database_path: Path
    api_base_url: str = DEFAULT_API_BASE_URL
    api_timeout_seconds: float = 8.0
    legacy_data_dirs: tuple[Path, ...] = ()

    @classmethod
    def from_env(cls) -> "Settings":
        explicit_data_dir = os.environ.get("OCR_KEJU_DATA_DIR")
        legacy_data_dirs: tuple[Path, ...] = ()

        if explicit_data_dir:
            data_dir = Path(explicit_data_dir).expanduser()
        elif _is_frozen():
            data_dir = _windows_persistent_data_dir()
            executable_dir = Path(sys.executable).resolve().parent
            candidates = [executable_dir / "data", Path.cwd() / "data"]
            legacy_data_dirs = tuple(
                candidate
                for index, candidate in enumerate(candidates)
                if candidate not in candidates[:index] and candidate.resolve() != data_dir.resolve()
            )
        else:
            data_dir = Path("data")

        api_base_url = os.environ.get("OCR_KEJU_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")
        timeout = float(os.environ.get("OCR_KEJU_API_TIMEOUT", "8"))
        return cls(
            data_dir=data_dir,
            database_path=data_dir / "questions.db",
            api_base_url=api_base_url,
            api_timeout_seconds=timeout,
            legacy_data_dirs=legacy_data_dirs,
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for legacy_dir in self.legacy_data_dirs:
            _copy_missing_tree(legacy_dir, self.data_dir)

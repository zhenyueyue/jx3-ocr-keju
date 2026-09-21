from __future__ import annotations

import sys

from ocr_keju.config import Settings


def test_source_mode_keeps_project_data_dir(monkeypatch) -> None:
    monkeypatch.delenv("OCR_KEJU_DATA_DIR", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)

    settings = Settings.from_env()

    assert settings.data_dir.as_posix() == "data"
    assert settings.database_path.as_posix() == "data/questions.db"
    assert settings.legacy_data_dirs == ()


def test_frozen_mode_uses_local_app_data_and_migrates_legacy_files(tmp_path, monkeypatch) -> None:
    local_app_data = tmp_path / "LocalAppData"
    executable_dir = tmp_path / "dist" / "ocr-keju"
    legacy_data = executable_dir / "data"
    legacy_data.mkdir(parents=True)
    (legacy_data / "questions.db").write_bytes(b"legacy-db")
    (legacy_data / "settings.json").write_text('{"ok": true}', encoding="utf-8")

    monkeypatch.delenv("OCR_KEJU_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable_dir / "ocr-keju.exe"))
    monkeypatch.chdir(tmp_path)

    settings = Settings.from_env()
    settings.ensure_directories()

    assert settings.data_dir == local_app_data / "jx3-ocr-keju"
    assert settings.database_path.read_bytes() == b"legacy-db"
    assert (settings.data_dir / "settings.json").read_text(encoding="utf-8") == '{"ok": true}'


def test_migration_never_overwrites_existing_persistent_database(tmp_path, monkeypatch) -> None:
    local_app_data = tmp_path / "LocalAppData"
    persistent = local_app_data / "jx3-ocr-keju"
    persistent.mkdir(parents=True)
    (persistent / "questions.db").write_bytes(b"persistent-db")

    executable_dir = tmp_path / "dist" / "ocr-keju"
    legacy_data = executable_dir / "data"
    legacy_data.mkdir(parents=True)
    (legacy_data / "questions.db").write_bytes(b"legacy-db")

    monkeypatch.delenv("OCR_KEJU_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable_dir / "ocr-keju.exe"))
    monkeypatch.chdir(tmp_path)

    settings = Settings.from_env()
    settings.ensure_directories()

    assert settings.database_path.read_bytes() == b"persistent-db"


def test_explicit_data_dir_still_takes_priority_in_frozen_mode(tmp_path, monkeypatch) -> None:
    custom = tmp_path / "custom-data"
    monkeypatch.setenv("OCR_KEJU_DATA_DIR", str(custom))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    settings = Settings.from_env()
    settings.ensure_directories()

    assert settings.data_dir == custom
    assert settings.legacy_data_dirs == ()

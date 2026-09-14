from __future__ import annotations

from pynput import keyboard
from PySide6.QtCore import QObject, Signal


class GlobalHotkeyManager(QObject):
    activated = Signal()
    failed = Signal(str)

    def __init__(self, hotkey: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.hotkey = hotkey
        self._listener: keyboard.GlobalHotKeys | None = None

    def start(self) -> None:
        self.stop()
        try:
            self._listener = keyboard.GlobalHotKeys(
                {self.hotkey: lambda: self.activated.emit()}
            )
            self._listener.start()
        except Exception as exc:  # platform hook errors are implementation-specific
            self._listener = None
            self.failed.emit(str(exc))

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

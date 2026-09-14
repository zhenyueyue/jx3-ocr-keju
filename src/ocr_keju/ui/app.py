from __future__ import annotations

import sys

from PySide6.QtCore import QObject, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

from ocr_keju.api import JX3BoxExamClient
from ocr_keju.capture import CaptureRegion
from ocr_keju.capture.qt_capture import QtScreenCapture, ScreenCaptureError
from ocr_keju.config import Settings
from ocr_keju.database import QuestionRepository
from ocr_keju.hotkey import GlobalHotkeyManager
from ocr_keju.ocr import RapidOcrEngine
from ocr_keju.pipeline import RecognitionOutcome, RecognitionPipeline
from ocr_keju.preferences import PreferencesStore, UserPreferences
from ocr_keju.sync import QuestionBankSyncService, SyncReport
from ocr_keju.ui.answer_overlay import AnswerOverlay
from ocr_keju.ui.main_window import MainWindow
from ocr_keju.ui.region_selector import RegionSelector
from ocr_keju.ui.worker import Worker


class DesktopController(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        self.settings = Settings.from_env()
        self.settings.ensure_directories()
        self.repository = QuestionRepository(self.settings.database_path)
        self.repository.initialize()
        self.preferences_store = PreferencesStore(self.settings.data_dir / "settings.json")
        self.preferences = self.preferences_store.load()
        self.capture = QtScreenCapture()
        self.pipeline = RecognitionPipeline(
            self.settings,
            self.repository,
            RapidOcrEngine(),
        )
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(max(2, self.thread_pool.maxThreadCount()))
        self.window = MainWindow()
        self.overlay = AnswerOverlay()
        self.selector: RegionSelector | None = None
        self.hotkey = GlobalHotkeyManager(self.preferences.hotkey, self)
        self._busy = False
        self._active_worker: Worker | None = None
        self._bind()
        self._refresh_status()
        self.hotkey.start()

    def _bind(self) -> None:
        self.window.select_region_requested.connect(self.select_region)
        self.window.recognize_requested.connect(self.recognize)
        self.window.sync_requested.connect(self.sync_bank)
        self.window.closing.connect(self.shutdown)
        self.hotkey.activated.connect(self.recognize)
        self.hotkey.failed.connect(
            lambda message: self.window.show_status(f"全局快捷键启动失败：{message}")
        )

    def _refresh_status(self) -> None:
        self.window.set_bank_count(self.repository.count())
        self.window.set_region(self.preferences.capture_region)
        self.window.set_hotkey(self.preferences.hotkey)

    def show(self) -> None:
        self.window.show()

    def select_region(self) -> None:
        if self._busy:
            return
        self.selector = RegionSelector()
        self.selector.region_selected.connect(self._region_selected)
        self.selector.show()

    def _region_selected(self, region: CaptureRegion) -> None:
        self.preferences = self.preferences_store.update_region(self.preferences, region)
        self.window.set_region(region)
        self.window.show_status("截图区域已保存，按 Alt + Q 或点击“立即识别”")
        self.window.raise_()
        self.window.activateWindow()

    def recognize(self) -> None:
        if self._busy:
            return
        region = self.preferences.capture_region
        if region is None:
            self.window.show_status("请先框选科举题目文字区域")
            self.select_region()
            return

        try:
            image = self.capture.capture(region)
        except ScreenCaptureError as exc:
            self.window.show_status(str(exc))
            return

        self._set_busy(True, "正在 OCR 并匹配题库…")
        threshold = self.preferences.local_match_threshold
        worker = Worker(lambda: self.pipeline.recognize(image, threshold))
        worker.signals.result.connect(self._recognition_done)
        worker.signals.error.connect(self._worker_error)
        self._active_worker = worker
        self.thread_pool.start(worker)

    def _recognition_done(self, value: object) -> None:
        self._finish_task()
        if not isinstance(value, RecognitionOutcome):
            self.window.show_status("识别任务返回了未知结果")
            return
        self.window.show_outcome(value)
        if value.warning:
            self.window.show_status(value.warning)
        else:
            self.window.show_status("识别完成")
        self.overlay.show_outcome(value, self.preferences.overlay_timeout_ms)
        self.window.set_bank_count(self.repository.count())

    def sync_bank(self) -> None:
        if self._busy:
            return
        self._set_busy(True, "正在同步 JX3BOX 科举题库…")

        def do_sync() -> SyncReport:
            with JX3BoxExamClient(
                base_url=self.settings.api_base_url,
                timeout_seconds=max(20.0, self.settings.api_timeout_seconds),
            ) as client:
                return QuestionBankSyncService(self.repository, client).sync()

        worker = Worker(do_sync)
        worker.signals.result.connect(self._sync_done)
        worker.signals.error.connect(self._worker_error)
        self._active_worker = worker
        self.thread_pool.start(worker)

    def _sync_done(self, value: object) -> None:
        self._finish_task()
        if not isinstance(value, SyncReport):
            self.window.show_status("同步任务返回了未知结果")
            return
        self.window.set_bank_count(value.local_total)
        self.window.show_status(
            f"同步完成：远端 {value.fetched} 条，本地共 {value.local_total} 条"
        )

    def _worker_error(self, message: str) -> None:
        self._finish_task()
        self.window.show_status(f"任务失败：{message}")
        QMessageBox.warning(self.window, "OCR 科举助手", message)

    def _finish_task(self) -> None:
        self._active_worker = None
        self._set_busy(False, "就绪")

    def _set_busy(self, busy: bool, message: str) -> None:
        self._busy = busy
        self.window.set_busy(busy, message)

    def shutdown(self) -> None:
        self.hotkey.stop()
        self.overlay.close()


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("OCR 科举助手")
    app.setOrganizationName("ocr-keju")
    controller = DesktopController(app)
    controller.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

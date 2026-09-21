from __future__ import annotations

import sys

import numpy as np
from PySide6.QtCore import QObject, QThreadPool, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from ocr_keju.api import JX3BoxExamClient
from ocr_keju.capture import CaptureRegion
from ocr_keju.capture.change_detector import frame_difference, frame_signature
from ocr_keju.capture.qt_capture import QtScreenCapture, ScreenCaptureError
from ocr_keju.config import Settings
from ocr_keju.database import QuestionRepository
from ocr_keju.ocr import RapidOcrEngine
from ocr_keju.pipeline import RecognitionOutcome, RecognitionPipeline
from ocr_keju.preferences import PreferencesStore
from ocr_keju.sync import QuestionBankSyncService, SyncReport
from ocr_keju.ui.answer_overlay import AnswerOverlay
from ocr_keju.ui.main_window import MainWindow
from ocr_keju.ui.region_selector import RegionSelector
from ocr_keju.ui.worker import Worker


MONITOR_INTERVAL_MS = 450
FRAME_CHANGE_THRESHOLD = 0.015


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

        self._busy = False
        self._recognition_running = False
        self._monitor_enabled = True
        self._recapture_pending = False
        self._active_worker: Worker | None = None
        self._last_signature: np.ndarray | None = None
        self._pending_signature: np.ndarray | None = None

        self._monitor_timer = QTimer(self)
        self._monitor_timer.setInterval(MONITOR_INTERVAL_MS)
        self._monitor_timer.timeout.connect(self._monitor_tick)

        self._bind()
        self._refresh_status()
        self._monitor_timer.start()

    def _bind(self) -> None:
        self.window.select_region_requested.connect(self.select_region)
        self.window.monitor_toggle_requested.connect(self.toggle_monitoring)
        self.window.recognize_requested.connect(self.recognize)
        self.window.sync_requested.connect(self.sync_bank)
        self.window.closing.connect(self.shutdown)

    def _refresh_status(self) -> None:
        region = self.preferences.capture_region
        self.window.set_bank_count(self.repository.count())
        self.window.set_region(region)
        self.window.set_monitoring(self._monitor_enabled, region is not None)

    def show(self) -> None:
        self.window.show()
        if self.preferences.capture_region is not None:
            self.window.show_status("实时检测已开启，检测到新题目后会自动框出正确选项")

    def select_region(self) -> None:
        if self._busy or self._recognition_running:
            return
        self.overlay.clear()
        self.selector = RegionSelector()
        self.selector.region_selected.connect(self._region_selected)
        self.selector.show()

    def _region_selected(self, region: CaptureRegion) -> None:
        self.preferences = self.preferences_store.update_region(self.preferences, region)
        self._monitor_enabled = True
        self._last_signature = None
        self._pending_signature = None
        self.overlay.clear()
        self.window.set_region(region)
        self.window.set_monitoring(True, True)
        self.window.show_status("检测区域已保存：请确保包含完整题目和全部答案选项")
        self.window.raise_()
        self.window.activateWindow()

    def toggle_monitoring(self) -> None:
        if self.preferences.capture_region is None:
            self.select_region()
            return
        self._monitor_enabled = not self._monitor_enabled
        self._last_signature = None
        self.overlay.clear()
        self.window.set_monitoring(True if self._monitor_enabled else False, True)
        self.window.show_status("实时检测已开启" if self._monitor_enabled else "实时检测已暂停")

    def recognize(self) -> None:
        if self._busy or self._recognition_running:
            return
        region = self.preferences.capture_region
        if region is None:
            self.window.show_status("请先框选包含题目和全部选项的区域")
            self.select_region()
            return
        try:
            image = self.capture.capture(region)
        except ScreenCaptureError as exc:
            self.window.show_status(str(exc))
            return
        self.overlay.clear()
        self._start_recognition(image, frame_signature(image), manual=True)

    def _monitor_tick(self) -> None:
        if (
            not self._monitor_enabled
            or self._busy
            or self._recognition_running
            or self._recapture_pending
        ):
            return
        region = self.preferences.capture_region
        if region is None:
            return

        try:
            image = self.capture.capture(region)
        except ScreenCaptureError as exc:
            self.window.show_status(str(exc))
            return

        signature = frame_signature(image)
        if self._last_signature is None:
            self.overlay.clear()
            self._start_recognition(image, signature)
            return

        if frame_difference(self._last_signature, signature) >= FRAME_CHANGE_THRESHOLD:
            # 先移除上一题的描边，再稍后重新截图，避免旧描边进入 OCR 图片。
            self.overlay.clear()
            self._recapture_pending = True
            QTimer.singleShot(45, self._recognize_changed_frame)

    def _recognize_changed_frame(self) -> None:
        self._recapture_pending = False
        if self._busy or self._recognition_running or not self._monitor_enabled:
            return
        region = self.preferences.capture_region
        if region is None:
            return
        try:
            image = self.capture.capture(region)
        except ScreenCaptureError as exc:
            self.window.show_status(str(exc))
            return
        self._start_recognition(image, frame_signature(image))

    def _start_recognition(
        self,
        image: np.ndarray,
        signature: np.ndarray,
        manual: bool = False,
    ) -> None:
        if self._recognition_running or self._busy:
            return
        self._recognition_running = True
        self._pending_signature = signature
        self.window.show_status("正在识别题目并定位正确选项…" if manual else "检测到新题目，正在识别…")
        threshold = self.preferences.local_match_threshold
        worker = Worker(lambda: self.pipeline.recognize(image, threshold))
        worker.signals.result.connect(self._recognition_done)
        worker.signals.error.connect(self._recognition_error)
        self._active_worker = worker
        self.thread_pool.start(worker)

    def _recognition_done(self, value: object) -> None:
        self._finish_recognition()
        if not isinstance(value, RecognitionOutcome):
            self.window.show_status("识别任务返回了未知结果")
            return

        self.window.show_outcome(value)
        region = self.preferences.capture_region
        if region is not None and value.answer_boxes:
            self.overlay.show_outcome(value, region)
            self.window.show_status("已识别并框出正确答案 · 实时检测继续运行")
        elif value.warning:
            self.overlay.clear()
            self.window.show_status(value.warning)
        else:
            self.overlay.clear()
            self.window.show_status("识别完成，但没有定位到屏幕选项")

        self.window.set_bank_count(self.repository.count())
        # 描边出现后重新建立基线，避免程序自己的框触发下一次 OCR。
        QTimer.singleShot(120, self._refresh_monitor_baseline)

    def _recognition_error(self, message: str) -> None:
        self._finish_recognition()
        self.overlay.clear()
        self.window.show_status(f"实时识别失败：{message}")
        QTimer.singleShot(500, self._refresh_monitor_baseline)

    def _finish_recognition(self) -> None:
        if self._pending_signature is not None:
            self._last_signature = self._pending_signature
        self._pending_signature = None
        self._active_worker = None
        self._recognition_running = False

    def _refresh_monitor_baseline(self) -> None:
        if self._busy or self._recognition_running:
            return
        region = self.preferences.capture_region
        if region is None:
            return
        try:
            image = self.capture.capture(region)
        except ScreenCaptureError:
            return
        self._last_signature = frame_signature(image)

    def sync_bank(self) -> None:
        if self._busy or self._recognition_running:
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
        worker.signals.error.connect(self._sync_error)
        self._active_worker = worker
        self.thread_pool.start(worker)

    def _sync_done(self, value: object) -> None:
        self._finish_task()
        if not isinstance(value, SyncReport):
            self.window.show_status("同步任务返回了未知结果")
            return
        self.window.set_bank_count(value.local_total)
        self.window.show_status(
            f"同步完成：远端 {value.fetched} 条，本地共 {value.local_total} 条 · 实时检测继续运行"
        )

    def _sync_error(self, message: str) -> None:
        self._finish_task()
        self.window.show_status(f"题库同步失败：{message}")
        QMessageBox.warning(self.window, "OCR 科举助手", message)

    def _finish_task(self) -> None:
        self._active_worker = None
        self._set_busy(False, "就绪")

    def _set_busy(self, busy: bool, message: str) -> None:
        self._busy = busy
        self.window.set_monitoring(
            self._monitor_enabled,
            self.preferences.capture_region is not None,
        )
        self.window.set_busy(busy, message)

    def shutdown(self) -> None:
        self._monitor_timer.stop()
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

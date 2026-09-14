from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QGuiApplication, QImage

from ocr_keju.capture.model import CaptureRegion


class ScreenCaptureError(RuntimeError):
    pass


class QtScreenCapture:
    def capture(self, region: CaptureRegion) -> np.ndarray:
        if not region.is_valid:
            raise ScreenCaptureError("截图区域无效，请重新框选")

        screen = self._resolve_screen(region)
        if screen is None:
            raise ScreenCaptureError("找不到截图区域所在的显示器，请重新框选")

        geometry = screen.geometry()
        requested = QRect(region.left, region.top, region.width, region.height)
        if not geometry.contains(requested):
            raise ScreenCaptureError("截图区域已经超出原显示器范围，请重新框选")

        local_x = region.left - geometry.left()
        local_y = region.top - geometry.top()
        pixmap = screen.grabWindow(0, local_x, local_y, region.width, region.height)
        if pixmap.isNull():
            raise ScreenCaptureError("屏幕截图失败")
        return self._qimage_to_bgr(pixmap.toImage())

    @staticmethod
    def _resolve_screen(region: CaptureRegion):
        screens = QGuiApplication.screens()
        if region.screen_name:
            for screen in screens:
                if screen.name() == region.screen_name:
                    return screen
        center = QPoint(
            region.left + region.width // 2,
            region.top + region.height // 2,
        )
        return QGuiApplication.screenAt(center)

    @staticmethod
    def _qimage_to_bgr(image: QImage) -> np.ndarray:
        converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
        width = converted.width()
        height = converted.height()
        bytes_per_line = converted.bytesPerLine()
        buffer = converted.bits()
        array = np.frombuffer(buffer, dtype=np.uint8, count=converted.sizeInBytes())
        array = array.reshape((height, bytes_per_line // 4, 4))[:, :width, :]
        return cv2.cvtColor(array, cv2.COLOR_RGBA2BGR).copy()

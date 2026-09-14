from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

from ocr_keju.capture import CaptureRegion


class RegionSelector(QWidget):
    region_selected = Signal(object)

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self._start: QPoint | None = None
        self._end: QPoint | None = None
        self._screenshots = []

        screens = QApplication.screens()
        if not screens:
            raise RuntimeError("没有可用显示器")
        virtual = screens[0].geometry()
        for screen in screens[1:]:
            virtual = virtual.united(screen.geometry())
        self._virtual_geometry = virtual
        self.setGeometry(virtual)

        for screen in screens:
            self._screenshots.append((screen, screen.grabWindow(0)))

    def showEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        for screen, pixmap in self._screenshots:
            geometry = screen.geometry()
            target = QRect(
                geometry.left() - self._virtual_geometry.left(),
                geometry.top() - self._virtual_geometry.top(),
                geometry.width(),
                geometry.height(),
            )
            painter.drawPixmap(target, pixmap, pixmap.rect())

        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(
            24,
            36,
            "拖动框选科举题目文字区域 · Esc 取消",
        )

        selection = self._selection_rect()
        if selection is not None:
            painter.setPen(QPen(QColor(72, 170, 255), 2))
            painter.setBrush(QColor(72, 170, 255, 35))
            painter.drawRect(selection)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                selection.left(),
                max(18, selection.top() - 8),
                f"{selection.width()} × {selection.height()}",
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.position().toPoint()
            self._end = self._start
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._start is not None:
            self._end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._start is None:
            return
        self._end = event.position().toPoint()
        selection = self._selection_rect()
        if selection is None or selection.width() < 20 or selection.height() < 20:
            self._start = None
            self._end = None
            self.update()
            return

        global_rect = selection.translated(self._virtual_geometry.topLeft())
        screen = QApplication.screenAt(global_rect.center())
        region = CaptureRegion(
            left=global_rect.left(),
            top=global_rect.top(),
            width=global_rect.width(),
            height=global_rect.height(),
            screen_name=screen.name() if screen is not None else "",
        )
        self.region_selected.emit(region)
        self.close()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def _selection_rect(self) -> QRect | None:
        if self._start is None or self._end is None:
            return None
        return QRect(self._start, self._end).normalized()
